# Security Policy

## Supported Versions

Security updates are provided for the latest commit on the `main` branch.

## Reporting a Vulnerability

Please do not open public issues for security vulnerabilities.

Send a private report with steps to reproduce, impact, and affected files to:
- GitHub Security Advisories (preferred)
- Repository owner: `vuquangvinh1004`

We will acknowledge reports within 72 hours and provide an estimated timeline for remediation.

## Sensitive Data Rules

This project is offline-first and may contain local user data during runtime.
Do not commit or publish any sensitive local data, including:
- database files (`*.db`, `*.sqlite`, `*.sqlite3`)
- logs, backups, temporary exports
- `.env` and secret keys

Automated guards are enabled in pre-commit and CI to block these files.
