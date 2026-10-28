#!/usr/bin/env bash
# Idempotent restore helper for the Phase 126 Release 1.8.0 sandbox smoke session
# (seedsyncarr-test).
#
# Usage (on the NAS):  bash teardown.sh [--revert-image] [<capture-dir>]   (or env D=<capture-dir>)
# When neither is given, the capture dir defaults to the directory containing this
# script (it is copied into the capture dir as teardown.sh).
#
# Reads <capture-dir>/state.env (KEY=value lines; parsed, never sourced), last value wins:
#   IMAGE_PIN_L0        original seedsyncarr-test image pin, recorded before any deploy
#   DEV_PIN             the digest-pinned release image this session deployed (informational)
#   SONARR_URL_L0       seedsyncarr-test's sonarr_url value recorded before any change
#   SONARR_URL_SET      1 if sonarr_url was changed this session and needs restoring
#   RADARR_URL_L0       seedsyncarr-test's radarr_url value recorded before any change
#   RADARR_URL_SET      1 if radarr_url was changed this session and needs restoring
#   RADARR_ENABLED_L0   seedsyncarr-test's radarr.enabled value recorded before any change
#   RADARR_ENABLED_SET  1 if radarr.enabled was changed this session and needs restoring
#   SONARR_KEY_SET      1 if sonarr_api_key was changed this session; original value lives
#                        only in the 0600 file <capture-dir>/sonarr_key.l0
#   RADARR_KEY_SET      1 if radarr_api_key was changed this session; original value lives
#                        only in the 0600 file <capture-dir>/radarr_key.l0
#   SYNTH_ROOTS         space-separated synthetic root names created this session, every
#                        name required to start with "SSA126." (refused otherwise)
#   PROBE_CONTAINERS    space-separated throwaway container names created this session,
#                        every name required to start with "seedsyncarr-probe126"
#   PROBE_DIRS          space-separated throwaway scratch dirs created this session, every
#                        path required to start with "/volume1/docker/probe126-"
# A missing key means nothing of that kind was created/changed this session, and that
# restore step is a no-op (printed as "ok (not set this session)").
#
# --revert-image additionally restores the sandbox image pin to IMAGE_PIN_L0
# (inode-preserving compose edit, then `compose pull` + `compose up -d`) and requires the
# restored image to be verified; without --revert-image the container is only
# `compose start`-ed if not running, and the sandbox stays on whatever image it currently
# runs (the sandbox is allowed to stay on the published 1.8.0 release tag). The current
# image reference is always printed, with or without the flag.
#
# Scope: only seedsyncarr-test, 127.0.0.1:8801 and this session's own synthetic roots
# (SSA126.*) / throwaway probe containers+dirs are touched. Production is never touched
# or named anywhere in this script. No `*_api_key`, `*_password`, `*_secret` or
# `api_token` field is ever read in full or printed -- every config read is filtered with
# jq to exactly one named field. Output is status words, counts and HTTP codes only.
#
# Idempotent: running this script twice in a row is safe -- every restore step first
# checks the live/restored value and only acts if it differs, and every step ends with
# a verifying read-back rather than trusting the write.
set -u

REVERT_IMAGE=0
POSITIONAL=()
for a in "$@"; do
  if [ "$a" = "--revert-image" ]; then
    REVERT_IMAGE=1
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
DOWNLOADS_ROOT="/downloads"
STAGING_ROOT="/downloads/.seedsyncarr-extracting"
SEEDBOX_HOST="nyx.usbx.me"
SEEDBOX_USER="jules1651"
SEEDBOX_ROOT="/home/jules1651/v5test"
SEEDBOX_STAGE="/home/jules1651/ssa126-stage"
COMPOSE="sudo /usr/local/bin/docker compose -f $COMPOSE_FILE"
DOCKER="sudo /usr/local/bin/docker"
ALLOWED_PROBE_CONTAINER_PREFIX="seedsyncarr-probe126"
ALLOWED_PROBE_DIR_PREFIX="/volume1/docker/probe126-"

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
SONARR_URL_L0="$(state_get SONARR_URL_L0)"
SONARR_URL_SET="$(state_get SONARR_URL_SET)"
RADARR_URL_L0="$(state_get RADARR_URL_L0)"
RADARR_URL_SET="$(state_get RADARR_URL_SET)"
RADARR_ENABLED_L0="$(state_get RADARR_ENABLED_L0)"
RADARR_ENABLED_SET="$(state_get RADARR_ENABLED_SET)"
SONARR_KEY_SET="$(state_get SONARR_KEY_SET)"
RADARR_KEY_SET="$(state_get RADARR_KEY_SET)"
SYNTH_ROOTS="$(state_get SYNTH_ROOTS)"
PROBE_CONTAINERS="$(state_get PROBE_CONTAINERS)"
PROBE_DIRS="$(state_get PROBE_DIRS)"

