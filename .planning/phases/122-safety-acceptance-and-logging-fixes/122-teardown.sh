#!/usr/bin/env bash
# Idempotent teardown for the Phase 122 SAFE-01 sandbox sessions (seedsyncarr-test).
#
# Usage (on the NAS):  bash teardown.sh [--final] [<capture-dir>]   (or env D=<capture-dir>)
# When neither is given, the capture dir defaults to the directory containing this script
# (it is copied into the capture dir as teardown.sh).
#
# Reads <capture-dir>/state.env (KEY=value lines; parsed, never sourced), last value wins:
#   IMAGE_PIN_L0        original seedsyncarr-test image pin, recorded before any deploy
#   DEV_PIN             the digest-pinned image this session deployed
#   RATE_LIMIT_L0       lftp.rate_limit value recorded before any session change
#   DELAY_L0            autodelete.delay_seconds value recorded before any session change
#   RATE_LIMIT_SET      1 if lftp.rate_limit was changed this session and needs restoring
#   DELAY_SET           1 if autodelete.delay_seconds was changed this session and needs restoring
#   WEBHOOK_SECRET_SET  1 if general.webhook_secret was set (non-empty) this session
#   SYNTH_ROOTS         comma-separated list of synthetic root names created this session
# A missing key means nothing of that kind was created/changed this session, and that
# restore step is a no-op (printed as "ok (not set this session)").
#
# --final additionally restores the sandbox image pin to IMAGE_PIN_L0 (recreating the
# container via `compose up -d`) and requires the restored image to be verified; without
# --final the container is only `compose start`-ed back up on its current (possibly
# DEV_PIN) image.
#
# Only sandbox endpoints are used (seedsyncarr-test, 127.0.0.1:8801) plus the seedbox
# (nyx.usbx.me, ~/v5test) strictly for synthetic-root cleanup when SYNTH_ROOTS is
# non-empty. Production (seedsyncarr) is never touched, never inspected, never named.
# The webhook secret value is never echoed or printed. Output is status words, counts
# and HTTP codes only. Exit 0 iff the last line is "SANDBOX_RESTORED ok".
#
# Idempotent: running this script twice in a row is safe -- every restore step first
# checks the live/restored value and only acts if it differs, and every step ends with
# a verifying read-back rather than trusting the write.
set -u

FINAL=0
POSITIONAL=()
for a in "$@"; do
  if [ "$a" = "--final" ]; then
    FINAL=1
  else
    POSITIONAL+=("$a")
  fi
done

D="${POSITIONAL[0]:-${D:-}}"
if [ -z "$D" ]; then
  D="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)"
fi

SSY="http://127.0.0.1:8801"
COMPOSE_FILE="/volume1/docker/v5test/docker-compose.yml"
SETTINGS_CFG="/volume1/docker/v5test/seedsyncarr/settings.cfg"
DOWNLOADS_ROOT="/downloads"
STAGING_ROOT="/downloads/.seedsyncarr-extracting"
SEEDBOX_HOST="nyx.usbx.me"
SEEDBOX_USER="jules1651"
SEEDBOX_ROOT="/home/jules1651/v5test"
SEEDBOX_STAGE="/home/jules1651/ssa122-stage"
COMPOSE="sudo /usr/local/bin/docker compose -f $COMPOSE_FILE"
DOCKER="sudo /usr/local/bin/docker"
ALLOWED_PREFIX="SSA122."

FAILED=""
fail() { FAILED="${FAILED}${FAILED:+,}$1"; }

state_get() {
  [ -n "$D" ] && [ -f "$D/state.env" ] || return 0
  grep -E "^$1=" "$D/state.env" | tail -n 1 | cut -d= -f2-
}
state_set() {
  # Append KEY=value; state_get's last-value-wins read picks this up on any later call.
  [ -n "$D" ] || return 0
  printf '%s=%s\n' "$1" "$2" >> "$D/state.env"
}

IMAGE_PIN_L0="$(state_get IMAGE_PIN_L0)"
RATE_LIMIT_L0="$(state_get RATE_LIMIT_L0)"
DELAY_L0="$(state_get DELAY_L0)"
RATE_LIMIT_SET="$(state_get RATE_LIMIT_SET)"
DELAY_SET="$(state_get DELAY_SET)"
WEBHOOK_SECRET_SET="$(state_get WEBHOOK_SECRET_SET)"
SYNTH_ROOTS="$(state_get SYNTH_ROOTS)"

