"""Local-only HTTP and JSON API for Raptor Esports."""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

import ai_assistant
import db
import rbac

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
SESSION_SECONDS = 60 * 60 * 12
ENTITY_ROUTE = re.compile(r"^/api/entities/([a-z_]+)(?:/(\d+))?$")
TEAM_PUBLIC_ROUTE = re.compile(r"^/api/public/teams/(\d+)$")
CHAT_LIMITER = ai_assistant.RateLimiter(limit=30, window_seconds=600)
PUBLIC_ORGANIZATION = {
    "name": "Raptor Esports",
    "description": "An Indian esports organization building competitive teams and community events.",
    "games": ["BGMI", "Free Fire", "Valorant"],
    "contact_email": "hello@raptoresports.local",
    "discord": "https://discord.gg/tjTjMpHvpa",
}


def compact(record: dict, fields: tuple[str, ...]) -> dict:
    """Keep only useful, present fields so prompts stay small and readable."""
    return {field: record[field] for field in fields if record.get(field) not in (None, "")}


def send_json(handler: BaseHTTPRequestHandler, status: int, payload: dict, headers: dict | None = None) -> None:
    data = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Cache-Control", "no-store")
    for key, value in (headers or {}).items(): handler.send_header(key, value)
    handler.end_headers()
    handler.wfile.write(data)