get_sonarr_url() {
  curl -s --max-time 15 "$SSY/server/config/get" | jq -r '.sonarr.sonarr_url // empty'
}
set_sonarr_url() {
  local value="$1" body
  body="$(jq -n --arg v "$value" '{section:"sonarr",key:"sonarr_url",value:$v}')"
  curl -s --max-time 15 -o /dev/null -X POST -H "Content-Type: application/json" \
    -d "$body" "$SSY/server/config/set"
}

get_radarr_url() {
  curl -s --max-time 15 "$SSY/server/config/get" | jq -r '.radarr.radarr_url // empty'
}
set_radarr_url() {
  local value="$1" body
  body="$(jq -n --arg v "$value" '{section:"radarr",key:"radarr_url",value:$v}')"
  curl -s --max-time 15 -o /dev/null -X POST -H "Content-Type: application/json" \
    -d "$body" "$SSY/server/config/set"
}

get_radarr_enabled() {
  # NOT `.radarr.enabled // empty`: jq's `//` treats boolean `false` as falsy too, so
  # that idiom silently returns "" whenever radarr is actually disabled -- making a
  # correct restore-to-false permanently unverifiable (always reads back as "" and
  # compares unequal to the literal string "false"). Use an explicit null check instead.
  curl -s --max-time 15 "$SSY/server/config/get" | jq -r 'if .radarr.enabled == null then "" else (.radarr.enabled|tostring) end'
}
set_radarr_enabled() {
  local value="$1" body
  body="$(jq -n --arg v "$value" '{section:"radarr",key:"enabled",value:$v}')"
  curl -s --max-time 15 -o /dev/null -X POST -H "Content-Type: application/json" \
    -d "$body" "$SSY/server/config/set"
}

# Build a value-free config/set body for one *arr API key from a 0600 L0 file (never
# printing the value itself) and POST it. Uses `-nR`/`[inputs]` (reads every stdin line
# as a raw string, joined back with "\n") rather than `--rawfile`, which the NAS's jq
# 1.5 does not support (added in jq 1.6) -- same value-never-in-argv guarantee either
# way. `[inputs]` (not a single `input`) is required so an EMPTY file -- restoring a
# key that was never set, e.g. radarr's key when radarr started this session disabled
# -- yields zero lines and therefore value:"" instead of jq raising "break" on `input`
# finding nothing to read.
post_arr_key() {
  local section="$1" key="$2" file="$3" tmp
  tmp="$D/.${section}_key.body.$$.json"
  jq -nR --arg section "$section" --arg key "$key" \
    '{section:$section,key:$key,value:([inputs]|join("\n"))}' < "$file" > "$tmp"
  chmod 0600 "$tmp"
  curl -s --max-time 15 -o /dev/null -X POST -H "Content-Type: application/json" \
    -d @"$tmp" "$SSY/server/config/set"
  rm -f "$tmp"
}

# (1) image pin: --revert-image rewrites the compose line and recreates the container;
# otherwise the container is only started if it is not already running (the sandbox is
# allowed to stay on the published 1.8.0 release tag between sessions).
if [ "$REVERT_IMAGE" = "1" ]; then
  if [ -n "$IMAGE_PIN_L0" ]; then
    tmp="$D/.compose.yml.tmp.$$"
    before_inode="$(stat -c %i "$COMPOSE_FILE" 2>/dev/null)"
    awk -v pin="$IMAGE_PIN_L0" '
      /^[[:space:]]*image:[[:space:]]*ghcr\.io\/thejuran\/seedsyncarr[:@]/ && !done { sub(/image:.*/, "image: " pin); done=1 }
      { print }
    ' "$COMPOSE_FILE" > "$tmp"
    cat "$tmp" > "$COMPOSE_FILE"
    rm -f "$tmp"
    after_inode="$(stat -c %i "$COMPOSE_FILE" 2>/dev/null)"
    echo "INODE before=$before_inode after=$after_inode"
    if [ "$before_inode" != "$after_inode" ]; then
      echo "INODE mismatch FAIL"
      fail inode_mismatch
    fi
    $COMPOSE pull seedsyncarr-test
    $COMPOSE up -d seedsyncarr-test
  else
    echo "IMAGE_PIN_L0 missing, cannot revert-image pin FAIL"
    fail image_pin_missing
  fi
else
  running="$($DOCKER inspect seedsyncarr-test --format '{{.State.Running}}' 2>/dev/null)"
  if [ "$running" != "true" ]; then
    $COMPOSE start seedsyncarr-test
  fi
fi

# (2) wait for /server/status 200
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

img_now="$($DOCKER inspect seedsyncarr-test --format '{{.Config.Image}}' 2>/dev/null)"
echo "IMAGE current=$img_now"

