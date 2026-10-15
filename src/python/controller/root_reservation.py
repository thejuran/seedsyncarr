"""
Per-root operation reservations.

Serializes destructive local operations (auto-delete Timer, manual Delete
Local) against transfer submission (QUEUE) for the same root. The model lock
alone cannot do this: Controller.__process_commands releases __model_lock
before CommandProcessor.handle submits a QUEUE, and the auto-delete Timer
releases it before FileOperationManager.delete_local. Without a reservation a
Timer could pass every guard on an empty submitted set, a concurrent QUEUE
could then submit the root, and the Timer would delete the copy lftp is
writing.

Ownership rule: the acquirer owns the token until it either calls release()
(or leaves the ``with`` block), or passes it to
FileOperationManager.delete_local(file, reservation=token). From the moment
delete_local is entered the manager owns it and guarantees release on every
outcome: launch failure (released before the exception propagates, the
wrapper is never tracked), child exit with any status (released by
cleanup_completed_processes), or shutdown (released by stop()). Between entry
and the end of the child's start() the token is held, untracked and not
releasable by the cleanup sweep: the manager registers a wrapper only after
start() has returned. The caller must not release after a hand-off; release()
is idempotent, so doing so is harmless to the registry but would reopen the
window early.

The hold deliberately spans the deletion child's whole lifetime:
delete_local returns as soon as the child has started, while the actual
os.remove / shutil.rmtree runs for seconds to minutes afterwards. A QUEUE
accepted in that time would submit a transfer whose files the child then
deletes.

Lock order: reservation -> Controller.__model_lock -> __auto_delete_lock.
The registry's own lock is a leaf (never held while calling out). A
reservation is held across lftp.queue and across the deletion child on
purpose, but nothing ever waits for a reservation: acquire() is
non-blocking and callers decide what to do on conflict (defer, 409, or a
quiet skip).
"""

import threading
from typing import Dict, Optional


class RootReservation:
    """A held reservation on one root name. Release is idempotent."""

    def __init__(self, registry: "RootReservations", name: str, holder: str):
        self.name = name
        self.holder = holder
        self.__registry = registry

    def release(self) -> None:
        """
        Release the reservation.

        Owner-checked: removes the registry entry only if that entry is this
        token, so a second call, or a call after a newer holder took the name,
        is a no-op. Never raises.
        """
        self.__registry._release(self)

    def __enter__(self) -> "RootReservation":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()


class RootReservations:
    """Process-local registry of per-root operation reservations."""

    def __init__(self):
        self.__lock = threading.Lock()
        self.__held: Dict[str, RootReservation] = {}

    def acquire(self, name: str, holder: str) -> Optional[RootReservation]:
        """
        Try to reserve ``name`` for ``holder``.

        Non-blocking: returns None when another holder already owns the name.
        """
        with self.__lock:
            if name in self.__held:
                return None
            token = RootReservation(self, name, holder)
            self.__held[name] = token
            return token

    def holder_of(self, name: str) -> Optional[str]:
        """Return the current holder of ``name``, or None if it is free."""
        with self.__lock:
            token = self.__held.get(name)
            return token.holder if token is not None else None

    def _release(self, token: RootReservation) -> None:
        with self.__lock:
            if self.__held.get(token.name) is token:
                del self.__held[token.name]
