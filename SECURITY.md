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
2. Email the maintainer at: **thejuran@users.noreply.github.com**
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

## Security Best Practices for Users

When deploying SeedSyncarr:

1. **Keep SeedSyncarr updated** to the latest version
2. **Use strong passwords** for SSH connections to your remote server
3. **Restrict network access** to the SeedSyncarr web UI (use a reverse proxy with authentication if exposing to the internet)
4. **Use SSH keys** instead of passwords when possible
5. **Review file permissions** on your local download directory