# (3) sonarr_url restore. If SONARR_URL_SET=1 but the original (L0) value was itself
# empty, no restore POST is attempted: ConfigHandler.__handle_set_config rejects any
# request with an empty "value" (400 by design, D-06) regardless of field, so a
# value:"" POST can never succeed for ANY field -- not just the api-key ones. Report
# this plainly instead of the misleading "not set this session" (it WAS set).
if [ "$SONARR_URL_SET" = "1" ] && [ -z "$SONARR_URL_L0" ]; then
  echo "RESTORED sonarr_url ok (original was empty; API cannot clear a URL value, left as currently set)"
  state_set SONARR_URL_SET 0
elif [ "$SONARR_URL_SET" = "1" ] && [ -n "$SONARR_URL_L0" ]; then
  have="$(get_sonarr_url)"
  if [ "$have" != "$SONARR_URL_L0" ]; then
    set_sonarr_url "$SONARR_URL_L0"
    have="$(get_sonarr_url)"
  fi
  if [ "$have" = "$SONARR_URL_L0" ]; then
    echo "RESTORED sonarr_url ok"
    state_set SONARR_URL_SET 0
  else
    echo "RESTORED sonarr_url FAIL"
    fail sonarr_url
  fi
else
  echo "RESTORED sonarr_url ok (not set this session)"
fi

# (4) radarr_url restore (same empty-original handling as sonarr_url above)
if [ "$RADARR_URL_SET" = "1" ] && [ -z "$RADARR_URL_L0" ]; then
  echo "RESTORED radarr_url ok (original was empty; API cannot clear a URL value, left as currently set)"
  state_set RADARR_URL_SET 0
elif [ "$RADARR_URL_SET" = "1" ] && [ -n "$RADARR_URL_L0" ]; then
  have="$(get_radarr_url)"
  if [ "$have" != "$RADARR_URL_L0" ]; then
    set_radarr_url "$RADARR_URL_L0"
    have="$(get_radarr_url)"
  fi
  if [ "$have" = "$RADARR_URL_L0" ]; then
    echo "RESTORED radarr_url ok"
    state_set RADARR_URL_SET 0
  else
    echo "RESTORED radarr_url FAIL"
    fail radarr_url
  fi
else
  echo "RESTORED radarr_url ok (not set this session)"
fi

# (5) radarr_enabled restore
if [ "$RADARR_ENABLED_SET" = "1" ] && [ -n "$RADARR_ENABLED_L0" ]; then
  have="$(get_radarr_enabled)"
  if [ "$have" != "$RADARR_ENABLED_L0" ]; then
    set_radarr_enabled "$RADARR_ENABLED_L0"
    have="$(get_radarr_enabled)"
  fi
  if [ "$have" = "$RADARR_ENABLED_L0" ]; then
    echo "RESTORED radarr_enabled ok"
    state_set RADARR_ENABLED_SET 0
  else
    echo "RESTORED radarr_enabled FAIL"
    fail radarr_enabled
  fi
else
  echo "RESTORED radarr_enabled ok (not set this session)"
fi

# (6) sonarr_api_key restore (value-free; see post_arr_key above). The original key
# lives only in the 0600 file $D/sonarr_key.l0, written by the smoke session before it
# changes the key; compared via a single-field jq read, never the full config response.
# If the original (want) was itself empty -- sonarr had no key configured before this
# session -- no restore POST is attempted: ConfigHandler.__handle_set_config rejects
# any request with an empty "value" (400, by design, D-06), so a value:"" POST can
# never succeed. This is the same documented no-restore-to-empty-path limitation as
# webhook_secret (see "Webhook secret" above) -- recorded, not treated as a failure.
SONARR_KEY_FILE="$D/sonarr_key.l0"
if [ "$SONARR_KEY_SET" = "1" ] && [ -f "$SONARR_KEY_FILE" ]; then
  want="$(cat "$SONARR_KEY_FILE")"
  if [ -z "$want" ]; then
    echo "RESTORED sonarr_api_key ok (original was empty; API cannot clear a key value, left as currently set)"
    state_set SONARR_KEY_SET 0
    rm -f "$SONARR_KEY_FILE"
  else
    have="$(curl -s --max-time 15 "$SSY/server/config/get" | jq -r '.sonarr.sonarr_api_key // empty')"
    if [ "$have" != "$want" ]; then
      post_arr_key sonarr sonarr_api_key "$SONARR_KEY_FILE"
      have="$(curl -s --max-time 15 "$SSY/server/config/get" | jq -r '.sonarr.sonarr_api_key // empty')"
    fi
    if [ "$have" = "$want" ]; then
      echo "RESTORED sonarr_api_key ok"
      state_set SONARR_KEY_SET 0
      rm -f "$SONARR_KEY_FILE"
    else
      echo "RESTORED sonarr_api_key FAIL"
      fail sonarr_api_key
    fi
  fi