# (1) lftp.rate_limit restore
if [ "$RATE_LIMIT_SET" = "1" ] && [ -n "$RATE_LIMIT_L0" ]; then
  have="$(curl -s --max-time 15 "$SSY/server/config/get" | jq -r '.lftp.rate_limit // empty' 2>/dev/null)"
  if [ "$have" != "$RATE_LIMIT_L0" ]; then
    curl -s --max-time 15 -o /dev/null -X POST -H "Content-Type: application/json" \
      -d "{\"section\":\"lftp\",\"key\":\"rate_limit\",\"value\":\"$RATE_LIMIT_L0\"}" \
      "$SSY/server/config/set"
    have="$(curl -s --max-time 15 "$SSY/server/config/get" | jq -r '.lftp.rate_limit // empty' 2>/dev/null)"
  fi
  if [ "$have" = "$RATE_LIMIT_L0" ]; then
    echo "RESTORED rate_limit ok"
    state_set RATE_LIMIT_SET 0
  else
    echo "RESTORED rate_limit FAIL"
    fail rate_limit
  fi
else
  echo "RESTORED rate_limit ok (not set this session)"
fi

# (2) autodelete.delay_seconds restore
if [ "$DELAY_SET" = "1" ] && [ -n "$DELAY_L0" ]; then
  have="$(curl -s --max-time 15 "$SSY/server/config/get" | jq -r '.autodelete.delay_seconds // empty' 2>/dev/null)"
  if [ "$have" != "$DELAY_L0" ]; then
    curl -s --max-time 15 -o /dev/null -X POST -H "Content-Type: application/json" \
      -d "{\"section\":\"autodelete\",\"key\":\"delay_seconds\",\"value\":\"$DELAY_L0\"}" \
      "$SSY/server/config/set"
    have="$(curl -s --max-time 15 "$SSY/server/config/get" | jq -r '.autodelete.delay_seconds // empty' 2>/dev/null)"
  fi
  if [ "$have" = "$DELAY_L0" ]; then
    echo "RESTORED delay_seconds ok"
    state_set DELAY_SET 0
  else
    echo "RESTORED delay_seconds FAIL"
    fail delay_seconds
  fi
else
  echo "RESTORED delay_seconds ok (not set this session)"
fi

# (3) synthetic root cleanup -- only touches names present in SYNTH_ROOTS, never any
# other path (the owner's own Hacks.S04E01 torrent under ~/v5test is never named here
# and is therefore never touched).
removed=0
refused=0
if [ -n "$SYNTH_ROOTS" ]; then
  OLDIFS="$IFS"
  IFS=,
  for name in $SYNTH_ROOTS; do
    IFS="$OLDIFS"
    [ -n "$name" ] || continue
    case "$name" in
      ${ALLOWED_PREFIX}*) ;;
      *)
        echo "REFUSED synth root (bad prefix): $name"
        refused=$((refused + 1))
        fail "synth_prefix:$name"
        continue
        ;;
    esac
    curl -s --max-time 15 -o /dev/null -X POST "$SSY/server/command/stop/$name"
    ssh -o ConnectTimeout=10 "${SEEDBOX_USER}@${SEEDBOX_HOST}" "rm -rf -- \"$SEEDBOX_ROOT/$name\"" 2>/dev/null
    $DOCKER exec "seedsyncarr-test" rm -rf -- "$DOWNLOADS_ROOT/$name" "$STAGING_ROOT/$name" 2>/dev/null

    present=0
    ssh -o ConnectTimeout=10 "${SEEDBOX_USER}@${SEEDBOX_HOST}" "[ -e \"$SEEDBOX_ROOT/$name\" ]" 2>/dev/null && present=1
    $DOCKER exec "seedsyncarr-test" sh -c "[ -e '$DOWNLOADS_ROOT/$name' ] || [ -e '$STAGING_ROOT/$name' ]" 2>/dev/null && present=1
    if [ "$present" = "0" ]; then
      removed=$((removed + 1))
    else
      echo "REMOVED synth root FAIL: $name"
      fail "synth_root:$name"
    fi
    IFS=,
  done
  IFS="$OLDIFS"
  ssh -o ConnectTimeout=10 "${SEEDBOX_USER}@${SEEDBOX_HOST}" "rm -rf -- \"$SEEDBOX_STAGE\"" 2>/dev/null
