"""SQLite persistence and seed data for the Raptor Esports portal."""
from __future__ import annotations

import hashlib
import os
import random
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path
import rbac

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("RAPTOR_DB_PATH", ROOT / "data" / "raptor.sqlite3"))
TABLES = {"players", "teams", "tournaments", "matches", "expenses", "performance_records"}
# Player avatar art shipped in assets/players/ (public, same-origin). Anything not
# in this tuple is rejected by _validate and falls back to the initials circle.
AVATARS = (
    "01-hood.png", "02-raptor.png", "03-trooper.png", "04-oni.png",
    "05-wolf.png", "06-skull.png", "07-fox.png", "08-phoenix.png",
)
AVATAR_DIR = "assets/players"
FIELDS = {
    "players": {"name", "ign", "role", "team_id", "status", "game", "joined_at", "avatar"},
    "teams": {"name", "game", "players_count", "status", "description", "accent"},
    "tournaments": {"name", "game", "date", "prize_pool", "status", "location", "team_id"},
    "matches": {"name", "game", "date", "time", "opponent", "tournament_id", "team_id", "status", "result"},
    "expenses": {"title", "category", "amount", "date", "notes"},
    "performance_records": {"player_id", "team_id", "category", "score", "date", "notes"},
}
REQUIRED = {
    "players": {"name", "ign", "role", "status"},
    "teams": {"name", "game"},
    "tournaments": {"name", "game", "date", "prize_pool", "status"},
    "matches": {"name", "game", "date", "time", "status"},
    "expenses": {"title", "category", "amount", "date"},
    "performance_records": {"player_id", "category", "score", "date"},
}


