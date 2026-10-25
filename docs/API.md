# Raptor Esports Portal — REST API Specification

**Document Version:** 1.0.0  
**Target Release:** Raptor Esports Portal 2026 (Production)  
**Classification:** REST API Reference & Contract Specification  
**Default Base URL:** `http://127.0.0.1:5050`  

---

## 1. Global API Architecture & Protocol Invariants

### 1.1 Transport & Serialization
All REST API endpoints exchange data exclusively using UTF-8 JSON. Every API response includes the following standard HTTP headers:
```http
Content-Type: application/json; charset=utf-8
Cache-Control: no-store
```

### 1.2 Global Request Size Limits
The web server strictly enforces a payload ceiling of **64,000 bytes (64 KB)** on all incoming request bodies (`read_json()`).
- If an incoming request body exceeds 64,000 bytes, the server aborts processing and responds with **HTTP 413 Payload Too Large**:
  ```json
  {
    "error": "Request is too large"
  }
  ```
- All mutating POST and PUT requests must supply `Content-Type: application/json`. Providing another MIME type or omitting it yields **HTTP 400 Bad Request**:
  ```json
  {
    "error": "Request must use application/json"
  }
  ```
- Unparseable JSON syntax or root payloads that are not JSON objects return **HTTP 400 Bad Request**:
  ```json
  {
    "error": "Request must contain valid JSON"
  }
  ```

### 1.3 Ground-Truth Implementation Notice: Non-Existent Endpoints
- **`/api/auth`**: Does **NOT** exist in the codebase. Authentication operations are divided among `POST /api/login`, `POST /api/logout`, `GET /api/me`, and `GET /api/chat/session`. Requests to `/api/auth` return **HTTP 404 Not Found**:
  ```json
  {
    "error": "Not found"
  }
  ```
- **`/api/health`**: Does **NOT** exist in the codebase. Requests to `/api/health` return **HTTP 404 Not Found**:
  ```json
  {
    "error": "Not found"
  }
  ```

---

## 2. Authentication & Session Endpoints

### 2.1 `POST /api/login`
Authenticates user credentials, clears stale sessions, generates an opaque 64-hex session token, returns the user record and CSRF token, and sets the secure `raptor_session` HTTP cookie.

- **HTTP Method:** `POST`
- **URL Pattern:** `/api/login`
- **Authentication:** None (Public)
- **CSRF Token:** Not required
- **Request Headers:**
  - `Content-Type: application/json`

#### Request Body Schema
```json
{
  "type": "object",
  "required": ["identity", "password"],
  "properties": {
    "identity": {"type": "string", "maxLength": 200, "description": "User email address"},
    "password": {"type": "string", "maxLength": 256, "description": "Plaintext user password"}
  }
}
```

#### Request Example
```json
{
  "identity": "admin@raptor.local",
  "password": "Raptor@2026"
}
```

#### Response (200 OK)
- **Headers:**
  - `Set-Cookie: raptor_session=0a4f8d7b3e1c9a2f5e8b4c7d0a3e6f9b2c5d8a1e4f7b0c3d6a9e2f5b8c1d4a7e; HttpOnly; SameSite=Strict; Path=/; Max-Age=43200`
- **Body:**
```json
{
  "user": {
    "name": "Admin",
    "email": "admin@raptor.local",
    "role": "admin"
  },
  "csrf": "g9K_L8mP2qR4tU7vW0yZ3bC6eF9hI1kL4nO7pQ0sT3u"
}
```

#### Error Responses
- **400 Bad Request:** Missing or empty credentials, or password > 256 chars:
  ```json
  {"error": "Enter your email and password."}
  ```
- **401 Unauthorized:** Invalid email or incorrect password (timing-safe PBKDF2 evaluated):
  ```json
  {"error": "That email or password isn’t correct."}
  ```
- **403 Forbidden:** Account role not supported in RBAC:
  ```json
  {"error": "This account has no supported role."}
  ```
- **413 Payload Too Large:** Body > 64,000 bytes.

---

### 2.2 `POST /api/logout`
Terminates the active session in the database and clears the browser cookie.

- **HTTP Method:** `POST`
- **URL Pattern:** `/api/logout`
- **Authentication:** Required (Any authenticated role)
- **CSRF Token:** Required (`X-CSRF-Token`)
- **Request Headers:**
  - `Cookie: raptor_session=<64-hex-token>`
  - `X-CSRF-Token: <csrf-token>`
  - `Content-Type: application/json`
