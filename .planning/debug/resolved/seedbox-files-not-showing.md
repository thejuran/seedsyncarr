---
status: resolved
trigger: "files on seedbox not showing in seedsyncarr"
created: 2026-06-21
updated: 2026-06-21
human_verified: "2026-06-21 — user confirmed file list refreshed and new seedbox files visible in UI"
follow_up: "Auto-recovery gap (scanner dies on permanent-class error with no restart) routed to a planned fix — see .planning/ phase for scanner-auto-recovery."
---

# Debug Session: seedbox-files-not-showing

## Symptoms

- **Expected behavior:** Files present on the seedbox (remote source path) should appear in the seedsyncarr UI file list as the remote scanner discovers them. Newly-added remote files should show up within a scan cycle.
- **Actual behavior:** Stale list, not updating. Some older files show, but newly-added seedbox files never appear no matter how long you wait — the list looks frozen.
- **Error messages:** Unknown — user has not checked container logs/status yet. KEY first investigative move: inspect live `seedsyncarr` container on maguffynas (logs, /server/status, scanner activity).
- **App state:** UI not yet checked for scan errors; responsiveness unknown.
- **Timeline:** Worked before, broke recently. File discovery was functioning, then stopped — possibly after the 2026-06-08 permissions fix/restart or a subsequent redeploy.
- **Reproduction:** Add (or expect) new files on the seedbox remote path; they never appear in the seedsyncarr list.

## Relationship to prior resolved sessions

This is the UPSTREAM / DISCOVERY layer — distinct from the recently resolved download-layer
session.

- `active-files-not-downloading.md` (resolved 2026-06-08): DOWNSTREAM. Files were KNOWN to the
  model but LFTP could not WRITE them locally (Synology ACL made `/downloads` read-only to
  container uid 1000). That was a local-write permissions issue. NOT this — here files never
  appear in the model at all, so the download layer is not the suspect.
- `hold-the-dream-not-syncing.md` (resolved 2026-05-05): UPSTREAM scanner bug — failed remote
  scans wiped/froze the remote model; silent scanner process death. THIS symptom (stale list,
  not updating, regression) closely matches that signature. Re-read that resolved session FIRST;
  the root cause or a regression of it is a strong candidate.

## Key area to investigate first

1. LIVE NAS FIRST (the prior session's lesson: don't theorize before inspecting the running
   instance). `ssh nas`, then `sudo /usr/local/bin/docker logs seedsyncarr` (tail), check
   `/server/status`, and look for scanner cycle activity vs. silence/errors.
2. Remote scanner: src/python/controller/ scan/scanner components — does the remote SFTP scan
   still run, succeed, and update the model? Look for silent scanner death, swallowed scan
   exceptions, or a scan that fails and leaves the model stale (the hold-the-dream pattern).
3. Remote connectivity/path: confirm the seedbox SFTP scan can still reach
   `remote_path = /home/jules1651/downloads/deluge2/done` and list it (auth, host key, path
   existence). A scan that errors but does not crash could freeze the list.
4. Regression window: changes since 2026-06-08 (the permissions fix / restart) or any redeploy
   that could have affected the scanner or remote config.

## Current Focus