@contextmanager
def get_connection():
    """Yield a SQLite connection, committing or rolling back and closing it."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def hash_password(password: str, salt: bytes | None = None) -> tuple[bytes, bytes]:
    salt = salt or secrets.token_bytes(16)
    return salt, hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)


def initialize() -> None:
    with get_connection() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, name TEXT NOT NULL, salt BLOB NOT NULL, password_hash BLOB NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, csrf TEXT NOT NULL, expires_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS teams(id INTEGER PRIMARY KEY, name TEXT NOT NULL, game TEXT NOT NULL, players_count INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'Active', description TEXT NOT NULL DEFAULT '', accent TEXT NOT NULL DEFAULT 'violet', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS players(id INTEGER PRIMARY KEY, name TEXT NOT NULL, ign TEXT NOT NULL, role TEXT NOT NULL, team_id INTEGER REFERENCES teams(id) ON DELETE SET NULL, status TEXT NOT NULL DEFAULT 'Active', game TEXT NOT NULL DEFAULT '', joined_at TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS tournaments(id INTEGER PRIMARY KEY, name TEXT NOT NULL, game TEXT NOT NULL, date TEXT NOT NULL, prize_pool REAL NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'Upcoming', location TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS matches(id INTEGER PRIMARY KEY, name TEXT NOT NULL, game TEXT NOT NULL, date TEXT NOT NULL, time TEXT NOT NULL DEFAULT '08:00 PM', opponent TEXT NOT NULL DEFAULT '', tournament_id INTEGER REFERENCES tournaments(id) ON DELETE SET NULL, status TEXT NOT NULL DEFAULT 'Upcoming', result TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS expenses(id INTEGER PRIMARY KEY, title TEXT NOT NULL, category TEXT NOT NULL, amount REAL NOT NULL CHECK(amount >= 0), date TEXT NOT NULL, notes TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS activity_events(id INTEGER PRIMARY KEY, message TEXT NOT NULL, kind TEXT NOT NULL DEFAULT 'info', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS assistant_messages(id INTEGER PRIMARY KEY, question TEXT NOT NULL, answer TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS data_migrations(key TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(date);
        CREATE INDEX IF NOT EXISTS idx_players_team ON players(team_id);
        """)
        # Idempotent schema upgrades retain existing portal data.
        user_columns = {row["name"] for row in db.execute("PRAGMA table_info(users)")}
        migrated_roles = "role" not in user_columns
        if migrated_roles:
            db.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'player'")
        if "player_id" not in user_columns:
            db.execute("ALTER TABLE users ADD COLUMN player_id INTEGER REFERENCES players(id) ON DELETE SET NULL")
        match_columns = {row["name"] for row in db.execute("PRAGMA table_info(matches)")}
        if "team_id" not in match_columns:
            db.execute("ALTER TABLE matches ADD COLUMN team_id INTEGER REFERENCES teams(id) ON DELETE SET NULL")
        tournament_columns = {row["name"] for row in db.execute("PRAGMA table_info(tournaments)")}
        if "team_id" not in tournament_columns:
            db.execute("ALTER TABLE tournaments ADD COLUMN team_id INTEGER REFERENCES teams(id) ON DELETE SET NULL")
        player_columns = {row["name"] for row in db.execute("PRAGMA table_info(players)")}
        if "avatar" not in player_columns:
            db.execute("ALTER TABLE players ADD COLUMN avatar TEXT NOT NULL DEFAULT ''")
        db.execute("UPDATE matches SET team_id=(SELECT id FROM teams WHERE teams.game=matches.game ORDER BY id LIMIT 1) WHERE team_id IS NULL")
        db.execute("UPDATE tournaments SET team_id=(SELECT id FROM teams WHERE teams.game=tournaments.game ORDER BY id LIMIT 1) WHERE team_id IS NULL")
        db.executescript("""
        CREATE TABLE IF NOT EXISTS user_team_assignments(user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE, PRIMARY KEY(user_id,team_id));
        CREATE TABLE IF NOT EXISTS performance_records(id INTEGER PRIMARY KEY, player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE, team_id INTEGER REFERENCES teams(id) ON DELETE SET NULL, category TEXT NOT NULL, score REAL NOT NULL DEFAULT 0, date TEXT NOT NULL, notes TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE INDEX IF NOT EXISTS idx_assignments_user ON user_team_assignments(user_id);
        CREATE INDEX IF NOT EXISTS idx_performance_player ON performance_records(player_id);
        """)
        if db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            password = os.environ.get("RAPTOR_DEMO_PASSWORD", "Raptor@2026")
            salt, digest = hash_password(password)
            db.execute("INSERT INTO users(email,name,salt,password_hash) VALUES(?,?,?,?)", ("admin@raptor.local", "Admin", salt, digest))
            teams = [("Raptor (BGMI)", "BGMI", 5, "India's next competitive BGMI lineup.", "violet"), ("Phoenix (Free Fire)", "Free Fire", 4, "Fast, fearless and always in the fight.", "amber"), ("Shadow (BGMI)", "BGMI", 3, "A rising roster built for the big stage.", "pink"), ("Vortex (Valorant)", "Valorant", 4, "Precision, teamwork, momentum.", "cyan")]
            db.executemany("INSERT INTO teams(name,game,players_count,description,accent) VALUES(?,?,?,?,?)", teams)
            players = [("Sanku", "Sanku", "IGL", 1, "Active", "BGMI"), ("Shisui", "Shisui", "Assaulter", 1, "Active", "BGMI"), ("Naruto", "Naruto", "Support", 1, "Active", "BGMI"), ("Dazzler", "Dazzler", "Assaulter", 1, "Active", "BGMI"), ("Zero", "Zero", "Support", 1, "Active", "BGMI"), ("Blaze", "Blaze", "IGL", 2, "Active", "Free Fire")]
            db.executemany("INSERT INTO players(name,ign,role,team_id,status,game) VALUES(?,?,?,?,?,?)", players)
            today = date.today()
            tournaments = [("Raptor Cup #01", "BGMI", (today + timedelta(days=3)).isoformat(), 5000, "Upcoming", "Online"), ("Free Fire Showdown", "Free Fire", (today + timedelta(days=10)).isoformat(), 3000, "Ongoing", "Mumbai"), ("Valorant Challenge", "Valorant", (today + timedelta(days=23)).isoformat(), 4000, "Upcoming", "Online"), ("BGMI Scrims", "BGMI", (today + timedelta(days=30)).isoformat(), 2000, "Upcoming", "Online")]
            db.executemany("INSERT INTO tournaments(name,game,date,prize_pool,status,location) VALUES(?,?,?,?,?,?)", tournaments)
            matches = [("BGMI Scrims", "BGMI", (today + timedelta(days=2)).isoformat(), "08:00 PM", "Xtreme", 1, "Upcoming", ""), ("BGMI Tournament", "BGMI", (today + timedelta(days=5)).isoformat(), "05:00 PM", "Team Soul", 1, "Upcoming", ""), ("Free Fire Match", "Free Fire", (today + timedelta(days=8)).isoformat(), "07:00 PM", "7Sea", 2, "Upcoming", "")]
            db.executemany("INSERT INTO matches(name,game,date,time,opponent,tournament_id,status,result) VALUES(?,?,?,?,?,?,?,?)", matches)
            db.executemany("INSERT INTO expenses(title,category,amount,date,notes) VALUES(?,?,?,?,?)", [("Prize Money", "Tournament", 2000, today.isoformat(), "Team placement reward"), ("Team jerseys", "Equipment", 10500, today.isoformat(), "New season kit")])
            db.executemany("INSERT INTO activity_events(message,kind) VALUES(?,?)", [("Shisui joined the team", "player"), ("Raptor Cup #01 created", "tournament"), ("Prize money expense added", "expense")])
        db.execute("UPDATE users SET role='admin' WHERE lower(email)='admin@raptor.local'")
        if migrated_roles:
            demo_password = os.environ.get("RAPTOR_DEMO_PASSWORD", "Raptor@2026")
            salt, digest = hash_password(demo_password)
            db.execute("UPDATE users SET salt=?,password_hash=? WHERE lower(email)='admin@raptor.local'", (salt, digest))
        _seed_role_accounts(db)
        db.execute("UPDATE matches SET team_id=(SELECT id FROM teams WHERE teams.game=matches.game ORDER BY id LIMIT 1) WHERE team_id IS NULL")
        db.execute("UPDATE tournaments SET team_id=(SELECT id FROM teams WHERE teams.game=tournaments.game ORDER BY id LIMIT 1) WHERE team_id IS NULL")
    expand_sample_data()
    assign_player_avatars()


