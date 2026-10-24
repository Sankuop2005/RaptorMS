# Raptor Esports Portal

A responsive esports organization portal with a public landing page, admin login, management dashboard, SQLite-backed records, and a local data assistant. It uses only Python's standard library and browser-native HTML, CSS, and JavaScript.

## Requirements

- Python 3.10 or newer
- No package installation required

## Run locally

From this folder, run:

```powershell
python server.py
```

Then open [http://127.0.0.1:5000](http://127.0.0.1:5000). The server listens on localhost only.

## Raptor AI Assistant

The floating assistant appears at the bottom-right of every page: public home, login, team detail, admin, and dashboard.

Configure any OpenAI-compatible chat completions provider. The app reads `API key.txt` from the project root by default:

```text
line 1: API key
line 2: primary model
line 3: fallback model
line 4: optional base URL
```

The included local setup uses NaraRouter with `agnes-2.5-flash` as the primary model and `minimax-m3.1-flash:free` as the fallback. An `sk-nry-` key automatically uses `https://router.bynara.id/v1` when no base URL is supplied. The key file is excluded from git.

Environment variables override the file and can be used instead:

```powershell
$env:OPENAI_API_KEY = "your-key"
$env:OPENAI_BASE_URL = "https://api.openai.com/v1"   # optional
$env:OPENAI_MODEL = "gpt-4o-mini"                    # optional
$env:OPENAI_FALLBACK_MODEL = "another-model"         # optional
$env:OPENAI_KEY_FILE = "C:\path\to\key.txt"          # optional
python server.py
```

- The primary model is tried first. If it fails, the fallback model is tried before answering from local data.
- The base URL can point at OpenAI, OpenRouter, Groq, Ollama, vLLM, NaraRouter, or another compatible provider; the app calls `{OPENAI_BASE_URL}/chat/completions`.
- The key stays on the server. The browser only talks to `/api/chat`; the key file is never served as a static file.
- Public visitors get public team, roster, tournament, and contact information. Signed-in users get role-scoped data from their workspace; finances are included only for Admin and Manager.
- Without a key, or if both models fail, the assistant falls back to local data answers and the widget shows **Local mode**.
- Chat requests are capped (10 messages of up to 2,000 characters per turn) and rate-limited to 30 messages per 10 minutes per IP.
- The Raptor AI page inside the workspace uses the same engine and role-scoped context.

## Local demo roles

- `admin@raptor.local` — Admin
- `manager@raptor.local` — Manager
- `coach@raptor.local` — Coach (assigned to the first team)
- `analyst@raptor.local` — Analyst (assigned to the first team)
- `player@raptor.local` — Player (linked to the first player)

All seeded local demo accounts use `Raptor@2026`. Set `RAPTOR_DEMO_PASSWORD` before first startup to choose another shared demo password. Passwords are stored as salted PBKDF2 hashes. These example accounts are for the localhost demo.

The supported roles are exactly Admin, Manager, Coach, Analyst, and Player. Admin manages accounts, roles, configuration, and all modules. Manager manages organization operations and finances without access to user management or system settings. Coach works with assigned teams and performance. Analyst reads assigned team data and can add/remove roster members, but cannot edit performance or matches. Player sees their linked team and own performance and can submit their own performance records. Financial data is limited to Admin and Manager.

Team-scoped access is configured in the admin console under Coach Assignments. Only Admin or Manager can assign coaches; only Admin can assign analysts or create/change/delete accounts and roles. The server checks each protected read and write, including its team or player scope.

The User Management page lists login accounts with their account role, assigned team access, linked player, and creation date, plus the full player roster with each player's in-game role, team, status, and linked login account. Coach and analyst team access is edited with the account checkboxes; player accounts inherit their team from the linked player record. Player records can be updated without creating a login account.

## Public homepage hero video

The public homepage hero plays `assets/herobg.mp4` (1920×1080 H.264, 10 s) as a plain looping background: `autoplay muted loop playsinline`, `object-fit: cover`, no scroll interaction. The poster copy sits on the left over the existing dark end of the `.hero-art:after` gradient, so the text stays legible over moving footage.

Implementation (public page only — the dashboard, admin console, and login page are untouched):

- `index.html` — the hero keeps its original static structure (`.hero` → `.hero-art` + `.hero-copy`); inside `.hero-art` the `<video class="hero-video">` sits above the `.hero-scene` still, which remains as the poster and the fallback.
- `assets/css/hero-video.css` — positions the clip to fill `.hero-art`, and holds it at `opacity: 0` until a real frame has painted (`.video-live`), which avoids the black flash you get showing a video before its first frame is ready. Under `prefers-reduced-motion` the video is hidden entirely and the still image carries the hero.
- `assets/js/hero-video.js` — adds `.video-live` on `loadeddata`, retries `play()` (some browsers reject the first muted-autoplay attempt), and pauses the clip when the hero scrolls out of view or the tab is hidden so it is not decoding for nobody. It yields to `prefers-reduced-motion` and follows live changes to that setting.
- `assets/css/hero-type.css` — the hero's poster typography, scoped to the homepage hero only. It mirrors a condensed horror-poster type system with two open-license (SIL OFL) fonts served locally from `assets/fonts/` (the CSP only allows same-origin assets): **Anton** for the stacked display headline and stat numerals, **Oswald** (500–700) for the eyebrow, mantra strap, buttons, and stat labels. Body copy keeps the site's existing sans. Fallback chain: `Impact` / `Arial Narrow`.
- `server.py` — serves `.mp4`/`.webm` with content type `video/mp4`. It also sends no cache headers by default, so during development bump the `?v=` version on the hero CSS/JS in `index.html` when iterating on them.

To swap the clip, replace `assets/herobg.mp4` (the `src` in `index.html` can point at any same-origin mp4). Any 1920×1080 or 16:9 encode works; there is no GOP/keyframe requirement now that nothing scrubs. The older scrub encode `assets/video/hero.mp4` and the root `Hero-video.mp4` are unused by the page and kept only as source material.

Requirements are unchanged: Python 3.10+ standard library only. The only external tool is ffmpeg, already installed/updated via winget (`Gyan.FFmpeg`), and only needed if you re-encode the hero video.

## Database

The app creates `data/raptor.sqlite3` on first start and seeds sample teams, players, tournaments, matches, and expenses once. Records remain in SQLite across restarts. To start with fresh demo data, stop the server and delete that database file. To use another location, set `RAPTOR_DB_PATH` before starting.

To add the optional realistic performance demo set after the first startup, run:

```powershell
python seed_performance.py
```

The seed is idempotent and records a migration marker after it loads the data.

## Player art

Players carry an optional `avatar` column naming one of eight hand-authored portrait PNGs in `assets/players/` (`01-hood`, `02-raptor`, `03-trooper`, `04-oni`, `05-wolf`, `06-skull`, `07-fox`, `08-phoenix`, all 512×512). The art is role-free by design; the player's role is specified as a small tinted badge overlaid on the portrait, derived from the existing `role` column, so renaming a role updates every badge without touching the art.

- **Seeding** — a one-time migration (`player_avatars_v1`) deals the eight arts round-robin across a shuffled deck so the whole roster is covered evenly and no art dominates. The migration key means a later restart never reshuffles a choice you have already made by hand.
- **Editing** — the create/edit dialog renders a `type: "avatar"` field as a nine-tile picker (the eight arts plus "No art"). It submits a value on every save, so leaving it alone keeps the current art; choosing "No art" clears it.
- **Validation** — `_validate` rejects any filename that is not a shipped art file, so the column can never be used to point at arbitrary paths.
- **Fallback** — if an art file goes missing, a delegated `error` listener swaps the `<img>` for the player's initials and drops the portrait styling; CSP forbids an inline `onerror`, which is why the listener is attached in the capture phase.

## Pages

- `/` — Public Raptor Esports homepage
- `/login` — Sign-in for all roles
- `/admin` — Admin-only dashboard and management console
- `/dashboard` — Role-scoped workspace for Manager, Coach, Analyst, and Player

The role-scoped portal manages or displays players, teams, performance, tournaments, matches, and (for Admin/Manager) expenses. Its data assistant only answers from data the signed-in role can access; it does not connect to an external AI service.

## Verify

Run the authorization, database migration, and assistant tests with:

```powershell
python -m unittest discover -s tests -v
```

## Continuous integration

`.github/workflows/ci.yml` runs the full test suite on Ubuntu and Windows with Python 3.10 and 3.13 for pushes and pull requests to `main`. No repository secrets are required. Dependabot checks for GitHub Actions updates weekly.
