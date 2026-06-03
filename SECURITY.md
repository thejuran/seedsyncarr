# Security Policy

## Supported Versions

The following versions of SeedSyncarr receive security updates:

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue, please report it responsibly.

### How to Report

1. **Do not** open a public GitHub issue for security vulnerabilities
2. Use the GitHub private security advisory: **[Report a vulnerability](https://github.com/thejuran/seedsyncarr/security/advisories/new)**
3. Include the following information:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### What to Expect

- **Acknowledgment**: Within 48 hours of your report
- **Initial assessment**: Within 1 week
- **Resolution timeline**: Depends on severity, typically 2-4 weeks for critical issues

### Disclosure Policy

- We will work with you to understand and resolve the issue
- We request that you give us reasonable time to address the vulnerability before public disclosure
- We will credit you in the security advisory (unless you prefer to remain anonymous)

## Security posture

SeedSyncarr is designed to be self-hosted on a private network, and several protections are active by default:

- **Encrypted secrets at rest** — API tokens, webhook secrets, and *arr API keys are Fernet-encrypted in the config file (AES-128-CBC + HMAC-SHA256); the keyfile is created with restrictive (0600) permissions on first enable.
- **HMAC-verified import webhooks** — Sonarr/Radarr webhook payloads are HMAC-SHA256 verified when a secret is configured; a missing or invalid signature is rejected with 401. Enable `webhook_require_secret = true` (opt-in) to fail-closed: when the requirement is on but no `webhook_secret` is set, every call is rejected with 503 (a configuration guard, since there is no secret to verify against).
- **Bearer auth** — The `/server/*` API requires a Bearer token when `api_token` is set (constant-time compare; allow-all when unset for backward compatibility). Set `api_token` for any non-loopback bind. Note that the web UI shell is served on the same address and carries the token so the in-browser app can call the API; `api_token` gates the API, not network reachability of the UI — put SeedSyncarr behind an authenticating reverse proxy for any untrusted network.
- **IP-resolution guard on *arr connection URLs** — When you test or connect a Sonarr/Radarr server, the user-supplied URL is resolved via `socket.getaddrinfo` and rejected if it points to a private, loopback, reserved, or link-local IP. This is an IP-resolution SSRF guard on the *arr connection URL (not a full SSRF library; DNS-rebinding/TOCTOU is a documented out-of-scope limitation for a homelab tool). SeedSyncarr *receives* import webhooks; it does not send outbound webhooks.
- **CSP headers** — A Content Security Policy header is sent on all responses, layered with Angular's hash-based meta CSP.
- **Rate limiting** — The following endpoints carry rate-limiting decorators: the Sonarr/Radarr webhook endpoints (60 req/60s), the POST config-set endpoint (60 req/60s), the Sonarr/Radarr test-connection endpoints (5 req/60s), the bulk-command endpoint (10 req/60s), and the status endpoint (60 req/60s). Single-file command endpoints, the server-restart endpoint, and autoqueue endpoints are not rate-limited.
- **Log-injection protection** — File names are sanitized for CR/LF and control characters before reaching log lines (CWE-117).

**This is not a substitute for network isolation.** Place SeedSyncarr behind a reverse proxy with authentication if you expose it beyond localhost.

## Security Best Practices for Users

When deploying SeedSyncarr:

1. **Keep SeedSyncarr updated** to the latest version
2. **Use strong passwords** for SSH connections to your remote server
3. **Restrict network access** to the SeedSyncarr web UI (use a reverse proxy with authentication if exposing to the internet)
4. **Use SSH keys** instead of passwords when possible
5. **Review file permissions** on your local download directory