- **Request Body:** `{}` (empty JSON object)

#### Response (200 OK)
- **Headers:**
  - `Set-Cookie: raptor_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0`
- **Body:**
```json
{
  "ok": true
}
```

#### Error Responses
- **401 Unauthorized:** Missing or expired session:
  ```json
  {"error": "Please sign in to continue."}
  ```
- **403 Forbidden:** CSRF token missing or mismatch:
  ```json
  {"error": "Your session expired. Refresh and try again."}
  ```

---

### 2.3 `GET /api/me`
Retrieves the profile, team assignments, linked player ID, full permission dictionary, and CSRF token for the currently authenticated user.

- **HTTP Method:** `GET`
- **URL Pattern:** `/api/me`
- **Authentication:** Required (Any authenticated role)
- **CSRF Token:** Not required
- **Request Headers:**
  - `Cookie: raptor_session=<64-hex-token>`
- **Request Body:** None

#### Response (200 OK)
```json
{
  "user": {
    "name": "Coach",
    "email": "coach@raptor.local",
    "role": "coach",
    "player_id": null,
    "team_ids": [1]
  },
  "permissions": {
    "teams.view_all": "assigned",
    "teams.create": false,
    "teams.update": "assigned",
    "teams.delete": false,
    "teams.assign_coaches": false,
    "roster.view": "assigned",
    "roster.create": "assigned",
    "roster.update": false,
    "roster.delete": "assigned",
    "performance.view_all": "assigned",
    "performance.create": "assigned",
    "performance.update": "assigned",
    "performance.delete": false,
    "matches.view_all": "assigned",
    "matches.create": false,
    "matches.update": false,
    "matches.delete": false,
    "financial.view": false,
    "financial.create": false,
    "financial.update": false,
    "financial.delete": false,
    "reports.view": "assigned",
    "analytics.view": "assigned",
    "admin.access": false,
    "system.configure": false,
    "users.view_all": false,
    "users.create": false,
    "users.update_role": false,
    "users.delete": false
  },
  "csrf": "g9K_L8mP2qR4tU7vW0yZ3bC6eF9hI1kL4nO7pQ0sT3u"
}
```

#### Error Responses
- **401 Unauthorized:** Invalid or absent session cookie:
  ```json
  {"error": "Please sign in."}
  ```
- **403 Forbidden:** Unknown or disabled account role:
  ```json
  {"error": "This account has no supported role."}
  ```

---

## 3. Chat & Assistant Endpoints

### 3.1 `GET /api/chat/session`
Session awareness discovery endpoint utilized by the floating Raptor AI Assistant widget to verify whether the visitor is authenticated, retrieve user permissions, and obtain a CSRF token.

- **HTTP Method:** `GET`
- **URL Pattern:** `/api/chat/session`
- **Authentication:** Optional (Session-aware)
- **CSRF Token:** Not required
- **Request Headers:**
  - `Cookie: raptor_session=<64-hex-token>` (Optional)
- **Request Body:** None

#### Response (200 OK - Visitor / Unauthenticated)
```json
{
  "authenticated": false,
  "user": null,
  "permissions": {},
  "csrf": null
}
```

#### Response (200 OK - Authenticated Staff)
```json
{
  "authenticated": true,
  "user": {
    "name": "Admin",
    "email": "admin@raptor.local",
    "role": "admin"
  },
  "permissions": {
    "admin.access": true,
    "analytics.view": "all",
    "financial.view": "all"
  },
  "csrf": "g9K_L8mP2qR4tU7vW0yZ3bC6eF9hI1kL4nO7pQ0sT3u"
}
```

---

### 3.2 `POST /api/chat`
Floating AI Assistant conversation endpoint. Supports public visitors (sanitized public context) and authenticated staff (role-scoped data context). Protected by sliding-window client-IP rate limiting (30 requests / 10 minutes).

- **HTTP Method:** `POST`
- **URL Pattern:** `/api/chat`
- **Authentication:** Optional (Session-aware)
- **CSRF Token:** Required if `raptor_session` cookie is provided
- **Rate Limit:** 30 requests / 10 minutes per client IP (`HTTP 429` on exceed)
- **Request Headers:**
  - `Content-Type: application/json`
  - `X-CSRF-Token: <csrf-token>` (Required if authenticated)
  - `Cookie: raptor_session=<token>` (Optional)