def assign_player_avatars() -> dict:
    """One-time: give every unassigned player one of AVATARS, round-robin over a
    shuffled deck so all eight arts appear and no art dominates. Guarded by a
    migration key so later restarts never reshuffle a player the admin picked."""
    migration_key = "player_avatars_v1"
    with get_connection() as conn:
        if conn.execute("SELECT 1 FROM data_migrations WHERE key=?", (migration_key,)).fetchone():
            return {"assigned": 0}
        rows = conn.execute("SELECT id FROM players ORDER BY id").fetchall()
        if not rows:
            conn.execute("INSERT INTO data_migrations(key) VALUES(?)", (migration_key,))
            return {"assigned": 0}
        deck = list(AVATARS)
        random.Random(len(rows) * 7 + sum(row["id"] for row in rows)).shuffle(deck)
        assigned = 0
        for index, row in enumerate(rows):
            avatar = deck[index % len(deck)]
            cursor = conn.execute("UPDATE players SET avatar=? WHERE id=? AND (avatar IS NULL OR avatar='')", (avatar, row["id"]))
            assigned += cursor.rowcount
        conn.execute("INSERT INTO data_migrations(key) VALUES(?)", (migration_key,))
    return {"assigned": assigned}


def _seed_role_accounts(conn: sqlite3.Connection) -> None:
    """Create local demo identities once; passwords are stored as salted hashes."""
    demo_password = os.environ.get("RAPTOR_DEMO_PASSWORD", "Raptor@2026")
    identities = [
        ("admin", "admin@raptor.local", "Admin"),
        ("manager", "manager@raptor.local", "Manager"),
        ("coach", "coach@raptor.local", "Coach"),
        ("analyst", "analyst@raptor.local", "Analyst"),
        ("player", "player@raptor.local", "Player"),
    ]
    first_team = conn.execute("SELECT id FROM teams ORDER BY id LIMIT 1").fetchone()
    first_player = conn.execute("SELECT id,team_id FROM players ORDER BY id LIMIT 1").fetchone()
    for role, email, name in identities:
        if conn.execute("SELECT 1 FROM users WHERE lower(email)=lower(?)", (email,)).fetchone():
            continue
        salt, digest = hash_password(demo_password)
        player_id = first_player["id"] if role == "player" and first_player else None
        cur = conn.execute("INSERT INTO users(email,name,salt,password_hash,role,player_id) VALUES(?,?,?,?,?,?)", (email, name, salt, digest, role, player_id))
        if role in {"coach", "analyst"} and first_team:
            conn.execute("INSERT OR IGNORE INTO user_team_assignments(user_id,team_id) VALUES(?,?)", (cur.lastrowid, first_team["id"]))


