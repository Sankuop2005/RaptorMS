# Security Policy

The Raptor Esports Portal team takes the security of our platform, user accounts, and competitive data seriously. This document outlines our supported versions, vulnerability reporting process, response timelines, and responsible disclosure practices.

## Supported Versions

We provide security updates and patches for active release branches. The table below details currently supported versions:

| Version | Supported | Release Date | Support Level |
|---------|-----------|--------------|---------------|
| 1.0.x   | Yes       | 2026-10-25   | Active security maintenance and bug fixes |
| < 1.0.0 | No        | N/A          | Unsupported legacy development builds |

## Reporting a Vulnerability

If you discover a security vulnerability or potential threat in the Raptor Esports Portal, please report it privately rather than opening a public issue on GitHub.

**Primary Security Contact:**  
`security@raptor.local`

### What to Include in Your Report

To help us investigate and resolve the issue efficiently, please include:
1. **Summary**: A clear and concise overview of the vulnerability.
2. **Impact**: Potential consequences if exploited (e.g., privilege escalation, unauthorized data access, denial of service).
3. **Affected Components**: Specific files, routes, or modules involved (for example, `server.py`, `ai_assistant.py`, `rbac.py`, `db.py`, or `/api/entities/*`).
4. **Steps to Reproduce**: Detailed, step-by-step instructions or a minimal proof-of-concept (PoC) payload.
5. **Mitigation Suggestions**: Any recommended patches or configurations that could mitigate the flaw, if known.

Please do not disclose or discuss the vulnerability publicly until a fix has been reviewed, released, and verified.

## Service Level Agreements (SLA) & Timeline

We commit to the following response schedule for all reported security vulnerabilities:

* **Initial Acknowledgment**: Within 48 hours of receiving your report, confirming receipt and assigning a security responder.
* **Triage & Severity Assessment**: Within 5 calendar days, validating reproduction steps and assigning a CVSS score.
* **Patch Release**: Within 14 calendar days for confirmed Critical and High severity issues, with an official update deployed to the main repository.
* **Coordinated Disclosure**: Publication of a security advisory and acknowledgement of the finder (unless anonymity is requested) following patch deployment.

## Core Security Architecture & Safeguards

The Raptor Esports Portal is architected with defense-in-depth principles:

* **Zero External Pip Dependencies**: Eliminates supply chain attacks and third-party dependency vulnerabilities by relying exclusively on the Python standard library.
* **Credential Protection**: Passwords hashed using PBKDF2-HMAC-SHA256 with unique random salts and 310,000 iterations. Constant-time dummy verification prevents timing attacks on unknown usernames.
* **Session Hardening**: 64-character hexadecimal session tokens stored in SQLite with strict 12-hour expiration, `HttpOnly`, `SameSite=Strict`, and `Path=/` cookie flags.
* **CSRF Protection**: High-entropy URL-safe base64 anti-CSRF tokens required for all state-changing HTTP methods (`POST`, `PUT`, `DELETE`), verified via constant-time `hmac.compare_digest`.
* **Fine-Grained RBAC**: Explicit 5-role hierarchy (`Admin`, `Manager`, `Coach`, `Analyst`, `Player`) with 29 atomic permissions and resource scoping (`all`, `assigned`, `own`). Self-privilege modification and self-deletion are blocked.
* **SQL Injection Prevention**: All database queries strictly use parameterized queries (`?` placeholders) with SQLite foreign key enforcement enabled (`PRAGMA foreign_keys = ON`).
* **Rate Limiting & Payload Limits**: Sliding-window rate limiter (30 requests per 10 minutes per IP) on AI chat endpoints, and a rigid 64,000-byte JSON request body cap across all API routes.

## Safe Harbor & Responsible Disclosure

We consider security research conducted under this policy to be authorized. We will not pursue legal action against researchers who:
* Make a good-faith effort to avoid privacy violations, data destruction, and service interruption.
* Give us reasonable time to resolve vulnerabilities before disclosing details publicly.
* Test against local development instances (`127.0.0.1:5050`) rather than disrupting shared production environments.
* Keep communication confidential between the researcher and the security team.

### Out of Scope
* Denial of service attacks targeting network bandwidth or hardware exhaustion.
* Social engineering or phishing targeting portal staff or tournament players.
* Physical security of servers, workstations, or facilities.