#### Request Body Schema
```json
{
  "type": "object",
  "properties": {
    "messages": {
      "type": "array",
      "maxItems": 10,
      "items": {
        "type": "object",
        "required": ["role", "content"],
        "properties": {
          "role": {"type": "string", "enum": ["user", "assistant"]},
          "content": {"type": "string", "maxLength": 2000}
        }
      }
    },
    "question": {"type": "string", "maxLength": 2000, "description": "Legacy single-question format"}
  }
}
```

#### Request Example
```json
{
  "messages": [
    {"role": "user", "content": "What are our upcoming tournament matches?"}
  ]
}
```

#### Response (200 OK - Live OpenAI Mode)
```json
{
  "answer": "Raptor Esports is participating in **Raptor Cup #01** for BGMI on **2026-10-28** with a prize pool of ₹5,000. Additionally, scrim matches against Xtreme are scheduled for tonight at 08:00 PM.",
  "mode": "openai",
  "model": "agnes-2.5-flash",
  "authenticated": false
}
```

#### Response (200 OK - Local Deterministic Fallback Mode)
```json
{
  "answer": "Raptor Esports has upcoming events: Raptor Cup #01 (BGMI) on 2026-10-28. Check the Tournaments section for registration and rules.",
  "mode": "local",
  "notice": "Live AI is unavailable right now, so I answered from Raptor's local data.",
  "authenticated": false
}
```

#### Error Responses
- **400 Bad Request:** Empty messages, message > 2,000 chars, total conversation > 8,000 chars, or invalid role:
  ```json
  {"error": "Each message must be 2,000 characters or fewer."}
  ```
- **403 Forbidden:** Authenticated user with invalid CSRF token or unsupported role:
  ```json
  {"error": "Your session expired. Refresh and try again."}
  ```
- **413 Payload Too Large:** Body > 64,000 bytes.
- **429 Too Many Requests:** Client IP exceeded 30 requests / 10 minutes:
  ```http
  HTTP/1.1 429 Too Many Requests
  Retry-After: 60
  Content-Type: application/json; charset=utf-8

  {"error": "Too many messages. Please wait a few minutes and try again."}
  ```

---

### 3.3 `POST /api/assistant`
Workspace console assistant endpoint. Takes a question, generates a role-scoped answer, and persists the interaction into the SQLite `assistant_messages` table.

- **HTTP Method:** `POST`
- **URL Pattern:** `/api/assistant`
- **Authentication:** Required
- **RBAC Permission:** `analytics.view` (`Admin`, `Manager`, `Coach`, `Analyst`, `Player`)
- **CSRF Token:** Required (`X-CSRF-Token`)
- **Request Headers:**
  - `Cookie: raptor_session=<64-hex-token>`
  - `X-CSRF-Token: <csrf-token>`
  - `Content-Type: application/json`

#### Request Example
```json
{
  "question": "Summarize our current roster count across divisions."
}
```

#### Response (200 OK)
```json
{
  "answer": "Raptor Esports currently fields 14 active players across 4 competitive divisions: Raptor (BGMI) with 5 players, Raptor (Free Fire) with 4 players, Raptor (Valorant) with 5 players, and Raptor Academy.",
  "mode": "openai",
  "model": "agnes-2.5-flash",
  "authenticated": true
}
```

#### Error Responses
- **400 Bad Request:** Empty question:
  ```json
  {"error": "Type a question first."}
  ```
- **401 Unauthorized:** Missing or invalid session.
- **403 Forbidden:** Missing `analytics.view` or CSRF mismatch.

---

## 4. Analytics & Dashboard Endpoints

### 4.1 `GET /api/dashboard`
Retrieves overview telemetry, upcoming scheduled matches, recent activity logs, and expense access status, filtered strictly to the caller's role scope.

- **HTTP Method:** `GET`
- **URL Pattern:** `/api/dashboard`
- **Authentication:** Required
- **RBAC Permission:** `analytics.view`
- **CSRF Token:** Not required
- **Request Headers:**
  - `Cookie: raptor_session=<64-hex-token>`

#### Response (200 OK - Admin / Manager with Financial Scope)
```json
{
  "stats": {
    "players": 14,
    "teams": 4,
    "tournaments": 4,
    "expenses": 12500.0
  },
  "matches": [
    {
      "id": 1,
      "name": "BGMI Scrims",
      "game": "BGMI",
      "date": "2026-10-27",
      "time": "08:00 PM",
      "opponent": "Xtreme",
      "status": "Upcoming",
      "result": ""
    }
  ],
  "activity": [
    {
      "id": 1,
      "message": "Player Sanku added to Raptor (BGMI)",
      "kind": "info",
      "created_at": "2026-10-25 10:00:00"
    }
  ],
  "can_view_expenses": true
}
```