def expand_sample_data() -> dict:
    """Expand the existing demo dataset to three times its current size once."""
    migration_key = "expanded_demo_dataset_v1"
    extra_teams = [
        ("Falcon (BGMI)", "BGMI", "A disciplined squad built for clutch finishes.", "amber"),
        ("Nova (Free Fire)", "Free Fire", "A fast-moving lineup with a fearless style.", "pink"),
        ("Titan (Valorant)", "Valorant", "A precision-first team ready for the stage.", "cyan"),
        ("Eclipse (BGMI)", "BGMI", "Smart rotations and steady team play.", "violet"),
        ("Reaper (Valorant)", "Valorant", "A tactical roster with an aggressive edge.", "pink"),
        ("Storm (Free Fire)", "Free Fire", "Quick decisions. Relentless pressure.", "cyan"),
        ("Apex (BGMI)", "BGMI", "Rising competitors with room to grow.", "amber"),
        ("Hydra (Valorant)", "Valorant", "A versatile roster that adapts each round.", "violet"),
    ]
    player_names = ["Raven", "Kairo", "Maverick", "Nix", "Onyx", "Viper", "Rogue", "Karma", "Frost", "Echo", "Drift", "Phoenix", "Orbit", "Jett"]
    roles = ["IGL", "Assaulter", "Support", "Sniper", "Flex"]
    tournament_names = ["Raptor Open #02", "Nightfall Showdown", "Raptor Rivals", "Phoenix Invitational", "Vortex Masters", "Raptor Cup #03", "Shadow Series", "Community Clash", "Raptor Open #04", "Final Zone Finals"]
    expense_rows = [
        ("Tournament entry fee", "Tournament", 1800, "Online"),
        ("Practice room booking", "Operations", 2400, "Team scrim block"),
        ("Headset replacement", "Equipment", 3200, "Player equipment"),
        ("Local event travel", "Travel", 5400, "Regional qualifier"),
        ("Streaming setup", "Equipment", 2600, "Community broadcast"),
        ("Team bootcamp", "Operations", 7500, "Weekend preparation"),
    ]
    with get_connection() as conn:
        if conn.execute("SELECT 1 FROM data_migrations WHERE key=?", (migration_key,)).fetchone():
            return {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in ("players", "teams", "expenses", "tournaments")}

        counts = {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in ("players", "teams", "expenses", "tournaments")}
        targets = {table: max(1, count * 3) for table, count in counts.items()}
        teams_needed = max(0, targets["teams"] - counts["teams"])
        for name, game, description, accent in extra_teams[:teams_needed]:
            conn.execute("INSERT INTO teams(name,game,players_count,status,description,accent) VALUES(?,?,0,'Active',?,?)", (name, game, description, accent))

        team_rows = [dict(row) for row in conn.execute("SELECT id,name,game FROM teams ORDER BY id")]
        player_count = counts["players"]
        players_needed = max(0, targets["players"] - player_count)
        today = date.today()
        for index in range(players_needed):
            team = team_rows[index % len(team_rows)]
            name = player_names[index % len(player_names)]
            ign = name.upper() if index % 2 == 0 else f"{name}{index + 7}"
            conn.execute("INSERT INTO players(name,ign,role,team_id,status,game,joined_at) VALUES(?,?,?,?,?,?,?)", (f"{name} {index + 1}", ign, roles[index % len(roles)], team["id"], "Active", team["game"], today.isoformat()))

        tournament_needed = max(0, targets["tournaments"] - counts["tournaments"])
        games = ["BGMI", "Free Fire", "Valorant"]
        for index in range(tournament_needed):
            conn.execute("INSERT INTO tournaments(name,game,date,prize_pool,status,location) VALUES(?,?,?,?,?,?)", (tournament_names[index % len(tournament_names)], games[index % len(games)], (today + timedelta(days=35 + index * 8)).isoformat(), [2500, 3500, 5000, 7000][index % 4], "Upcoming", "Online" if index % 2 == 0 else "India"))

        expense_needed = max(0, targets["expenses"] - counts["expenses"])
        for title, category, amount, notes in expense_rows[:expense_needed]:
            conn.execute("INSERT INTO expenses(title,category,amount,date,notes) VALUES(?,?,?,?,?)", (title, category, amount, today.isoformat(), notes))

        conn.execute("UPDATE teams SET players_count=(SELECT COUNT(*) FROM players WHERE players.team_id=teams.id)")
        conn.execute("INSERT INTO activity_events(message,kind) VALUES(?,?)", ("Sample organization data expanded", "organization"))
        conn.execute("INSERT INTO data_migrations(key) VALUES(?)", (migration_key,))
        return {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in ("players", "teams", "expenses", "tournaments")}


