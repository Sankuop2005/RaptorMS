# Raptor Esports Portal — Design Spec

Date: 2026-10-22

## Intent

Build an actual, locally runnable esports organization portal that follows the supplied Raptor Esports reference image. The intended users are public visitors and an organization administrator. Success means the reference's visual hierarchy is recognizable while the key visitor and admin tasks work end to end, with durable data in SQLite.

## Product shape

One responsive web app with two access levels:

- Public home page: brand, navigation, esports hero, calls to action, organization stats, public teams and tournament highlights, and contact/community links.
- Login page: branded split layout and accessible email/username + password form.
- Admin area: consistent dark sidebar and light content panels for Dashboard, Players, Teams, Tournaments, Matches, Expenses, AI Assistant, and Settings.

On narrow screens, navigation collapses into a keyboard-operable menu and data tables become scrollable or compact cards. Use the Raptor name and an original, lightweight raptor mark drawn in the page; do not depend on the reference JPEG being present at runtime. Use a polished dark navy/black frame, electric purple accents, white content surfaces, compact status chips, and clear sans-serif typography. The supplied image is a visual target, not a source of implementation instructions.

## Main interactions

- Public visitors can navigate between public sections/pages and open the login form.
- An administrator can sign in and sign out. A seeded local demo account is documented for development. Passwords are stored as salted hashes; authentication uses an expiring server-side session and CSRF protection for state-changing forms/API requests.
- Dashboard totals and activity/match summaries come from stored records.
- Admin can create, list, edit, and delete players, teams, tournaments, matches, and expenses. Relationships (such as players assigned to a team) are selectable and validated. Dashboard totals update from those records.
- The assistant accepts questions and returns useful answers from current organization data, including upcoming matches, the five most recent activity updates, and all recorded expenses with a total. It is a deterministic local data assistant, not a claim of external LLM connectivity.
- Empty, loading, validation, success, and failure states are visible and understandable. Destructive deletion requires an in-app confirmation.

## Data and backend

Use Python's standard library HTTP server and SQLite to keep local setup simple and avoid a runtime service dependency. Serve plain HTML, CSS, and JavaScript assets. Implement a small JSON API with server-side input validation and parameterized SQL. Initialize/migrate the database on startup and seed representative Raptor demo data only for a new database. Store the SQLite file in a local `data/` directory. Do not expose secrets or store plaintext passwords.

Core entities: users, players, teams, tournaments, matches, expenses, activity events, and assistant conversation messages. Use foreign keys, stable IDs, timestamps, and sensible delete behavior. Public endpoints expose only deliberately public organization data; admin endpoints require authentication.

## Accessibility and quality

Use semantic landmarks, labeled form controls, visible keyboard focus, sufficient contrast, accessible dialog behavior, status text that does not rely on color alone, and reduced-motion support. Responsive behavior must avoid page-level horizontal overflow. Keep the interface usable without external image or font downloads.

## Scope and constraints

- Stack: HTML, CSS, and vanilla JavaScript frontend; Python backend; SQLite database.
- Deliver a complete local source project with run instructions and seeded demo credentials.
- Match the provided composite reference as a coherent application rather than reproduce every miniature screenshot literally.
- No external account, hosted database, payment service, or live Discord/AI integration is required.
- The local admin login is for demonstration; deployment hardening and production hosting are outside this build.

## Acceptance criteria

1. A user can start the Python server using documented steps and open the public landing page.
2. A fresh run creates and seeds a usable SQLite database.
3. Public navigation and login work; unauthenticated users cannot access admin APIs/pages.
4. Authenticated CRUD works for all five management areas and persists across restart.
5. Dashboard counts and upcoming matches reflect current stored records.
6. Assistant answers upcoming-match and basic organization-stat questions from the database.
7. Layout remains usable at desktop and mobile widths, with keyboard-visible focus and form feedback.
8. README explains setup, run command, demo credentials, and local database location.