#### Response Behavior for Scoped Roles (Coach, Analyst, Player)
- `stats.expenses`: Evaluates to `0`.
- `activity`: Empty array `[]` (activity logs restricted to `Admin` and `Manager`).
- `can_view_expenses`: Evaluates to `false`.
- `matches`, `teams`, `players`: Filtered strictly to assigned/own IDs.

#### Error Responses
- **401 Unauthorized:** Not authenticated.
- **403 Forbidden:** Lacks `analytics.view`:
  ```json
  {"error": "You do not have permission to view the dashboard."}
  ```

---

### 4.2 `GET /api/reports`
Calculates aggregated reporting metrics (team counts, roster counts, total scrims, average performance evaluation score, and organization expenses) scoped to the caller's authorized boundaries.

- **HTTP Method:** `GET`
- **URL Pattern:** `/api/reports`
- **Authentication:** Required
- **RBAC Permission:** `reports.view`
- **CSRF Token:** Not required
- **Request Headers:**
  - `Cookie: raptor_session=<64-hex-token>`

#### Response (200 OK - Full Access)
```json
{
  "teams": 4,
  "players": 14,
  "performance_records": 15,
  "average_score": 84.2,
  "matches": 3,
  "competitions": 4,
  "can_view_expenses": true,
  "expenses_total": 12500.0
}
```

#### Response Notes
- If caller lacks `financial.view` (e.g. `Coach`, `Analyst`, `Player`), `can_view_expenses` is `false` and `expenses_total` is omitted.
- If no performance records match the caller's scope, `average_score` returns `null`.

#### Error Responses
- **401 Unauthorized:** Not authenticated.
- **403 Forbidden:** Lacks `reports.view`:
  ```json
  {"error": "You do not have permission to view reports."}
  ```

---

## 5. Public Views Endpoints

### 5.1 `GET /api/public` (Public Overview & Live Ticker)
*Canonical Path:* `GET /api/public`  
*Logical View Aliases:* `GET /api/public/teams-overview`, `GET /api/public/live-ticker`  
Powers the public portal stats counter, live tournament card rail, and teams directory.

- **HTTP Method:** `GET`
- **URL Pattern:** `/api/public`
- **Authentication:** None (Public)
- **CSRF Token:** Not required
- **Request Headers:** None required
- **Request Body:** None

#### Response (200 OK)
```json
{
  "stats": {
    "players": 14,
    "teams": 4,
    "tournaments": 4
  },
  "teams": [
    {
      "id": 1,
      "name": "Raptor (BGMI)",
      "game": "BGMI",
      "players_count": 5,
      "status": "Active",
      "description": "India's premier competitive Battlegrounds Mobile India lineup.",
      "accent": "violet",
      "created_at": "2026-10-25 10:00:00"
    }
  ],
  "tournaments": [
    {
      "id": 1,
      "name": "Raptor Cup #01",
      "game": "BGMI",
      "date": "2026-10-28",
      "prize_pool": 5000.0,
      "status": "Upcoming",
      "location": "Online",
      "team_id": 1,
      "created_at": "2026-10-25 10:00:00"
    }
  ]
}
```

---

### 5.2 `GET /api/public/teams/<id>` (Public Team Details)
*Canonical Path:* `GET /api/public/teams/<id>`  
*Logical View Alias:* `GET /api/public/team-details`  
Retrieves public information for a single team along with its active roster and assigned avatar art filenames.

- **HTTP Method:** `GET`
- **URL Pattern:** `/api/public/teams/<id>`
- **Authentication:** None (Public)
- **Path Parameter:** `id` (integer) — Team ID (e.g. `1`)
- **Request Headers:** None required

#### Response (200 OK)
```json
{
  "team": {
    "id": 1,
    "name": "Raptor (BGMI)",
    "game": "BGMI",
    "players_count": 5,
    "status": "Active",
    "description": "India's premier competitive Battlegrounds Mobile India lineup.",
    "accent": "violet"
  },
  "players": [
    {
      "id": 1,
      "name": "Sanku",
      "ign": "Sanku",
      "role": "IGL",
      "status": "Active",
      "game": "BGMI",
      "avatar": "01-hood.png"
    },
    {
      "id": 2,
      "name": "Arjun",
      "ign": "Viper",
      "role": "Assaulter",
      "status": "Active",
      "game": "BGMI",
      "avatar": "02-oni.png"
    }
  ]
}
```