def _validate(table: str, values: dict) -> dict:
    if table not in TABLES:
        raise ValueError("Unknown section")
    clean = {k: v for k, v in values.items() if k in FIELDS[table]}
    missing = [k for k in REQUIRED[table] if k not in clean or clean[k] is None or str(clean[k]).strip() == ""]
    if missing:
        raise ValueError("Required fields: " + ", ".join(sorted(missing)))
    for key, value in clean.items():
        if isinstance(value, str) and len(value) > 240:
            raise ValueError(f"{key} must be 240 characters or fewer")
    enums = {"players": {"status": {"Active", "Inactive", "Trial"}}, "teams": {"status": {"Active", "Recruiting", "Inactive"}}, "tournaments": {"status": {"Upcoming", "Ongoing", "Completed"}}, "matches": {"status": {"Upcoming", "Live", "Completed"}}}
    for key, choices in enums.get(table, {}).items():
        if key in clean and clean[key] not in choices:
            raise ValueError(f"Choose a valid {key}")
    if table == "players" and "avatar" in clean:
        # Only shipped art is allowed; "" means "no art" and renders initials.
        # Guarded by `in clean` so updates that omit the field never wipe it.
        avatar = str(clean.get("avatar") or "").strip()
        if avatar and avatar not in AVATARS:
            raise ValueError("Choose one of the available player art options")
        clean["avatar"] = avatar
    if table == "expenses":
        try: clean["amount"] = round(float(clean["amount"]), 2)
        except (ValueError, TypeError): raise ValueError("Amount must be a number")
        if not 0 <= clean["amount"] <= 100_000_000: raise ValueError("Amount must be between 0 and 100,000,000")
    for key in ("prize_pool", "players_count", "team_id", "tournament_id", "player_id"):
        if key in clean and clean[key] not in (None, ""):
            try: clean[key] = int(clean[key]) if key in {"players_count", "team_id", "tournament_id", "player_id"} else round(float(clean[key]), 2)
            except (ValueError, TypeError): raise ValueError(f"{key.replace('_',' ').title()} must be a number")
    if table == "performance_records":
        try: clean["score"] = round(float(clean["score"]), 2)
        except (ValueError, TypeError): raise ValueError("Score must be a number")
        if not 0 <= clean["score"] <= 100: raise ValueError("Score must be between 0 and 100")
    if "date" in clean:
        try: date.fromisoformat(str(clean["date"]))
        except ValueError: raise ValueError("Date must use YYYY-MM-DD")
    return clean


def list_records(table: str, filters: dict | None = None) -> list[dict]:
    if table not in TABLES: raise ValueError("Unknown section")
    with get_connection() as db:
        if table == "players":
            rows = db.execute("SELECT p.*, t.name AS team_name FROM players p LEFT JOIN teams t ON t.id=p.team_id ORDER BY p.id")
        elif table == "matches":
            rows = db.execute("SELECT m.*, t.name AS tournament_name FROM matches m LEFT JOIN tournaments t ON t.id=m.tournament_id ORDER BY m.date,m.time")
        elif table == "performance_records":
            rows = db.execute("SELECT p.*, pl.name AS player_name, pl.ign, tm.name AS team_name FROM performance_records p JOIN players pl ON pl.id=p.player_id LEFT JOIN teams tm ON tm.id=p.team_id ORDER BY p.date DESC,p.id DESC")
        else:
            rows = db.execute(f"SELECT * FROM {table} ORDER BY id")
        result = [dict(r) for r in rows]
    if filters and "status" in filters: result = [r for r in result if r.get("status") == filters["status"]]
    if filters and filters.get("team_id") is not None: result = [r for r in result if r.get("team_id") == filters["team_id"]]
    if filters and filters.get("player_id") is not None: result = [r for r in result if r.get("player_id") == filters["player_id"]]
    return result