else
  echo "RESTORED sonarr_api_key ok (not set this session)"
fi

# (7) radarr_api_key restore (same value-free pattern and same empty-original handling
# as sonarr_api_key above)
RADARR_KEY_FILE="$D/radarr_key.l0"
if [ "$RADARR_KEY_SET" = "1" ] && [ -f "$RADARR_KEY_FILE" ]; then
  want="$(cat "$RADARR_KEY_FILE")"
  if [ -z "$want" ]; then
    echo "RESTORED radarr_api_key ok (original was empty; API cannot clear a key value, left as currently set)"
    state_set RADARR_KEY_SET 0
    rm -f "$RADARR_KEY_FILE"
  else
    have="$(curl -s --max-time 15 "$SSY/server/config/get" | jq -r '.radarr.radarr_api_key // empty')"
    if [ "$have" != "$want" ]; then
      post_arr_key radarr radarr_api_key "$RADARR_KEY_FILE"
      have="$(curl -s --max-time 15 "$SSY/server/config/get" | jq -r '.radarr.radarr_api_key // empty')"
    fi
    if [ "$have" = "$want" ]; then
      echo "RESTORED radarr_api_key ok"
      state_set RADARR_KEY_SET 0
      rm -f "$RADARR_KEY_FILE"
    else
      echo "RESTORED radarr_api_key FAIL"
      fail radarr_api_key
    fi
  fi
else
  echo "RESTORED radarr_api_key ok (not set this session)"
fi

# (8) synthetic root cleanup -- only touches names present in SYNTH_ROOTS and matching
# the required ^SSA126\. prefix; never any other path.
removed=0
refused=0
if [ -n "$SYNTH_ROOTS" ]; then
  for name in $SYNTH_ROOTS; do
    if [[ ! "$name" =~ ^SSA126\. ]]; then
      echo "REFUSED synth root (bad prefix): $name"
      refused=$((refused + 1))
      fail "synth_prefix:$name"
      continue
    fi
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
  done
  ssh -o ConnectTimeout=10 "${SEEDBOX_USER}@${SEEDBOX_HOST}" "rm -rf -- \"$SEEDBOX_STAGE\"" 2>/dev/null
fi
echo "REMOVED synth roots count=$removed refused=$refused"

# (9) throwaway probe container + scratch dir cleanup (token-probe positive control)
probe_c_removed=0
probe_c_refused=0
if [ -n "$PROBE_CONTAINERS" ]; then
  for name in $PROBE_CONTAINERS; do
    case "$name" in
      ${ALLOWED_PROBE_CONTAINER_PREFIX}*)
        $DOCKER rm -f "$name" >/dev/null 2>&1
        if $DOCKER inspect "$name" >/dev/null 2>&1; then
          echo "REMOVED probe container FAIL: $name"
          fail "probe_container:$name"
        else
          probe_c_removed=$((probe_c_removed + 1))
        fi
        ;;
      *)
        echo "REFUSED probe container (bad prefix): $name"
        probe_c_refused=$((probe_c_refused + 1))
        fail "probe_container_prefix:$name"
        ;;
    esac
  done
fi
echo "REMOVED probe containers count=$probe_c_removed refused=$probe_c_refused"

probe_d_removed=0
probe_d_refused=0
if [ -n "$PROBE_DIRS" ]; then
  for dir in $PROBE_DIRS; do
    case "$dir" in
      ${ALLOWED_PROBE_DIR_PREFIX}*)
        # No sudo here: the NAS's passwordless sudoers rule only covers the
        # docker/docker-compose binaries (absolute path), so a non-interactive
        # `sudo rm` would hang/fail waiting for a password. These dirs are
        # created by this same user (mkdir, no sudo) and the throwaway
        # container's PUID/PGID maps its writes to the same uid/gid, so a
        # plain rm -rf always has permission.
        rm -rf -- "$dir" 2>/dev/null
        if [ -e "$dir" ]; then
          echo "REMOVED probe dir FAIL: $dir"
          fail "probe_dir:$dir"
        else
          probe_d_removed=$((probe_d_removed + 1))
        fi
        ;;
      *)
        echo "REFUSED probe dir (bad prefix): $dir"
        probe_d_refused=$((probe_d_refused + 1))
        fail "probe_dir_prefix:$dir"
        ;;
    esac
  done
fi
echo "REMOVED probe dirs count=$probe_d_removed refused=$probe_d_refused"

# (10) --revert-image image restore verification
if [ "$REVERT_IMAGE" = "1" ]; then
  if [ "$img_now" = "$IMAGE_PIN_L0" ]; then
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
