# Raptor Esports Portal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a locally runnable Raptor Esports portal matching the supplied composite reference, with public pages, authenticated admin CRUD, an organization assistant, and SQLite persistence.

**Architecture:** A Python standard-library HTTP server serves static assets and a small JSON API. SQLite stores seeded organization data, password hashes, sessions, and activity. Vanilla JavaScript renders the public portal and authenticated admin views from the API.

**Tech Stack:** HTML, CSS, vanilla JavaScript, Python 3 standard library (`http.server`, `sqlite3`, `hashlib`, `secrets`, `json`), SQLite.

**Spec:** `docs/superpowers/specs/2026-10-22-raptor-esports-portal-design.md`

## Global Constraints

- Build with HTML, CSS, and vanilla JavaScript frontend; Python backend; SQLite database.
- Do not depend on external image or font downloads at runtime.
- Use server-side validation, parameterized SQL, foreign keys, salted password hashes, expiring sessions, and CSRF protection for state-changing requests.
- Public endpoints expose only deliberately public organization data; admin endpoints require authentication.
- Keep accessible labels, visible focus, feedback states, confirmation before deletion, and usable responsive layouts.
- Seed representative demo data on a new database only; preserve existing records on restart.
- Assistant is deterministic and answers using the current database; do not imply external LLM integration.

## Review Focus

- Invalid or malicious record input must return a useful client error without corrupting the database; check required fields and escaped rendering in Task 2/3.
- Unauthenticated or expired sessions must not access or mutate admin data; check in Task 1/2.
- Cross-site request forgery must not allow a state-changing operation; check token-required writes in Task 1/2.
- Invalid/missing team references and deletes with linked records must preserve valid relationships; check in Task 2.
- Empty organization data and narrow viewports must remain understandable and navigable; check in Task 3.

---

### Task 1: Server, SQLite setup, and authentication

**Files:**
- Create: `server.py` — HTTP routing, static-file serving, JSON request/response helpers, session and CSRF handling.
- Create: `db.py` — schema, startup initialization, seed records, password hashing, DB connection helpers.
- Create: `data/.gitkeep` — local database directory placeholder; runtime database is ignored by source control if Git is later initialized.
- Create: `.gitignore` — Python cache and local SQLite files.

**Interfaces:**
- `db.initialize() -> None` creates schema and seeds only a new DB.
- `db.get_connection() -> sqlite3.Connection` enables foreign keys and row objects.
- `db.hash_password(password: str, salt: bytes | None = None) -> tuple[bytes, bytes]` returns salt and PBKDF2-HMAC-SHA256 hash.
- `server.send_json(handler, status: int, payload: dict) -> None` serializes JSON safely.
- `server.require_admin(handler) -> dict | None` validates the opaque cookie session and returns the authenticated user or sends 401.
- `server.main() -> None` initializes the DB and serves on `127.0.0.1:8000`.

- [ ] Create the tables for `users`, `sessions`, `players`, `teams`, `tournaments`, `matches`, `expenses`, `activity_events`, and `assistant_messages`, including primary keys, timestamps, foreign keys, and constraints from the spec.
- [ ] Seed one demo admin and sample teams, players, tournaments, matches, and expenses only when the database is first created; store the demo password as PBKDF2 hash and document `admin@raptor.local` / `Raptor2025!`.
- [ ] Implement login, logout, `/api/me`, expiring server-side sessions, HttpOnly/SameSite cookie, and per-session CSRF token; reject unauthenticated protected requests and missing/invalid CSRF tokens on writes.
- [ ] Implement static asset serving with resolved-path checks and correct MIME types; bind locally by default.
- [ ] Confirm with focused manual checks that a fresh start creates one seeded DB, login succeeds, logout expires access, and protected routes reject unauthenticated requests.

### Task 2: Public and authenticated JSON APIs

**Files:**
- Modify: `server.py` — route dispatch and API handlers.
- Modify: `db.py` — query helpers as needed.