def save_record(table: str, record_id: int | None, values: dict) -> dict:
    clean = _validate(table, values)
    relations = {"players": ("team_id", "teams"), "matches": ("team_id", "teams"), "tournaments": ("team_id", "teams"), "performance_records": ("player_id", "players")}
    if table in relations:
        key, relation_table = relations[table]
        relation = clean.get(key)
        if relation not in (None, ""):
            with get_connection() as db:
                if not db.execute(f"SELECT 1 FROM {relation_table} WHERE id=?", (relation,)).fetchone(): raise ValueError(f"Choose an existing {relation_table[:-1]}")
    if table == "matches" and clean.get("tournament_id"):
        with get_connection() as db:
            if not db.execute("SELECT 1 FROM tournaments WHERE id=?", (clean["tournament_id"],)).fetchone(): raise ValueError("Choose an existing tournament")
    if table == "performance_records":
        with get_connection() as db:
            player = db.execute("SELECT team_id FROM players WHERE id=?", (clean["player_id"],)).fetchone()
        if not player: raise ValueError("Choose an existing player")
        player_team_id = player["team_id"]
        if clean.get("team_id") not in (None, "") and clean["team_id"] != player_team_id:
            raise ValueError("The performance record team must match the player's team")
        clean["team_id"] = player_team_id
        if player_team_id is not None:
            with get_connection() as db:
                if not db.execute("SELECT 1 FROM teams WHERE id=?", (player_team_id,)).fetchone(): raise ValueError("Choose an existing team")
    if table == "teams": clean["players_count"] = sum(1 for p in list_records("players") if p.get("team_id") and int(p["team_id"]) == (record_id or -1)) if record_id else 0
    with get_connection() as db:
        if record_id:
            if not db.execute(f"SELECT 1 FROM {table} WHERE id=?", (record_id,)).fetchone(): raise LookupError("Record not found")
            assignments = ",".join(f"{field}=?" for field in clean)
            if clean: db.execute(f"UPDATE {table} SET {assignments} WHERE id=?", (*clean.values(), record_id))
            saved_id = record_id
        else:
            cols = ",".join(clean)
            marks = ",".join("?" for _ in clean)
            cur = db.execute(f"INSERT INTO {table} ({cols}) VALUES ({marks})", tuple(clean.values()))
            saved_id = cur.lastrowid
        db.execute("INSERT INTO activity_events(message,kind) VALUES(?,?)", (f"{table[:-1].title()} {'updated' if record_id else 'added'}", table[:-1]))
        row = db.execute(f"SELECT * FROM {table} WHERE id=?", (saved_id,)).fetchone()
        if table == "players":
            db.execute("UPDATE teams SET players_count=(SELECT COUNT(*) FROM players WHERE players.team_id=teams.id)")
    return dict(row)


def delete_record(table: str, record_id: int) -> None:
    if table not in TABLES: raise ValueError("Unknown section")
    with get_connection() as db:
        cur = db.execute(f"DELETE FROM {table} WHERE id=?", (record_id,))
        if cur.rowcount == 0: raise LookupError("Record not found")
        db.execute("INSERT INTO activity_events(message,kind) VALUES(?,?)", (f"{table[:-1].title()} removed", table[:-1]))
        if table == "players": db.execute("UPDATE teams SET players_count=(SELECT COUNT(*) FROM players WHERE players.team_id=teams.id)")


def dashboard() -> dict:
    with get_connection() as db:
        counts = {"players": db.execute("SELECT COUNT(*) FROM players").fetchone()[0], "teams": db.execute("SELECT COUNT(*) FROM teams").fetchone()[0], "tournaments": db.execute("SELECT COUNT(*) FROM tournaments").fetchone()[0], "expenses": db.execute("SELECT COALESCE(SUM(amount),0) FROM expenses").fetchone()[0]}
        matches = [dict(r) for r in db.execute("SELECT * FROM matches WHERE date>=? ORDER BY date,time LIMIT 5", (date.today().isoformat(),))]
        activity = [dict(r) for r in db.execute("SELECT * FROM activity_events ORDER BY id DESC LIMIT 5")]
    return {"stats": counts, "matches": matches, "activity": activity}