reasoning_checkpoint:
  hypothesis: "On 2026-06-19 02:44:51, the remote scanner process (RemoteScanner) failed to SSH
    into moon.usbx.me because SSH output matched 'Could not resolve hostname' or
    'Name or service not known' — pexpect pattern index 3 or 5 in sshcp.py. This raised
    SshcpError('Bad hostname: moon.usbx.me'), which RemoteScanner classified as a permanent
    error (PERMANENT_ERROR_PATTERNS match), wrapped it in ScannerError(recoverable=False),
    and re-raised. ScannerProcess.run_loop() re-raised the non-recoverable ScannerError, which
    propagated up through propagate_exception() in scan_manager.py and then controller.py, and
    was finally caught in seedsyncarr.py line 184 as AppError — marking the controller as down
    (status.server.up=False) but NOT restarting it. The scanner child process died, the web
    server child (webapp_job) kept running, and the health-check GET / loop never stopped.
    The list has been frozen since then: 2 days and ~3 hours."
  confirming_evidence:
    - "Log at 2026-06-19 02:44:51: ScannerError: 'Bad hostname: moon.usbx.me' — exact
      PERMANENT_ERROR_PATTERNS match in sshcp.py line 98/129."
    - "Log shows traceback: scanner_process.py:90 scan() -> remote_scanner.py:108 ScannerError
      -> scan_manager.py:165 propagate_exception() -> controller.py:755/__propagate_exceptions
      -> controller_job.py:24 execute() -> seedsyncarr.py:183 caught as AppError, NOT re-raised
      (context.args.exit=False, so controller stops but app stays up — lines 185-190)."
    - "Since 2026-06-19 02:44, ALL 2000+ logged lines are web_access only (health-check pings
      every ~2 min from python-httpx/0.28.1). Zero scanner activity. Zero controller logs.
      Zero MemoryMonitor logs after the crash. Web server running, controller dead."
    - "moon.usbx.me resolves NOW from the NAS (nslookup returns 46.232.210.200). Likely a
      brief DNS outage or seedbox maintenance window at 02:44 on 2026-06-19 caused the
      transient hostname resolution failure — but the code treats any hostname error as permanent."
    - "Config confirms remote_address = moon.usbx.me — the hostname in the error matches
      the configured address exactly."
  falsification_test: "If the hypothesis is wrong, the MemoryMonitor logs would still appear
    after 2026-06-19 02:44 (they don't), OR the container logs would show a scanner restart
    (they don't), OR the error pattern would be something other than Bad hostname (it isn't)."
  fix_rationale: "The fix is a container restart. The controller thread has exited; the scanner
    process is dead. There is no code path to restart them short of restarting the container.
    The root cause is the DNS blip that triggered a 'Bad hostname' permanent error during a
    transient condition — a code-level fix (treating hostname errors as transient rather than
    permanent, or adding auto-restart logic after permanent errors) is a future improvement,
    but the immediate unblock is container restart, which clears the dead controller state.
    DNS resolves fine now, so the scanner will succeed on restart."
  blind_spots: "Did not confirm whether the DNS blip was seedbox-side or NAS-side. It does not
    matter for the immediate fix — restart will recover regardless of which side had the hiccup."
next_action: restart the seedsyncarr container on maguffynas

## Evidence

- timestamp: 2026-06-21 user report
  content: "files on seedbox not showing in seedsyncarr — stale list, not updating; older files
    show but new ones never appear; worked before, broke recently; logs not yet checked."

- timestamp: 2026-06-21 live log inspection
  checked: "docker logs --tail 2000 seedsyncarr (filtered to non-web-access)"
  found: "Last non-web-access log at 2026-06-19 02:44:51 — ScannerError: 'Bad hostname:
    moon.usbx.me'. Full traceback: scanner_process.py:90 -> remote_scanner.py:108 ->
    scan_manager.py:165 -> controller.py:755 -> controller_job.py:24 -> seedsyncarr.py:183
    caught as AppError. After that: only web_access GET / health pings every ~2min.
    No MemoryMonitor, no scanner, no controller logs for 2+ days."
  implication: "Controller job died at 02:44:51 2026-06-19. Web server stayed alive.
    Seedsyncarr.run() line 184 caught the AppError, set status.server.up=False, logged it,
    and kept running WITHOUT restarting the controller. Scanner has been dead for 2+ days."

- timestamp: 2026-06-21 live config read
  checked: "docker exec seedsyncarr cat /config/settings.cfg"
  found: "remote_address = moon.usbx.me — matches the error exactly."
  implication: "This is the configured hostname. No misconfiguration; the hostname was temporarily
    unresolvable at the time of the failure."

- timestamp: 2026-06-21 DNS check from NAS
  checked: "nslookup moon.usbx.me from NAS"
  found: "Resolves to 46.232.210.200 now. DNS is fine."
  implication: "The hostname failure was transient. The host is reachable now.
    Container restart will let the scanner reconnect successfully."

- timestamp: 2026-06-21 code inspection
  checked: "sshcp.py PERMANENT_ERROR_PATTERNS, scanner_process.py recoverable flag,
    remote_scanner.py permanent error classification, seedsyncarr.py AppError catch"
  found: "'Bad hostname:' is in PERMANENT_ERROR_PATTERNS. RemoteScanner._is_permanent_ssh_error()
    returns True. ScannerError(recoverable=False) raised. scanner_process.py:96-98: non-recoverable
    re-raises immediately. seedsyncarr.py:184: AppError caught, controller marked down,
    NO restart attempted."
  implication: "By design, 'Bad hostname' is treated as permanent/fatal to avoid infinite retry
    loops on genuinely wrong config. But a transient DNS blip at the seedbox provider during a
    scan window triggers the same path. The controller dies and never recovers without a restart."

## Eliminated

- hold-the-dream pattern (scanner process died silently, scan_manager.propagate_exceptions
  health check not detecting it): ELIMINATED. The hold-the-dream fix IS working — the error
  DID propagate correctly (traceback visible in logs). The problem is what happens AFTER
  propagation: permanent errors kill the controller job without restart.

- Remote host key changed: ELIMINATED. Error is specifically 'Bad hostname', not 'Remote host
  key has changed'.

- Config error (wrong remote_address): ELIMINATED. moon.usbx.me resolves correctly now;
  the 2026-06-19 failure was a transient DNS blip.

- Download-layer (permissions) regression from 2026-06-08 fix: ELIMINATED. This is purely
  the upstream discovery layer; the error is at the SSH scan stage, not LFTP write.

## Resolution

root_cause: "Transient DNS resolution failure for moon.usbx.me at 2026-06-19 02:44:51 triggered
  SshcpError('Bad hostname: moon.usbx.me'), which the scanner classified as a permanent
  (non-recoverable) error. The scanner process re-raised, propagated through the controller
  thread, and was caught in seedsyncarr.py as AppError — marking the controller down without
  restarting it. The web server stayed alive. The scanner has been dead for 2+ days. The fix
  is container restart; moon.usbx.me resolves now so the scanner will reconnect on restart."
fix: "Restarted seedsyncarr container via: ssh nas 'cd /volume1/docker && sudo /usr/local/bin/docker compose restart seedsyncarr'"
verification: "Post-restart logs at 16:48:38 confirm:
  - RemoteScanner completed scan ('Skipping remote scanfs installation: already installed') within 2s
  - MemoryMonitor logging resumed
  - AutoQueue picked up 7 new files immediately (John Wick 2014, That.Mitchell.and.Webb.Look.S04,
    Inside.Llewyn.Davis, Lolita.1962, Barbie.2023, Celebrity.Gogglebox, John Wick 2014 HDR)
  - Controller processing queue commands
  - DNS resolves fine: moon.usbx.me -> 46.232.210.200
  SELF-VERIFIED: scanner running, controller alive, new files discovered.
  AWAITING USER: confirm files visible in UI."
files_changed: []
