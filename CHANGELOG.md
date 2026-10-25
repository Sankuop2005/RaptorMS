# Changelog

All notable changes to the Raptor Esports Portal will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-10-25

### Added
* Five-role Role-Based Access Control (RBAC) engine in `rbac.py` defining 29 atomic permissions with resource scoping (`all`, `assigned`, `own`) supporting Admin, Manager, Coach, Analyst, and Player roles.
* Zero-dependency multi-threaded application server in `server.py` utilizing Python Standard Library `http.server.ThreadingHTTPServer` bound to `127.0.0.1:5050`.
* Thread-safe SQLite database persistence layer in `db.py` featuring Write-Ahead Logging (WAL), foreign key cascade enforcement (`PRAGMA foreign_keys = ON`), automated migration ledger, and thread-isolated connection pooling.
* Context-aware OpenAI-compatible AI assistant gateway in `ai_assistant.py` supporting direct OpenAI integration, automatic ByNara routing for `sk-nry-*` keys, dual-model fallback (`agnes-2.5-flash` -> `minimax-m3.1-flash:free`), deterministic local rules, and sliding-window rate limiting.
* Modern liquid glass frontend styling with 11 modular CSS stylesheets, dark esports color palette, and custom typography (General Sans, Raptor Valorant, Sayonara / Raptor Stencil, JetBrains Mono).
* Interactive roster scrub stage with 10-second scroll-driven animation and HTTP 206 partial content video streaming.
* Shipped player avatar art assets (`01-hood.png` through `08-phoenix.png`) with persistent assignment logic, avatar customization, and SVG initials fallback.
* Comprehensive 48-unit-test regression suite covering role access rules, database migrations, HTTP authorization, avatar assignment, and AI chatbot integration.
* Full-featured administration console (`admin.html`) providing dynamic dashboards, entity CRUD management, team staff assignments, and financial tracking.
* Public esports portal (`index.html`) and dedicated team overview pages (`team-detail.html`) showing rosters, achievements, and match schedules.
* Generic entity REST endpoints (`/api/entities/*`) for players, teams, tournaments, matches, expenses, and performance records.

### Changed
* Transitioned server architecture from single-threaded request handler to thread-safe `ThreadingHTTPServer` supporting concurrent client connections.
* Upgraded user authentication architecture to individual account credentials stored with cryptographic salts and PBKDF2 hashing.
* Standardized all JSON API responses to set `Cache-Control: no-store` and `Content-Type: application/json; charset=utf-8`.

### Fixed
* Resolved SQLite concurrency locking issues during concurrent write bursts through WAL journaling and connection context isolation.
* Fixed performance record creation logic to guarantee records cannot pair a player with an unassigned team.
* Prevented administrator self-lockout by forbidding self-role updates and self-deletion on active admin sessions.
* Fixed avatar persistence during player record updates so existing assigned artwork is retained when avatar field is omitted.

### Security
* Password hashing using PBKDF2-HMAC-SHA256 with 310,000 iterations and cryptographically random salts.
* Constant-time dummy verification on invalid user lookups to mitigate user-enumeration timing attacks.
* Anti-CSRF token verification required on all mutating API endpoints (`POST`, `PUT`, `DELETE`) verified via constant-time `hmac.compare_digest`.
* Hardened session cookies using 64-character hexadecimal tokens with `HttpOnly; SameSite=Strict; Path=/` attributes and 12-hour expiration.
* Sliding-window client IP rate limiter (30 requests per 10 minutes) on AI chat endpoints with HTTP 429 and `Retry-After` headers.
* Strict 64 KB request body size cap (`OverflowError`) preventing memory exhaustion denial-of-service attempts.
* Content Security Policy (CSP) and `X-Content-Type-Options: nosniff` headers on all served static assets.