fi
echo "REMOVED synth roots count=$removed refused=$refused"

# (4) webhook_secret restore to empty (API 400s on an empty value -- see 122-RESEARCH.md
# Pitfall 1 -- so this is always a stop/edit-file/start, never a config API call).
if [ "$WEBHOOK_SECRET_SET" = "1" ] || [ "$FINAL" = "1" ]; then
  $COMPOSE stop seedsyncarr-test >/dev/null 2>&1
  running="$($DOCKER inspect seedsyncarr-test --format '{{.State.Running}}' 2>/dev/null)"
  if [ "$running" = "true" ]; then
    echo "STOP seedsyncarr-test FAIL (still running)"
    fail stop_container
  else
    echo "STOP seedsyncarr-test ok"
    tmp="$D/.settings.cfg.tmp.$$"
    awk '
      /^webhook_secret[[:space:]]*=/ { print "webhook_secret = "; next }
      { print }
    ' "$SETTINGS_CFG" > "$tmp"
    cat "$tmp" > "$SETTINGS_CFG"
    rm -f "$tmp"
    len="$(awk -F'= ' '/^webhook_secret/{print length($2)}' "$SETTINGS_CFG")"
    if [ "$len" = "0" ]; then
      echo "RESTORED webhook_secret ok (len=0)"
      state_set WEBHOOK_SECRET_SET 0
      rm -f "$D/secret"
    else
      echo "RESTORED webhook_secret FAIL (len=$len)"
      fail webhook_secret
    fi
  fi
else
  echo "RESTORED webhook_secret ok (not set this session)"
fi

# (5) image pin restore (--final only, inode-preserving edit) then bring the container
# back up; otherwise just restart it on its current image.
if [ "$FINAL" = "1" ]; then
  if [ -n "$IMAGE_PIN_L0" ]; then
    tmp="$D/.compose.yml.tmp.$$"
    awk -v pin="$IMAGE_PIN_L0" '
      /^[[:space:]]*image:[[:space:]]*ghcr\.io\/thejuran\/seedsyncarr[:@]/ && !done { sub(/image:.*/, "image: " pin); done=1 }
      { print }
    ' "$COMPOSE_FILE" > "$tmp"
    cat "$tmp" > "$COMPOSE_FILE"
    rm -f "$tmp"
    $COMPOSE pull seedsyncarr-test
    $COMPOSE up -d seedsyncarr-test
  else
    echo "IMAGE_PIN_L0 missing, cannot restore --final pin FAIL"
    fail image_pin_missing
  fi
else
  $COMPOSE start seedsyncarr-test
fi

# (6) wait for status, unsigned Test event (proves the secret is empty again), and in
# --final mode confirm the image pin is actually restored.
ok_status=0
for _ in $(seq 1 24); do
  code="$(curl -s --max-time 10 -o /dev/null -w '%{http_code}' "$SSY/server/status")"
  if [ "$code" = "200" ]; then
    ok_status=1
    break
  fi
  sleep 5
done
if [ "$ok_status" = "1" ]; then
  echo "WAIT server/status ok"
else
  echo "WAIT server/status FAIL"
  fail server_status
fi

test_code="$(curl -s --max-time 15 -o /dev/null -w '%{http_code}' -X POST -H "Content-Type: application/json" \
  -d '{"eventType":"Test"}' "$SSY/server/webhook/sonarr")"
if [ "$test_code" = "200" ]; then
  echo "CHECK webhook/sonarr Test http=200"
else
  echo "CHECK webhook/sonarr Test http=$test_code FAIL"
  fail webhook_test
fi

if [ "$FINAL" = "1" ]; then
  img="$($DOCKER inspect seedsyncarr-test --format '{{.Config.Image}}' 2>/dev/null)"
  if [ "$img" = "$IMAGE_PIN_L0" ]; then
    echo "CHECK image=restored ok"
  else
    echo "CHECK image=restored FAIL"
    fail image_restore
  fi
fi

if [ -z "$FAILED" ]; then
  echo "SANDBOX_RESTORED ok"
  exit 0
fi
echo "SANDBOX_RESTORED FAIL $FAILED"
exit 1