#### Error Responses
- **404 Not Found:** Team ID does not exist or team has status `'Inactive'`:
  ```json
  {"error": "Team not found"}
  ```

---

## 6. User Administration Endpoints (Admin Only)

### 6.1 `GET /api/users`
Lists all user accounts registered in the portal, along with their assigned staff teams and linked player profiles.

- **HTTP Method:** `GET`
- **URL Pattern:** `/api/users`
- **Authentication:** Required
- **RBAC Permission:** `users.view_all` (`Admin` only)
- **CSRF Token:** Not required

#### Response (200 OK)
```json
{
  "items": [
    {
      "id": 1,
      "email": "admin@raptor.local",
      "name": "Admin",
      "role": "admin",
      "player_id": null,
      "created_at": "2026-10-25 10:00:00",
      "teams": [],
      "player": null
    },
    {
      "id": 3,
      "email": "coach@raptor.local",
      "name": "Coach",
      "role": "coach",
      "player_id": null,
      "created_at": "2026-10-25 10:00:00",
      "teams": [
        {"id": 1, "name": "Raptor (BGMI)", "game": "BGMI"}
      ],
      "player": null
    },
    {
      "id": 5,
      "email": "player@raptor.local",
      "name": "Player",
      "role": "player",
      "player_id": 1,
      "created_at": "2026-10-25 10:00:00",
      "teams": [],
      "player": {
        "id": 1,
        "name": "Sanku",
        "ign": "Sanku",
        "role": "IGL",
        "game": "BGMI",
        "team_id": 1,
        "team_name": "Raptor (BGMI)",
        "status": "Active"
      }
    }
  ]
}
```

#### Error Responses
- **401 Unauthorized:** Missing or invalid session.
- **403 Forbidden:** Lacks `users.view_all`:
  ```json
  {"error": "You do not have permission to perform this action."}
  ```

---

### 6.2 `POST /api/users`
Creates a new portal user account, salted password hash, assigned role, and optional initial staff team or player linkage.

- **HTTP Method:** `POST`
- **URL Pattern:** `/api/users`
- **Authentication:** Required
- **RBAC Permission:** `users.create` (`Admin` only)
- **CSRF Token:** Required (`X-CSRF-Token`)
- **Request Headers:**
  - `Cookie: raptor_session=<64-hex-token>`
  - `X-CSRF-Token: <csrf-token>`
  - `Content-Type: application/json`

#### Request Body Schema
```json
{
  "type": "object",
  "required": ["email", "name", "role", "password"],
  "properties": {
    "email": {"type": "string", "maxLength": 200},
    "name": {"type": "string", "maxLength": 100},
    "role": {"type": "string", "enum": ["admin", "manager", "coach", "analyst", "player"]},
    "password": {"type": "string", "minLength": 8, "maxLength": 256},
    "team_id": {"type": "integer", "nullable": true, "description": "Only permitted for coach or analyst"},
    "player_id": {"type": "integer", "nullable": true, "description": "Only permitted for player"}
  }
}
```

#### Request Example
```json
{
  "email": "analyst2@raptor.local",
  "name": "Senior Analyst",
  "role": "analyst",
  "password": "Raptor@2026",
  "team_id": 1,
  "player_id": null
}
```

#### Response (201 Created)
```json
{
  "user": {
    "id": 6,
    "email": "analyst2@raptor.local",
    "name": "Senior Analyst",
    "role": "analyst",
    "player_id": null,
    "created_at": "2026-10-25 12:00:00"
  }
}
```

#### Error Responses
- **400 Bad Request:** Password < 8 chars, invalid role, or `team_id` given for non-staff:
  ```json
  {"error": "Initial team access is only valid for coach or analyst accounts."}
  ```
- **403 Forbidden:** CSRF mismatch or missing `users.create`.
- **409 Conflict:** Email already exists:
  ```json
  {"error": "That account already exists or the linked record is invalid."}
  ```

---

### 6.3 `PUT /api/users/<id>`
Updates an existing user's role and replaces their assigned teams. Prevents admin self-modification.