def public_data() -> dict:
    with get_connection() as conn:
        stats = {
            "players": conn.execute("SELECT COUNT(*) FROM players").fetchone()[0],
            "teams": conn.execute("SELECT COUNT(*) FROM teams").fetchone()[0],
            "tournaments": conn.execute("SELECT COUNT(*) FROM tournaments").fetchone()[0],
        }
    teams = [t for t in list_records("teams") if t.get("status") != "Inactive"]
    tournaments = [t for t in list_records("tournaments") if t.get("status") in ("Upcoming", "Ongoing")][:3]
    return {"stats": stats, "teams": teams, "tournaments": tournaments}


def public_team_data(team_id: int) -> dict | None:
    with get_connection() as db:
        row = db.execute(
            "SELECT id,name,game,players_count,status,description,accent FROM teams WHERE id=? AND status!='Inactive'",
            (team_id,),
        ).fetchone()
        if not row:
            return None
        players = db.execute(
            "SELECT id,name,ign,role,status,game,avatar FROM players WHERE team_id=? ORDER BY id",
            (team_id,),
        )
        return {"team": dict(row), "players": [dict(player) for player in players]}


def recent_activity(limit: int = 5) -> list[dict]:
    limit = max(1, min(int(limit), 25))
    with get_connection() as db:
        rows = db.execute("SELECT message,kind,created_at FROM activity_events ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(row) for row in rows]


def all_expenses() -> list[dict]:
    with get_connection() as db:
        rows = db.execute("SELECT title,category,amount,date,notes FROM expenses ORDER BY date DESC,id DESC")
        return [dict(row) for row in rows]


def list_users() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT u.id,u.email,u.name,u.role,u.player_id,u.created_at,
                   p.id AS linked_player_id,p.name AS linked_player_name,p.ign AS linked_player_ign,
                   p.role AS linked_player_role,p.game AS linked_player_game,p.team_id AS linked_player_team_id,
                   p.status AS linked_player_status,t.name AS linked_player_team_name
            FROM users u
            LEFT JOIN players p ON p.id=u.player_id
            LEFT JOIN teams t ON t.id=p.team_id
            ORDER BY u.id
        """).fetchall()
        assignment_rows = conn.execute("""
            SELECT a.user_id,t.id,t.name,t.game
            FROM user_team_assignments a
            JOIN teams t ON t.id=a.team_id
            ORDER BY t.name
        """).fetchall()
    teams_by_user: dict[int, list[dict]] = {}
    for row in assignment_rows:
        teams_by_user.setdefault(row["user_id"], []).append({"id": row["id"], "name": row["name"], "game": row["game"]})
    users = []
    for row in rows:
        user = {key: row[key] for key in ("id", "email", "name", "role", "player_id", "created_at")}
        user["teams"] = teams_by_user.get(user["id"], [])
        if row["linked_player_id"] is None:
            user["player"] = None
        else:
            user["player"] = {
                "id": row["linked_player_id"],
                "name": row["linked_player_name"],
                "ign": row["linked_player_ign"],
                "role": row["linked_player_role"],
                "game": row["linked_player_game"],
                "team_id": row["linked_player_team_id"],
                "team_name": row["linked_player_team_name"],
                "status": row["linked_player_status"],
            }
        users.append(user)
    return users


def create_user(email: str, name: str, role: str, password: str, player_id=None) -> dict:
    if role not in rbac.ROLES:
        raise ValueError("Choose one of the five supported roles")
    if not email or len(email) > 200 or "@" not in email or not name.strip() or len(name) > 100:
        raise ValueError("Enter a valid email and name")
    if len(password) < 8 or len(password) > 256:
        raise ValueError("Password must be between 8 and 256 characters")
    if player_id not in (None, ""):
        if role != "player": raise ValueError("Only player accounts can link to a player record")
        try: player_id = int(player_id)
        except (ValueError, TypeError): raise ValueError("Choose an existing player")
        with get_connection() as conn:
            if not conn.execute("SELECT 1 FROM players WHERE id=?", (player_id,)).fetchone(): raise ValueError("Choose an existing player")
    salt, digest = hash_password(password)
    with get_connection() as conn:
        cur = conn.execute("INSERT INTO users(email,name,salt,password_hash,role,player_id) VALUES(?,?,?,?,?,?)", (email.strip().lower(), name.strip(), salt, digest, role, player_id))
        row = conn.execute("SELECT id,email,name,role,player_id,created_at FROM users WHERE id=?", (cur.lastrowid,)).fetchone()
        return dict(row)


def update_user_account(user_id: int, role: str, team_ids=None) -> None:
    if role not in rbac.ROLES:
        raise ValueError("Choose one of the five supported roles")
    selected = None
    if team_ids is not None:
        if not isinstance(team_ids, (list, tuple)):
            raise ValueError("Choose valid teams")
        selected = []
        for value in team_ids:
            try:
                team_id = int(value)
            except (TypeError, ValueError):
                raise ValueError("Choose valid teams") from None
            if team_id not in selected:
                selected.append(team_id)
        if selected and role not in {"coach", "analyst"}:
            raise ValueError("Team access is only valid for coach or analyst accounts")
    with get_connection() as conn:
        if not conn.execute("SELECT 1 FROM users WHERE id=?", (user_id,)).fetchone():
            raise LookupError("User not found")
        if selected:
            placeholders = ",".join("?" for _ in selected)
            existing = {row[0] for row in conn.execute(f"SELECT id FROM teams WHERE id IN ({placeholders})", selected)}
            if len(existing) != len(selected):
                raise ValueError("Choose existing teams")
        conn.execute("UPDATE users SET role=?, player_id=CASE WHEN ?='player' THEN player_id ELSE NULL END WHERE id=?", (role, role, user_id))
        if role not in {"coach", "analyst"}:
            conn.execute("DELETE FROM user_team_assignments WHERE user_id=?", (user_id,))
        elif selected is not None:
            conn.execute("DELETE FROM user_team_assignments WHERE user_id=?", (user_id,))
            for team_id in selected:
                conn.execute("INSERT OR IGNORE INTO user_team_assignments(user_id,team_id) VALUES(?,?)", (user_id, team_id))


def update_user_role(user_id: int, role: str) -> None:
    update_user_account(user_id, role)


def delete_user(user_id: int) -> None:
    with get_connection() as conn:
        if not conn.execute("DELETE FROM users WHERE id=?", (user_id,)).rowcount:
            raise LookupError("User not found")


def set_user_team_assignment(user_id: int, team_id: int, assigned: bool = True) -> None:
    with get_connection() as conn:
        user = conn.execute("SELECT role FROM users WHERE id=?", (user_id,)).fetchone()
        if not user: raise LookupError("User not found")
        if user["role"] not in {"coach", "analyst"}: raise ValueError("Only coaches and analysts can be assigned to teams")
        if not conn.execute("SELECT 1 FROM teams WHERE id=?", (team_id,)).fetchone(): raise LookupError("Team not found")
        if assigned:
            conn.execute("INSERT OR IGNORE INTO user_team_assignments(user_id,team_id) VALUES(?,?)", (user_id, team_id))
        else:
            conn.execute("DELETE FROM user_team_assignments WHERE user_id=? AND team_id=?", (user_id, team_id))


def list_assignments(role: str | None = None) -> list[dict]:
    with get_connection() as conn:
        query = "SELECT a.user_id,u.name AS user_name,u.email,u.role,a.team_id,t.name AS team_name FROM user_team_assignments a JOIN users u ON u.id=a.user_id JOIN teams t ON t.id=a.team_id"
        if role:
            query += " WHERE u.role=?"
            rows = conn.execute(query + " ORDER BY t.name,u.name", (role,))
        else:
            rows = conn.execute(query + " ORDER BY t.name,u.name")
        return [dict(row) for row in rows]


def list_assignable_staff(roles: tuple[str, ...] = ("coach", "analyst")) -> list[dict]:
    if not roles: return []
    if any(role not in {"coach", "analyst"} for role in roles): raise ValueError("Unsupported assignment role")
    with get_connection() as conn:
        placeholders = ",".join("?" for _ in roles)
        return [dict(row) for row in conn.execute(f"SELECT id,name,email,role FROM users WHERE role IN ({placeholders}) ORDER BY name", roles)]