**Interfaces:**
- `server.handle_api(handler, method: str, path: str, body: dict | None) -> bool` handles an API route and returns whether it matched.
- `db.list_records(table: str, filters: dict | None = None) -> list[dict]` only permits the five predefined management tables and explicit filter fields.
- `db.save_record(table: str, record_id: int | None, values: dict) -> dict` validates table/fields, persists an insert/update, and returns the row.
- `db.delete_record(table: str, record_id: int) -> None` uses explicit per-entity deletion rules and raises typed validation/relationship errors.

- [ ] Implement public summary, public team/tournament lists, admin dashboard stats/recent activity/upcoming matches, and authenticated CRUD endpoints for players, teams, tournaments, matches, and expenses.
- [ ] Validate required fields, allowed status values, dates, numeric amounts, IDs, and team/player relationships; use parameterized SQL and return consistent 400/404/409 errors.
- [ ] Record activity events for successful admin mutations; calculate dashboard counts and totals from saved rows.
- [ ] Implement `POST /api/assistant` with deterministic intent matching for upcoming matches, basic organization counts, the five most recent activity events, and every saved expense with a total; store conversation messages and format database-backed answers.
- [ ] Confirm focused manual API interactions cover create/list/update/delete, database persistence after server restart, relationship constraint errors, dashboard calculations, and assistant answers.

### Task 3: Public site and admin interface

**Files:**
- Create: `index.html` — public home page structure.
- Create: `login.html` — branded login page.
- Create: `admin.html` — admin shell and content region.
- Create: `assets/css/styles.css` — shared tokens, responsive layout, public/admin styling, states.
- Create: `assets/js/api.js` — JSON API and CSRF-aware request helpers.
- Create: `assets/js/public.js` — public stats, teams, public navigation.
- Create: `assets/js/login.js` — login form, validation, password visibility, redirect.
- Create: `assets/js/admin.js` — admin navigation, dashboard, CRUD tables/forms, assistant.
- Create: `assets/raptor-mark.svg` — original lightweight Raptor mark.

**Interfaces:**
- `api.request(path: string, options: RequestInit = {}) -> Promise<any>` sends same-origin JSON and includes CSRF for writes.
- `api.me() -> Promise<User>` and `api.logout() -> Promise<void>` manage auth state.
- `admin.renderPage(page: string) -> Promise<void>` loads the chosen admin view from the API.
- `admin.showForm(entity: string, record?: object) -> void` renders create/edit modal and submits validated data.

- [ ] Implement the public landing page based on the reference: responsive black/navy esports header, original hero art treatment, Raptor headline, value proposition, join/team actions, stats, team/tournament previews, and footer.
- [ ] Implement the split login screen and accessible validation/error feedback, remember-me presentation, password visibility toggle, and successful navigation to admin.
- [ ] Implement responsive dark sidebar/light-panel admin shell and Dashboard, Players, Teams, Tournaments, Matches, Expenses, Assistant, and Settings navigation.
- [ ] Implement database-driven dashboard cards and upcoming activity; data lists; create/edit forms; accessible delete confirmation; visible empty/loading/error/success states; and responsive table/card behavior.
- [ ] Escape server-provided text before inserting into the DOM, use semantic labels/focus states and keyboard-operable dialogs, and honor reduced motion.
- [ ] Confirm focused manual browser checks cover desktop/mobile layout, login/logout, representative CRUD in each entity, accessible form feedback, and assistant responses.

### Task 4: Local setup guide and final integration

**Files:**
- Create: `README.md` — setup, run, credentials, routes, database/reset details.
- Modify: `server.py`, `db.py`, `assets/**` — integration corrections only.

**Interfaces:**
- `python server.py` starts the app at `http://127.0.0.1:8000`.

- [ ] Document Python 3.10+ requirement, exact run command, demo login, seeded-data behavior, database location, and reset steps.
- [ ] Review all eight acceptance criteria in the spec against implemented routes and pages; correct gaps before handoff.
- [ ] Start the app and perform a final smoke walkthrough of public navigation, authentication, CRUD persistence, dashboard stats, and assistant; report any limitation plainly.