- **HTTP Method:** `PUT`
- **URL Pattern:** `/api/users/<id>`
- **Authentication:** Required
- **RBAC Permission:** `users.update_role` (`Admin` only)
- **CSRF Token:** Required (`X-CSRF-Token`)
- **Path Parameter:** `id` (integer) — User ID to update

#### Request Example
```json
{
  "role": "coach",
  "team_ids": [1, 2]
}
```

#### Response (200 OK)
```json
{
  "ok": true
}
```

#### Error Responses
- **400 Bad Request:** Invalid role or assigning teams to non-staff.
- **403 Forbidden:** Admin attempting to change their own role:
  ```json
  {"error": "You cannot change or delete your own account role here."}
  ```
- **404 Not Found:** User ID does not exist:
  ```json
  {"error": "User not found"}
  ```

---

### 6.4 `DELETE /api/users/<id>`
Deletes a user account. Cascades deletion of active sessions and staff assignments. Prevents admin self-deletion.

- **HTTP Method:** `DELETE`
- **URL Pattern:** `/api/users/<id>`
- **Authentication:** Required
- **RBAC Permission:** `users.delete` (`Admin` only)
- **CSRF Token:** Required (`X-CSRF-Token`)
- **Path Parameter:** `id` (integer) — User ID to delete

#### Response (200 OK)
```json
{
  "ok": true
}
```

#### Error Responses
- **403 Forbidden:** Admin attempting to delete their own account:
  ```json
  {"error": "You cannot change or delete your own account role here."}
  ```
- **404 Not Found:** User not found.

---

## 7. Staff & Coach Assignment Endpoints

### 7.1 `GET /api/assignments` (List Assignments)
*Canonical Path:* `GET /api/assignments`  
*Logical View Alias:* `GET /api/coach/assignments`  
Lists staff team assignments. Managers view only coach assignments; Admins view both coach and analyst assignments.

- **HTTP Method:** `GET`
- **URL Pattern:** `/api/assignments`
- **Authentication:** Required
- **RBAC Permission:** `teams.assign_coaches` (`Admin`, `Manager`)
- **CSRF Token:** Not required

#### Response (200 OK)
```json
{
  "items": [
    {
      "user_id": 3,
      "user_name": "Coach",
      "email": "coach@raptor.local",
      "role": "coach",
      "team_id": 1,
      "team_name": "Raptor (BGMI)"
    }
  ]
}
```

---

### 7.2 `GET /api/coaches` (List Assignable Staff)
Lists eligible staff accounts available for team assignment.

- **HTTP Method:** `GET`
- **URL Pattern:** `/api/coaches`
- **Authentication:** Required
- **RBAC Permission:** `teams.assign_coaches` (`Admin`, `Manager`)
- **CSRF Token:** Not required

#### Response (200 OK)
```json
{
  "items": [
    {
      "id": 3,
      "name": "Coach",
      "email": "coach@raptor.local",
      "role": "coach"
    }
  ]
}
```

---

### 7.3 `POST /api/assignments` (Create Assignment)
*Canonical Path:* `POST /api/assignments`  
*Logical View Alias:* `POST /api/coach/assignments`  
Assigns a coach or analyst user to a team. Managers may assign coaches only; Admins may assign coaches or analysts.

- **HTTP Method:** `POST`
- **URL Pattern:** `/api/assignments`
- **Authentication:** Required
- **RBAC Permission:** `teams.assign_coaches` (`Admin`, `Manager`)
- **CSRF Token:** Required (`X-CSRF-Token`)

#### Request Example
```json
{
  "user_id": 3,
  "team_id": 2
}
```

#### Response (201 Created)
```json
{
  "ok": true
}
```

#### Error Responses
- **400 Bad Request:** Missing fields or user is not coach/analyst.
- **403 Forbidden:** Manager attempting to assign an analyst:
  ```json
  {"error": "This role cannot be assigned by your account."}
  ```
- **404 Not Found:** User or team does not exist.

---

### 7.4 `DELETE /api/assignments/<user_id>/<team_id>` (Remove Assignment)
*Canonical Path:* `DELETE /api/assignments/<user_id>/<team_id>`  
*Logical View Alias:* `DELETE /api/coach/assignments/<id>`  
Unbinds a staff member from a team.

- **HTTP Method:** `DELETE`
- **URL Pattern:** `/api/assignments/<user_id>/<team_id>`
- **Authentication:** Required
- **RBAC Permission:** `teams.assign_coaches` (`Admin`, `Manager`)
- **CSRF Token:** Required (`X-CSRF-Token`)
- **Path Parameters:**
  - `user_id` (integer)
  - `team_id` (integer)

