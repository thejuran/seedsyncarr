#!/usr/bin/env bash
# Phase 78 UAT — bounded local FS for the Local Storage tile (D-05).
# Usage: ./bound-local-fs.sh up     # create + mount 100 MB ext4 image at /tmp/seedsyncarr-phase78-local
#        ./bound-local-fs.sh down   # unmount + remove image
# Requires sudo for mount/losetup.
set -euo pipefail

IMG="/tmp/seedsyncarr-phase78-local.img"
MNT="/tmp/seedsyncarr-phase78-local"

case "${1:-up}" in
  up)
    if mountpoint -q "$MNT" 2>/dev/null; then
      echo "[bound-local-fs] Already mounted at $MNT"; exit 0
    fi
    mkdir -p "$MNT"
    if [[ ! -f "$IMG" ]]; then
      dd if=/dev/zero of="$IMG" bs=1M count=100 status=none
      mkfs.ext4 -q -F "$IMG"
    fi
    sudo mount -o loop "$IMG" "$MNT"
    sudo chown "$(id -u):$(id -g)" "$MNT"
    chmod 0755 "$MNT"
    df -B1 "$MNT" | tail -1
    ;;
  down)
    if mountpoint -q "$MNT" 2>/dev/null; then
      sudo umount "$MNT"
    fi
    rm -f "$IMG"
    rmdir "$MNT" 2>/dev/null || true
    ;;
  *)
    echo "usage: $0 up|down" >&2; exit 2
    ;;
esac
