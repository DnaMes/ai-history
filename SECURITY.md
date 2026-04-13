# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 2.x     | ✅ Yes    |
| < 2.0   | ❌ No     |

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Report security issues by opening a [GitHub Security Advisory](https://github.com/YOUR-ORG/ai-history/security/advisories/new) (preferred), or by emailing the maintainers directly.

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

You will receive a response within 72 hours. If confirmed, a patch will be released as soon as possible.

## Scope

This tool runs **entirely local** — it reads AI tool config directories on your machine and serves a local web UI. There is no cloud connectivity, no authentication server, and no data leaves your machine unless you explicitly deploy it behind a reverse proxy.

Known limitations:
- The web UI has no built-in authentication. If you expose it publicly, use a reverse proxy with Basic Auth or similar.
- PostgreSQL and Redis credentials in `docker-compose.yml` use a default value. Change `POSTGRES_PASSWORD` in your `.env` file before any networked deployment.