#### Response (200 OK)
```json
{
  "ok": true
}
```

#### Error Responses
- **403 Forbidden:** Manager attempting to unassign an analyst.
- **404 Not Found:** Assignment or user record does not exist.

---

## 8. Generic Entity CRUD Engine (`/api/entities/<table_name>`)

The entity engine exposes unified CRUD operations over 6 database tables: `players`, `teams`, `tournaments`, `matches`, `expenses`, and `performance_records`. Route regex: `^/api/entities/([a-z_]+)(?:/(\d+))?$`.

### 8.1 Schema & Field Constraints Matrix

| Table | Permitted Fields | Required Fields | Enums & Range Constraints |
|---|---|---|---|
| `players` | `name`, `ign`, `role`, `team_id`, `status`, `game`, `joined_at`, `avatar` | `name`, `ign`, `role`, `status` | `status`: `Active`, `Inactive`, `Trial`<br>`avatar`: Shipped filenames (`01-hood.png` ... `08-phoenix.png`) or `""` (initials circle) |
| `teams` | `name`, `game`, `players_count`, `status`, `description`, `accent` | `name`, `game` | `status`: `Active`, `Recruiting`, `Inactive`<br>`accent`: `violet`, `amber`, `pink`, `cyan`<br>`players_count`: Auto-maintained by system |
| `tournaments` | `name`, `game`, `date`, `prize_pool`, `status`, `location`, `team_id` | `name`, `game`, `date`, `prize_pool`, `status` | `status`: `Upcoming`, `Ongoing`, `Completed`<br>`date`: `YYYY-MM-DD`<br>`prize_pool`: Float $\ge 0$ |
| `matches` | `name`, `game`, `date`, `time`, `opponent`, `tournament_id`, `team_id`, `status`, `result` | `name`, `game`, `date`, `time`, `status` | `status`: `Upcoming`, `Live`, `Completed`<br>`date`: `YYYY-MM-DD`<br>`time`: `HH:MM AM/PM` (default `08:00 PM`) |
| `expenses` | `title`, `category`, `amount`, `date`, `notes` | `title`, `category`, `amount`, `date` | `amount`: Float in $[0, 100{,}000{,}000]$<br>`date`: `YYYY-MM-DD` |
| `performance_records` | `player_id`, `team_id`, `category`, `score`, `date`, `notes` | `player_id`, `category`, `score`, `date` | `score`: Float in $[0, 100]$<br>`date`: `YYYY-MM-DD`<br>`team_id`: Must match player's linked team |

---

### 8.2 `GET /api/entities/<table_name>` (List Records)
Returns all records for the specified entity table that the caller is authorized to view.

- **HTTP Method:** `GET`
- **URL Pattern:** `/api/entities/<table_name>`
- **Authentication:** Required
- **RBAC Permission:** Checked per table (`roster.view`, `teams.view_all`, `matches.view_all`, `financial.view`, `performance.view_all`)
- **CSRF Token:** Not required

#### Request Example
```http
GET /api/entities/players HTTP/1.1
Host: 127.0.0.1:5050
Cookie: raptor_session=0a4f8d...
```

#### Response (200 OK)
```json
{
  "items": [
    {
      "id": 1,
      "name": "Sanku",
      "ign": "Sanku",
      "role": "IGL",
      "team_id": 1,
      "team_name": "Raptor (BGMI)",
      "status": "Active",
      "game": "BGMI",
      "joined_at": "2026-01-15",
      "avatar": "01-hood.png",
      "created_at": "2026-10-25 10:00:00"
    }
  ]
}
```

#### Error Responses
- **401 Unauthorized:** Missing session.
- **403 Forbidden:** Lacks view permission for this table:
  ```json
  {"error": "You do not have permission to view this section."}
  ```
- **404 Not Found:** Table not supported in `db.TABLES`:
  ```json
  {"error": "Not found"}
  ```

---

### 8.3 `POST /api/entities/<table_name>` (Create Record)
Inserts a new record into the specified entity table. Automatically overrides `player_id` and binds `team_id` when submitted by a `Player` role.

- **HTTP Method:** `POST`
- **URL Pattern:** `/api/entities/<table_name>`
- **Authentication:** Required
- **RBAC Permission:** Checked per table (`roster.create`, `teams.create`, `matches.create`, `financial.create`, `performance.create`)
- **CSRF Token:** Required (`X-CSRF-Token`)
- **Request Headers:**
  - `Cookie: raptor_session=<64-hex-token>`
  - `X-CSRF-Token: <csrf-token>`
  - `Content-Type: application/json`