class PortalHandler(BaseHTTPRequestHandler):
    server_version = "RaptorPortal/1.0"

    def log_message(self, fmt, *args):
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))

    def read_json(self) -> dict:
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise ValueError("Invalid request size")
        if size > 64_000:
            raise OverflowError("Request is too large")
        if size == 0:
            return {}
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            raise ValueError("Request must use application/json")
        try:
            data = json.loads(self.rfile.read(size).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValueError("Request must contain valid JSON")
        if not isinstance(data, dict):
            raise ValueError("Request must be a JSON object")
        return data

    def cookie_values(self) -> dict:
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie", ""))
        except Exception:
            return {}
        return {k: morsel.value for k, morsel in cookie.items()}

    def current_session(self):
        token = self.cookie_values().get("raptor_session", "")
        if not re.fullmatch(r"[a-f0-9]{64}", token):
            return None
        with db.get_connection() as conn:
            row = conn.execute("SELECT s.*,u.email,u.name,u.role,u.player_id FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND s.expires_at>?", (token, datetime.now(timezone.utc).isoformat())).fetchone()
        return dict(row) if row else None

    def require_session(self):
        session = self.current_session()
        if not session:
            send_json(self, 401, {"error": "Please sign in to continue."})
            return None
        if session.get("role") not in rbac.ROLES:
            send_json(self, 403, {"error": "This account has no supported role."})
            return None
        return session

    def allowed(self, session, permission: str, *, team_id=None, player_id=None) -> bool:
        with db.get_connection() as conn:
            assigned = {row[0] for row in conn.execute("SELECT team_id FROM user_team_assignments WHERE user_id=?", (session["user_id"],))}
            own_team = None
            if session.get("player_id"):
                row = conn.execute("SELECT team_id FROM players WHERE id=?", (session["player_id"],)).fetchone()
                own_team = row[0] if row else None
        return rbac.resource_allowed(session.get("role"), permission, team_id=team_id, player_id=player_id,
                                     assigned_team_ids=assigned, own_team_id=own_team,
                                     own_player_id=session.get("player_id"))

    def demand(self, session, permission: str, *, team_id=None, player_id=None) -> bool:
        if self.allowed(session, permission, team_id=team_id, player_id=player_id):
            return True
        send_json(self, 403, {"error": "You do not have permission to perform this action."})
        return False

    def scoped_records(self, session, table: str) -> list[dict]:
        """Return only the records the signed-in role may read."""
        permission = self.entity_permission(table, "view")
        if not permission or not rbac.has_permission(session.get("role"), permission):
            return []
        records = []
        for item in db.list_records(table):
            team_id = item.get("team_id", item.get("id") if table == "teams" else None)
            player_id = item.get("player_id", item.get("id") if table == "players" else None)
            if self.allowed(session, permission, team_id=team_id, player_id=player_id):
                records.append(item)
        return records

    @staticmethod
    def entity_permission(table: str, operation: str) -> str | None:
        permissions = {
            "players": {"view": "roster.view", "create": "roster.create", "update": "roster.update", "delete": "roster.delete"},
            "teams": {"view": "teams.view_all", "create": "teams.create", "update": "teams.update", "delete": "teams.delete"},
            "tournaments": {"view": "matches.view_all", "create": "matches.create", "update": "matches.update", "delete": "matches.delete"},
            "matches": {"view": "matches.view_all", "create": "matches.create", "update": "matches.update", "delete": "matches.delete"},
            "expenses": {"view": "financial.view", "create": "financial.create", "update": "financial.update", "delete": "financial.delete"},
            "performance_records": {"view": "performance.view_all", "create": "performance.create", "update": "performance.update", "delete": "performance.delete"},
        }
        return permissions.get(table, {}).get(operation)

    def dashboard_for_user(self, session):
        teams = [item for item in db.list_records("teams") if self.allowed(session, "teams.view_all", team_id=item["id"])]
        team_ids = {item["id"] for item in teams}
        players = [item for item in db.list_records("players") if self.allowed(session, "roster.view", team_id=item.get("team_id"), player_id=item["id"])]
        matches = [item for item in db.list_records("matches") if self.allowed(session, "matches.view_all", team_id=item.get("team_id")) and item.get("date", "") >= datetime.now().date().isoformat()][:5]
        tournaments = [item for item in db.list_records("tournaments") if self.allowed(session, "matches.view_all", team_id=item.get("team_id"))]
        activity = db.recent_activity(10) if session.get("role") in {"admin", "manager"} else []
        if not self.allowed(session, "financial.view"):
            activity = [event for event in activity if event.get("kind") != "expense"]
        can_view_expenses = self.allowed(session, "financial.view")
        stats = {"players": len(players), "teams": len(teams), "tournaments": len(tournaments), "expenses": 0}
        if can_view_expenses:
            stats["expenses"] = sum(float(row.get("amount") or 0) for row in db.list_records("expenses"))
        return {"stats": stats, "matches": matches, "activity": activity[:5], "can_view_expenses": can_view_expenses}

    def reports_for_user(self, session):
        teams = [row for row in db.list_records("teams") if self.allowed(session, "teams.view_all", team_id=row["id"])]
        players = [row for row in db.list_records("players") if self.allowed(session, "roster.view", team_id=row.get("team_id"), player_id=row["id"])]
        performances = [row for row in db.list_records("performance_records") if self.allowed(session, "performance.view_all", team_id=row.get("team_id"), player_id=row.get("player_id"))]
        matches = [row for row in db.list_records("matches") if self.allowed(session, "matches.view_all", team_id=row.get("team_id"))]
        competitions = [row for row in db.list_records("tournaments") if self.allowed(session, "matches.view_all", team_id=row.get("team_id"))]
        can_view_expenses = self.allowed(session, "financial.view")
        result = {"teams": len(teams), "players": len(players), "performance_records": len(performances),
                  "average_score": round(sum(float(row["score"]) for row in performances) / len(performances), 1) if performances else None,
                  "matches": len(matches), "competitions": len(competitions), "can_view_expenses": can_view_expenses}
        if can_view_expenses:
            result["expenses_total"] = sum(float(row.get("amount") or 0) for row in db.list_records("expenses"))
        return result

    def public_chat_context(self) -> dict:
        """Context for visitors: public teams, rosters, events, and contact info only."""
        public = db.public_data()
        team_names = {team["id"]: team["name"] for team in public["teams"]}
        teams = []
        for team in public["teams"][:12]:
            detail = db.public_team_data(team["id"]) or {}
            teams.append({
                **compact(team, ("name", "game", "players_count", "status", "description")),
                "roster": [compact(player, ("ign", "role", "status")) for player in detail.get("players", [])[:10]],
            })
        today = datetime.now().date().isoformat()
        matches = []
        for match in db.list_records("matches"):
            if match.get("date", "") < today or match.get("status") not in ("Upcoming", "Live"):
                continue
            matches.append({
                **compact(match, ("name", "game", "date", "time", "opponent", "status")),
                "team": team_names.get(match.get("team_id"), ""),
            })
        tournaments = [
            {
                **compact(item, ("name", "game", "date", "status", "location", "prize_pool")),
                "team": team_names.get(item.get("team_id"), ""),
            }
            for item in public["tournaments"][:8]
        ]
        return {
            "mode": "public",
            "organization": PUBLIC_ORGANIZATION,
            "stats": public["stats"],
            "teams": teams,
            "matches": matches[:5],
            "tournaments": tournaments,
            "capabilities": [
                "public team and roster information",
                "tournament and match schedules",
                "how to join or contact Raptor",
            ],
        }

    def authorized_chat_context(self, session) -> dict:
        """Context for a signed-in role, filtered with the same rules as the API."""
        role = session.get("role")
        dashboard = self.dashboard_for_user(session)
        teams = self.scoped_records(session, "teams")
        players = self.scoped_records(session, "players")
        matches = self.scoped_records(session, "matches")
        tournaments = self.scoped_records(session, "tournaments")
        performance = self.scoped_records(session, "performance_records")
        can_view_expenses = self.allowed(session, "financial.view")
        expenses = self.scoped_records(session, "expenses") if can_view_expenses else []
        team_names = {team["id"]: team["name"] for team in teams}

        stats = dict(dashboard.get("stats") or {})
        if not can_view_expenses:
            stats.pop("expenses", None)

        capabilities = []
        if rbac.has_permission(role, "roster.view"):
            capabilities.append("team rosters")
        if rbac.has_permission(role, "performance.view_all"):
            capabilities.append("performance records")
        if rbac.has_permission(role, "matches.view_all"):
            capabilities.append("matches and competitions")
        if can_view_expenses:
            capabilities.append("expenses and spending")
        if role in {"admin", "manager"}:
            capabilities.append("recent activity")
        capabilities.append("general esports guidance")

        context = {
            "mode": "authenticated",
            "user": {
                "name": session.get("name"),
                "role": role,
                "role_name": rbac.ROLES.get(role, {}).get("display_name", role),
            },
            "organization": PUBLIC_ORGANIZATION,
            "capabilities": capabilities,
            "stats": stats,
            "teams": [compact(team, ("name", "game", "players_count", "status", "description")) for team in teams[:50]],
            "players": [
                {
                    **compact(player, ("name", "ign", "role", "game", "status")),
                    "team_name": player.get("team_name", ""),
                }
                for player in players[:100]
            ],
            "matches": [
                {
                    **compact(match, ("name", "game", "date", "time", "opponent", "status", "result")),
                    "team_name": team_names.get(match.get("team_id"), ""),
                    "tournament_name": match.get("tournament_name", ""),
                }
                for match in matches[:50]
            ],
            "tournaments": [
                {
                    **compact(tournament, ("name", "game", "date", "prize_pool", "status", "location")),
                    "team_name": team_names.get(tournament.get("team_id"), ""),
                }
                for tournament in tournaments[:50]
            ],
        }
        if performance:
            context["performance"] = [
                {
                    **compact(record, ("date", "player_name", "ign", "category", "score", "notes")),
                    "team_name": team_names.get(record.get("team_id"), "") or record.get("team_name", ""),
                }
                for record in performance[:100]
            ]
        if can_view_expenses:
            expense_items = [
                compact(expense, ("title", "category", "amount", "date", "notes"))
                for expense in expenses[:50]
            ]
            context["expenses"] = {
                "total": round(sum(float(expense.get("amount") or 0) for expense in expenses), 2),
                "items": expense_items,
            }
        activity = dashboard.get("activity") or []
        if activity:
            context["activity"] = [compact(event, ("message", "kind", "created_at")) for event in activity[:10]]
        return context

    def check_csrf(self, session) -> bool:
        if not session or not hmac.compare_digest(str(session["csrf"]), str(self.headers.get("X-CSRF-Token", ""))):
            send_json(self, 403, {"error": "Your session expired. Refresh and try again."})
            return False
        return True

    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if path.startswith("/api/"):
            return self.handle_get_api(path)
        if path == "/api":
            return send_json(self, 404, {"error": "Not found"})
        if path in ("/", "/index.html"):
            return self.serve_file(ROOT / "index.html")
        if path.lower() == "/hero-video.mp4":
            return self.serve_file(ROOT / "Hero-video.mp4")
        if path in ("/login", "/login.html"):
            return self.serve_file(ROOT / "login.html")
        if path in ("/admin", "/admin.html", "/dashboard"):
            session = self.current_session()
            if not session:
                self.send_response(302); self.send_header("Location", "/login"); self.end_headers(); return
            if session.get("role") not in rbac.ROLES:
                return send_json(self, 403, {"error": "This account has no supported role."})
            if path != "/dashboard" and not rbac.has_permission(session.get("role"), "admin.access"):
                self.send_response(302); self.send_header("Location", "/dashboard"); self.end_headers(); return
            return self.serve_file(ROOT / "admin.html")
        if re.fullmatch(r"/teams/\d+", path):
            return self.serve_file(ROOT / "team-detail.html")
        if path.startswith("/assets/"):
            assets_root = (ROOT / "assets").resolve()
            candidate = (ROOT / path.lstrip("/")).resolve()
            if candidate != assets_root and assets_root not in candidate.parents:
                return send_json(self, 403, {"error": "Forbidden"})
            return self.serve_file(candidate)
        return self.serve_file(ROOT / "index.html") if not Path(path).suffix else send_json(self, 404, {"error": "Not found"})

    def serve_file(self, path: Path):
        try:
            resolved = path.resolve(strict=True)
            if ROOT.resolve() not in resolved.parents and resolved != ROOT.resolve():
                return send_json(self, 403, {"error": "Forbidden"})
            safe_suffixes = {".html", ".css", ".js", ".svg", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico", ".woff", ".woff2", ".ttf", ".mp4", ".webm"}
            if resolved.suffix.lower() not in safe_suffixes:
                return send_json(self, 404, {"error": "Page not found"})
            data = resolved.read_bytes()
        except (FileNotFoundError, IsADirectoryError):
            return send_json(self, 404, {"error": "Page not found"})
        content_type = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
            ".svg": "image/svg+xml",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".gif": "image/gif",
            ".ico": "image/x-icon",
            ".woff": "font/woff",
            ".woff2": "font/woff2",
            ".ttf": "font/ttf",
            ".mp4": "video/mp4",
            ".webm": "video/webm",
        }.get(resolved.suffix.lower(), "application/octet-stream")
        # Byte-range support for video: scrubbing relies on seekable ranges,
        # and without 206/Content-Range the browser clamps every video seek
        # to byte 0 (the clip freezes on its first frame mid-scrub).
        total = len(data)
        start, end, status = 0, total - 1, 200
        is_media = resolved.suffix.lower() in (".mp4", ".webm")
        range_header = self.headers.get("Range", "") if is_media else ""
        if range_header.startswith("bytes="):
            a, _, b = range_header[6:].partition("-")
            try:
                if a:
                    start = max(0, int(a)); end = int(b) if b else total - 1
                elif b:
                    start = max(0, total - int(b))
                end = min(end, total - 1)
                if start > end or start >= total:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{total}")
                    self.end_headers()
                    return
            except ValueError:
                start, end = 0, total - 1
            if start > 0 or end < total - 1:
                status = 206
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        if is_media:
            self.send_header("Accept-Ranges", "bytes")
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{total}")
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; media-src 'self' blob:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(data[start:end + 1])

    def handle_get_api(self, path: str):
        if path == "/api/public":
            return send_json(self, 200, db.public_data())
        team_match = TEAM_PUBLIC_ROUTE.fullmatch(path)
        if team_match:
            team_data = db.public_team_data(int(team_match.group(1)))
            if not team_data: return send_json(self, 404, {"error": "Team not found"})
            return send_json(self, 200, team_data)
        if path == "/api/chat/session":
            session = self.current_session()
            if not session or session.get("role") not in rbac.ROLES:
                return send_json(self, 200, {"authenticated": False, "user": None, "permissions": {}, "csrf": None})
            return send_json(self, 200, {
                "authenticated": True,
                "user": {"name": session["name"], "email": session["email"], "role": session["role"]},
                "permissions": rbac.PERMISSIONS.get(session.get("role"), {}),
                "csrf": session["csrf"],
            })
        if path == "/api/me":
            session = self.current_session()
            if not session:
                return send_json(self, 401, {"error": "Please sign in."})
            if session.get("role") not in rbac.ROLES:
                return send_json(self, 403, {"error": "This account has no supported role."})
            with db.get_connection() as conn:
                assigned = [row[0] for row in conn.execute("SELECT team_id FROM user_team_assignments WHERE user_id=?", (session["user_id"],))]
            return send_json(self, 200, {"user": {"name": session["name"], "email": session["email"], "role": session["role"], "player_id": session.get("player_id"), "team_ids": assigned}, "permissions": rbac.PERMISSIONS.get(session.get("role"), {}), "csrf": session["csrf"]})
        session = self.require_session()
        if not session: return
        if path == "/api/dashboard":
            if not rbac.has_permission(session.get("role"), "analytics.view"):
                return send_json(self, 403, {"error": "You do not have permission to view the dashboard."})
            return send_json(self, 200, self.dashboard_for_user(session))
        if path == "/api/reports":
            if not rbac.has_permission(session.get("role"), "reports.view"):
                return send_json(self, 403, {"error": "You do not have permission to view reports."})
            return send_json(self, 200, self.reports_for_user(session))
        if path == "/api/users":
            if not self.demand(session, "users.view_all"): return
            return send_json(self, 200, {"items": db.list_users()})
        if path == "/api/assignments":
            if not rbac.has_permission(session.get("role"), "teams.assign_coaches"): return send_json(self, 403, {"error": "You do not have permission to assign coaches."})
            return send_json(self, 200, {"items": db.list_assignments("coach" if session.get("role") == "manager" else None)})
        if path == "/api/coaches":
            if not rbac.has_permission(session.get("role"), "teams.assign_coaches"): return send_json(self, 403, {"error": "You do not have permission to assign coaches."})
            return send_json(self, 200, {"items": db.list_assignable_staff(("coach",) if session.get("role") == "manager" else ("coach", "analyst"))})
        match = ENTITY_ROUTE.fullmatch(path)
        if match and match.group(1) in db.TABLES:
            table = match.group(1)
            permission = self.entity_permission(table, "view")
            if not permission or not rbac.has_permission(session.get("role"), permission): return send_json(self, 403, {"error": "You do not have permission to view this section."})
            return send_json(self, 200, {"items": self.scoped_records(session, table)})
        return send_json(self, 404, {"error": "Not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            body = self.read_json()
        except OverflowError as exc:
            return send_json(self, 413, {"error": str(exc)})
        except ValueError as exc:
            return send_json(self, 400, {"error": str(exc)})
        if path == "/api/login":
            return self.login(body)
        if path == "/api/chat":
            return self.chat(body)
        session = self.require_session()
        if not session: return
        if not self.check_csrf(session): return
        if path == "/api/logout":
            token = self.cookie_values().get("raptor_session", "")
            with db.get_connection() as conn: conn.execute("DELETE FROM sessions WHERE token=?", (token,))
            self.send_response(200)
            self.send_header("Set-Cookie", "raptor_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0")
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
            return
        if path == "/api/users":
            if not self.demand(session, "users.create"): return
            try:
                role = str(body.get("role", ""))
                if body.get("team_id") not in (None, "") and role not in {"coach", "analyst"}:
                    return send_json(self, 400, {"error": "Initial team access is only valid for coach or analyst accounts."})
                if body.get("team_id") not in (None, ""):
                    with db.get_connection() as conn:
                        if not conn.execute("SELECT 1 FROM teams WHERE id=?", (body["team_id"],)).fetchone():
                            return send_json(self, 400, {"error": "Choose an existing team."})
                user = db.create_user(str(body.get("email", "")), str(body.get("name", "")), str(body.get("role", "")), str(body.get("password", "")), body.get("player_id"))
                if body.get("team_id"):
                    db.set_user_team_assignment(user["id"], int(body["team_id"]))
                return send_json(self, 201, {"user": user})
            except ValueError as exc: return send_json(self, 400, {"error": str(exc)})
            except sqlite3.IntegrityError: return send_json(self, 409, {"error": "That account already exists or the linked record is invalid."})
        if path == "/api/assignments":
            if not self.demand(session, "teams.assign_coaches"): return
            try:
                target_id = int(body["user_id"])
                with db.get_connection() as conn:
                    target = conn.execute("SELECT role FROM users WHERE id=?", (target_id,)).fetchone()
                if not rbac.can_assign_team_role(session.get("role"), target["role"] if target else None):
                    return send_json(self, 403, {"error": "This role cannot be assigned by your account."})
                db.set_user_team_assignment(target_id, int(body["team_id"]))
                return send_json(self, 201, {"ok": True})
            except (KeyError, ValueError) as exc: return send_json(self, 400, {"error": str(exc) or "Choose a coach or analyst and team."})
            except LookupError as exc: return send_json(self, 404, {"error": str(exc)})
        if path == "/api/assistant":
            if not rbac.has_permission(session.get("role"), "analytics.view"):
                return send_json(self, 403, {"error": "You do not have permission to use the assistant."})
            return self.assistant(body)
        match = ENTITY_ROUTE.fullmatch(path)
        if match and not match.group(2) and match.group(1) in db.TABLES:
            table = match.group(1)
            permission = self.entity_permission(table, "create")
            if not permission or not rbac.has_permission(session.get("role"), permission): return send_json(self, 403, {"error": "You do not have permission to create this record."})
            if table == "performance_records" and session.get("role") == "player":
                body["player_id"] = session.get("player_id")
                with db.get_connection() as conn:
                    linked = conn.execute("SELECT team_id FROM players WHERE id=?", (session.get("player_id"),)).fetchone()
                body["team_id"] = linked["team_id"] if linked else None
            if table == "performance_records" and not body.get("team_id") and body.get("player_id"):
                with db.get_connection() as conn:
                    linked = conn.execute("SELECT team_id FROM players WHERE id=?", (body["player_id"],)).fetchone()
                body["team_id"] = linked["team_id"] if linked else None
            team_id = body.get("team_id")
            player_id = body.get("player_id")
            if permission in {"roster.create", "performance.create", "matches.create"} and not self.demand(session, permission, team_id=team_id, player_id=player_id): return
            try: return send_json(self, 201, {"item": db.save_record(table, None, body)})
            except ValueError as exc: return send_json(self, 400, {"error": str(exc)})
            except sqlite3.IntegrityError: return send_json(self, 409, {"error": "This change conflicts with related records."})
        return send_json(self, 404, {"error": "Not found"})

    def do_PUT(self):
        self.mutate_entity("update")

    def do_DELETE(self):
        self.mutate_entity("delete")

    def mutate_entity(self, action: str):
        path = urlparse(self.path).path
        session = self.require_session()
        if not session: return
        if not self.check_csrf(session): return
        user_match = re.fullmatch(r"/api/users/(\d+)", path)
        if user_match:
            user_id = int(user_match.group(1))
            if user_id == session["user_id"]:
                return send_json(self, 403, {"error": "You cannot change or delete your own account role here."})
            permission = "users.update_role" if action == "update" else "users.delete"
            if not self.demand(session, permission): return
            try:
                if action == "delete":
                    db.delete_user(user_id)
                    return send_json(self, 200, {"ok": True})
                body = self.read_json()
                db.update_user_account(user_id, str(body.get("role", "")), body.get("team_ids"))
                return send_json(self, 200, {"ok": True})
            except OverflowError as exc: return send_json(self, 413, {"error": str(exc)})
            except ValueError as exc: return send_json(self, 400, {"error": str(exc)})
            except LookupError as exc: return send_json(self, 404, {"error": str(exc)})
        assignment_match = re.fullmatch(r"/api/assignments/(\d+)/(\d+)", path)
        if action == "delete" and assignment_match:
            if not self.demand(session, "teams.assign_coaches"): return
            try:
                target_id = int(assignment_match.group(1))
                with db.get_connection() as conn:
                    target = conn.execute("SELECT role FROM users WHERE id=?", (target_id,)).fetchone()
                if not target: return send_json(self, 404, {"error": "User not found"})
                if not rbac.can_assign_team_role(session.get("role"), target["role"]):
                    return send_json(self, 403, {"error": "This role cannot be assigned by your account."})
                db.set_user_team_assignment(target_id, int(assignment_match.group(2)), False)
                return send_json(self, 200, {"ok": True})
            except (LookupError, ValueError) as exc: return send_json(self, 404, {"error": str(exc)})
        match = ENTITY_ROUTE.fullmatch(path)
        if not match or not match.group(2) or match.group(1) not in db.TABLES:
            return send_json(self, 404, {"error": "Not found"})
        table, record_id = match.group(1), int(match.group(2))
        operation = "delete" if action == "delete" else "update"
        permission = self.entity_permission(table, operation)
        if not permission or not rbac.has_permission(session.get("role"), permission):
            return send_json(self, 403, {"error": "You do not have permission to change this section."})
        record = next((item for item in db.list_records(table) if item.get("id") == record_id), None)
        if not record: return send_json(self, 404, {"error": "Record not found"})
        team_id = record.get("team_id", record_id if table == "teams" else None)
        player_id = record.get("player_id", record_id if table == "players" else None)
        if not self.demand(session, permission, team_id=team_id, player_id=player_id): return
        if action == "delete":
            try:
                db.delete_record(table, record_id)
                return send_json(self, 200, {"ok": True})
            except LookupError as exc: return send_json(self, 404, {"error": str(exc)})
            except sqlite3.IntegrityError: return send_json(self, 409, {"error": "This record is linked to other data."})
        try:
            body = self.read_json()
            destination_team = body.get("team_id", team_id)
            destination_player = body.get("player_id", player_id)
            if table == "performance_records" and "team_id" not in body and body.get("player_id"):
                with db.get_connection() as conn:
                    linked = conn.execute("SELECT team_id FROM players WHERE id=?", (body["player_id"],)).fetchone()
                destination_team = linked["team_id"] if linked else None
            if table in {"players", "matches", "tournaments", "performance_records"} and not self.demand(session, permission, team_id=destination_team, player_id=destination_player): return
            return send_json(self, 200, {"item": db.save_record(table, record_id, body)})
        except OverflowError as exc: return send_json(self, 413, {"error": str(exc)})
        except ValueError as exc: return send_json(self, 400, {"error": str(exc)})
        except LookupError as exc: return send_json(self, 404, {"error": str(exc)})
        except sqlite3.IntegrityError: return send_json(self, 409, {"error": "This change conflicts with related records."})

    def login(self, body: dict):
        identity = str(body.get("identity", "")).strip().lower()[:200]
        password = str(body.get("password", ""))
        if not identity or not password or len(password) > 256:
            return send_json(self, 400, {"error": "Enter your email and password."})
        with db.get_connection() as conn:
            user = conn.execute("SELECT * FROM users WHERE lower(email)=?", (identity,)).fetchone()
        if not user:
            hashlib.pbkdf2_hmac("sha256", password.encode(), b"raptor-timing-salt", 310_000)
            return send_json(self, 401, {"error": "That email or password isn’t correct."})
        if user["role"] not in rbac.ROLES:
            return send_json(self, 403, {"error": "This account has no supported role."})
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), user["salt"], 310_000)
        if not hmac.compare_digest(candidate, user["password_hash"]):
            return send_json(self, 401, {"error": "That email or password isn’t correct."})
        token, csrf = secrets.token_hex(32), secrets.token_urlsafe(32)
        expires = (datetime.now(timezone.utc) + timedelta(seconds=SESSION_SECONDS)).isoformat()
        with db.get_connection() as conn:
            conn.execute("DELETE FROM sessions WHERE expires_at<=?", (datetime.now(timezone.utc).isoformat(),))
            conn.execute("INSERT INTO sessions(token,user_id,csrf,expires_at) VALUES(?,?,?,?)", (token, user["id"], csrf, expires))
        send_json(self, 200, {"user": {"name": user["name"], "email": user["email"], "role": user["role"]}, "csrf": csrf}, {"Set-Cookie": f"raptor_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={SESSION_SECONDS}"})

    def chat(self, body: dict):
        """Public/session-aware chat used by the floating Raptor AI Assistant."""
        client_ip = self.client_address[0] if self.client_address else "unknown"
        if not CHAT_LIMITER.allow(client_ip):
            return send_json(self, 429, {"error": "Too many messages. Please wait a few minutes and try again."}, {"Retry-After": "60"})
        try:
            history = ai_assistant.normalize_history(body)
        except ValueError as exc:
            return send_json(self, 400, {"error": str(exc)})
        session = self.current_session()
        if session:
            if session.get("role") not in rbac.ROLES:
                return send_json(self, 403, {"error": "This account has no supported role."})
            if not self.check_csrf(session):
                return
            context = self.authorized_chat_context(session)
            authenticated = True
        else:
            context = self.public_chat_context()
            authenticated = False
        result = ai_assistant.chat(context, history)
        return send_json(self, 200, {**result, "authenticated": authenticated})

    def assistant(self, body: dict):
        """Workspace assistant page; shares the same AI and role-scoped context."""
        question = str(body.get("question", "")).strip()[:500]
        if not question: return send_json(self, 400, {"error": "Type a question first."})
        session = self.require_session()
        if not session: return
        context = self.authorized_chat_context(session)
        result = ai_assistant.chat(context, [{"role": "user", "content": question}])
        with db.get_connection() as conn: conn.execute("INSERT INTO assistant_messages(question,answer) VALUES(?,?)", (question, result["answer"]))
        return send_json(self, 200, {**result, "authenticated": True})

    def do_HEAD(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"): return self.serve_file(ROOT / "index.html")
        return send_json(self, 404, {"error": "Not found"})


def main():
    db.initialize()
    host, port = "127.0.0.1", 5050
    print(f"Raptor Esports portal running at http://{host}:{port}")
    print("Local demo accounts use Raptor@2026 (override with RAPTOR_DEMO_PASSWORD).")
    ThreadingHTTPServer((host, port), PortalHandler).serve_forever()


if __name__ == "__main__":
    main()
