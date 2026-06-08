#!/bin/bash
# Runtime entrypoint: remap the seedsyncarr user to the PUID/PGID supplied at
# container start, fix ownership of the runtime-writable paths, then drop
# privileges to that user via gosu.
#
# Why this exists: the image bakes a non-root `seedsyncarr` user at build time.
# Without remapping, the container's uid never matches the host owner of the
# bind-mounted /downloads (and /config), so LFTP cannot write and the whole
# pipeline silently fails. PUID/PGID let the operator align the in-container
# user to the host owner of the mounts.
#
# Defaults preserve historical behaviour (uid/gid 1000) when PUID/PGID are unset.
set -euo pipefail

PUID="${PUID:-1000}"
PGID="${PGID:-1000}"

log() { echo "[entrypoint] $*"; }

# --- Remap group -----------------------------------------------------------
# groupmod by GID. If another group already owns the target GID, reuse its name
# rather than failing (common on NAS where GID 100 = 'users').
current_gid="$(getent group seedsyncarr | cut -d: -f3 || true)"
if [ "${current_gid}" != "${PGID}" ]; then
    if existing_group="$(getent group "${PGID}" | cut -d: -f1)"; then
        log "GID ${PGID} already exists as '${existing_group}'; using it for seedsyncarr"
        usermod -g "${PGID}" seedsyncarr
    else
        groupmod -g "${PGID}" seedsyncarr
    fi
fi

# --- Remap user ------------------------------------------------------------
current_uid="$(id -u seedsyncarr)"
if [ "${current_uid}" != "${PUID}" ]; then
    log "Remapping seedsyncarr uid ${current_uid} -> ${PUID}"
    usermod -u "${PUID}" seedsyncarr
fi

# --- Fix ownership of runtime-writable paths -------------------------------
# Only the mount roots, non-recursively by default, to avoid an expensive
# chown -R over terabytes of existing downloads on every start. Set
# ENTRYPOINT_CHOWN_RECURSIVE=true to force a one-time deep fix after a
# permissions incident.
chown_target() {
    target="$1"
    [ -e "${target}" ] || return 0
    if [ "${ENTRYPOINT_CHOWN_RECURSIVE:-false}" = "true" ]; then
        log "Recursively chowning ${target} -> ${PUID}:${PGID}"
        chown -R "${PUID}:${PGID}" "${target}"
    else
        chown "${PUID}:${PGID}" "${target}"
    fi
}
chown_target /config
chown_target /downloads

# --- SSH home for the remapped user ----------------------------------------
# Outbound SSH/SCP/SFTP (remote scan + LFTP) runs through the libnss-wrapper
# `run_as_user` shim, which hardcodes HOME=/home/seedsync and tries to mkdir it.
# After remapping to an arbitrary PUID, /home is root-owned and not writable by
# that uid, so the mkdir fails, ssh cannot write known_hosts, and host-key
# verification fails — silently breaking the remote scan (model stays empty).
# Pre-create the shim's HOME (and the user's passwd HOME) owned by PUID:PGID and
# seed an ssh config that auto-accepts new host keys (rejects changed ones),
# mirroring the build-time /root/.ssh/config which the non-root user can't read.
#
# Resilience notes (must not hard-fail under `set -e`):
#  - A read-only bind mount may live inside the home (e2e mounts an SSH key at
#    /home/seedsync/.ssh/id_ed25519, read-only) — a recursive chown over it
#    fails on that inode. chown the dir top-level only, ignoring per-file errors;
#    a mounted key is already owned correctly by whoever mounted it.
#  - The ssh config may itself be a read-only mount — only seed/chmod it when we
#    actually own and can write it.
SHIM_HOME=/home/seedsync
USER_HOME="$(getent passwd "${PUID}" | cut -d: -f6 || true)"
for h in "${SHIM_HOME}" "${USER_HOME}"; do
    [ -n "${h}" ] || continue
    mkdir -p "${h}/.ssh" 2>/dev/null || true
    if [ ! -e "${h}/.ssh/config" ]; then
        echo "StrictHostKeyChecking accept-new" > "${h}/.ssh/config" 2>/dev/null || true
    fi
    chmod 700 "${h}/.ssh" 2>/dev/null || true
    chmod 600 "${h}/.ssh/config" 2>/dev/null || true
    # Own the home + .ssh dir for the runtime user; tolerate read-only mounts
    # inside (e.g. an injected SSH key) instead of aborting startup.
    chown "${PUID}:${PGID}" "${h}" "${h}/.ssh" 2>/dev/null || true
    chown "${PUID}:${PGID}" "${h}/.ssh/config" 2>/dev/null || true
done

# --- First-run config setup (runs at runtime, after /config is mounted) ----
# setup_default_config.sh is idempotent for an existing settings.cfg: the
# default-generation step is guarded with `|| true` and the replace step is a
# no-op once the placeholder is gone. Run it as the target user so any files it
# creates are owned correctly.
if [ -x /scripts/setup_default_config.sh ]; then
    log "Running config setup as uid ${PUID}"
    gosu "${PUID}:${PGID}" /scripts/setup_default_config.sh || \
        log "config setup returned non-zero (existing config — continuing)"
fi

log "Starting seedsyncarr as uid ${PUID} gid ${PGID}"
exec gosu "${PUID}:${PGID}" "$@"