#### Request Example (Create Performance Record)
```json
{
  "player_id": 1,
  "team_id": 1,
  "category": "Aim & Accuracy",
  "score": 92.5,
  "date": "2026-10-25",
  "notes": "Excellent recoil stabilization in scrims"
}
```

#### Response (201 Created)
```json
{
  "item": {
    "id": 16,
    "player_id": 1,
    "player_name": "Sanku",
    "ign": "Sanku",
    "team_id": 1,
    "team_name": "Raptor (BGMI)",
    "category": "Aim & Accuracy",
    "score": 92.5,
    "date": "2026-10-25",
    "notes": "Excellent recoil stabilization in scrims",
    "created_at": "2026-10-25 14:30:00"
  }
}
```

#### Error Responses
- **400 Bad Request:** Validation error (e.g. invalid date, score > 100, invalid avatar, cross-team performance pairing):
  ```json
  {"error": "The performance record team must match the player's team"}
  ```
- **403 Forbidden:** Lacks create permission or record outside caller's resource scope:
  ```json
  {"error": "You do not have permission to create this record."}
  ```
- **409 Conflict:** Foreign key violation:
  ```json
  {"error": "This change conflicts with related records."}
  ```
- **413 Payload Too Large:** Body > 64,000 bytes.

---

### 8.4 `PUT /api/entities/<table_name>/<id>` (Update Record)
Modifies an existing record. Verifies authorization over both existing and destination resource scopes. Automatically recalculates `teams.players_count` on player roster edits.

- **HTTP Method:** `PUT`
- **URL Pattern:** `/api/entities/<table_name>/<id>`
- **Authentication:** Required
- **RBAC Permission:** Checked per table (`roster.update`, `teams.update`, `matches.update`, `financial.update`, `performance.update`)
- **CSRF Token:** Required (`X-CSRF-Token`)
- **Path Parameters:**
  - `table_name`: Target entity table
  - `id`: Primary key integer of the record to update

#### Request Example (Update Match Result)
```json
{
  "name": "BGMI Scrims",
  "game": "BGMI",
  "date": "2026-10-27",
  "time": "08:00 PM",
  "opponent": "Xtreme",
  "status": "Completed",
  "result": "Victory (15 Kills)"
}
```

#### Response (200 OK)
```json
{
  "item": {
    "id": 1,
    "name": "BGMI Scrims",
    "game": "BGMI",
    "date": "2026-10-27",
    "time": "08:00 PM",
    "opponent": "Xtreme",
    "tournament_id": null,
    "team_id": 1,
    "team_name": "Raptor (BGMI)",
    "status": "Completed",
    "result": "Victory (15 Kills)",
    "created_at": "2026-10-25 10:00:00"
  }
}
```

#### Error Responses
- **400 Bad Request:** Validation constraints failure.
- **403 Forbidden:** Scope violation or missing permission:
  ```json
  {"error": "You do not have permission to change this section."}
  ```
- **404 Not Found:** Record ID not found:
  ```json
  {"error": "Record not found"}
  ```
- **409 Conflict:** Foreign key conflict.

---

### 8.5 `DELETE /api/entities/<table_name>/<id>` (Delete Record)
Deletes an entity record. Verifies resource scope prior to execution. Automatically updates `teams.players_count` if a player is deleted.

- **HTTP Method:** `DELETE`
- **URL Pattern:** `/api/entities/<table_name>/<id>`
- **Authentication:** Required
- **RBAC Permission:** Checked per table (`roster.delete`, `teams.delete`, `matches.delete`, `financial.delete`, `performance.delete`)
- **CSRF Token:** Required (`X-CSRF-Token`)
- **Path Parameters:**
  - `table_name`: Target entity table
  - `id`: Primary key integer of the record to delete

#### Response (200 OK)
```json
{
  "ok": true
}
```

#### Error Responses
- **403 Forbidden:** Lacks delete permission or scope denied:
  ```json
  {"error": "You do not have permission to change this section."}
  ```
- **404 Not Found:** Record not found:
  ```json
  {"error": "Record not found"}
  ```
- **409 Conflict:** Record is linked to foreign key references:
  ```json
  {"error": "This record is linked to other data."}
  ```
