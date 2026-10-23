import contextlib
import unittest
import uuid
from pathlib import Path

import db


class RBACDatabaseMigrationTests(unittest.TestCase):
    def setUp(self):
        self.original = db.DB_PATH
        self.temp = db.ROOT / "work" / f"rbac-test-{uuid.uuid4().hex}.sqlite3"
        self.temp.parent.mkdir(parents=True, exist_ok=True)
        db.DB_PATH = self.temp

    def tearDown(self):
        db.DB_PATH = self.original
        with contextlib.suppress(OSError):
            self.temp.unlink()

    def test_initialize_adds_role_scope_and_performance_tables_without_losing_seeded_data(self):
        db.initialize()
        with db.get_connection() as conn:
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)")}
            self.assertIn("role", columns)
            self.assertIn("player_id", columns)
            tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertIn("performance_records", tables)
            self.assertIn("user_team_assignments", tables)
            roles = {row["role"] for row in conn.execute("SELECT role FROM users")}
            self.assertEqual(roles, {"admin", "manager", "coach", "analyst", "player"})
            self.assertGreater(conn.execute("SELECT COUNT(*) FROM teams").fetchone()[0], 0)
        conn.close()
        self.assertNotIn("expenses", db.public_data()["stats"])

    def test_performance_record_cannot_pair_a_player_with_another_team(self):
        db.initialize()
        teams = db.list_records("teams")
        players = db.list_records("players")
        other_team_player = next(player for player in players if player["team_id"] != teams[0]["id"])
        with self.assertRaises(ValueError):
            db.save_record("performance_records", None, {
                "player_id": other_team_player["id"], "team_id": teams[0]["id"],
                "category": "Accuracy", "score": 80, "date": "2026-10-22",
            })

    def test_legacy_database_migration_keeps_records_and_upgrades_the_existing_admin(self):
        with db.get_connection() as conn:
            salt, digest = db.hash_password("old-local-password")
            conn.executescript("""
                CREATE TABLE users(id INTEGER PRIMARY KEY,email TEXT UNIQUE NOT NULL,name TEXT NOT NULL,salt BLOB NOT NULL,password_hash BLOB NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
                CREATE TABLE teams(id INTEGER PRIMARY KEY,name TEXT NOT NULL,game TEXT NOT NULL,players_count INTEGER NOT NULL DEFAULT 0,status TEXT NOT NULL DEFAULT 'Active',description TEXT NOT NULL DEFAULT '',accent TEXT NOT NULL DEFAULT 'violet',created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
                CREATE TABLE players(id INTEGER PRIMARY KEY,name TEXT NOT NULL,ign TEXT NOT NULL,role TEXT NOT NULL,team_id INTEGER,status TEXT NOT NULL DEFAULT 'Active',game TEXT NOT NULL DEFAULT '',joined_at TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
                CREATE TABLE tournaments(id INTEGER PRIMARY KEY,name TEXT NOT NULL,game TEXT NOT NULL,date TEXT NOT NULL,prize_pool REAL NOT NULL DEFAULT 0,status TEXT NOT NULL DEFAULT 'Upcoming',location TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
                CREATE TABLE matches(id INTEGER PRIMARY KEY,name TEXT NOT NULL,game TEXT NOT NULL,date TEXT NOT NULL,time TEXT NOT NULL DEFAULT '08:00 PM',opponent TEXT NOT NULL DEFAULT '',tournament_id INTEGER,status TEXT NOT NULL DEFAULT 'Upcoming',result TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
                CREATE TABLE expenses(id INTEGER PRIMARY KEY,title TEXT NOT NULL,category TEXT NOT NULL,amount REAL NOT NULL,date TEXT NOT NULL,notes TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            """)
            conn.execute("INSERT INTO users(id,email,name,salt,password_hash) VALUES(1,?,?,?,?)", ("admin@raptor.local", "Admin", salt, digest))
            conn.execute("INSERT INTO teams(id,name,game) VALUES(1,'Legacy Squad','BGMI')")
            conn.execute("INSERT INTO players(id,name,ign,role,team_id,game) VALUES(1,'Legacy Player','LP','Support',1,'BGMI')")
            conn.execute("INSERT INTO matches(id,name,game,date) VALUES(1,'Legacy Match','BGMI','2026-10-25')")
            conn.execute("INSERT INTO expenses(id,title,category,amount,date) VALUES(1,'Legacy Cost','Travel',250,'2026-10-22')")
        db.initialize()
        with db.get_connection() as conn:
            self.assertEqual(conn.execute("SELECT name FROM teams WHERE id=1").fetchone()[0], "Legacy Squad")
            self.assertEqual(conn.execute("SELECT title FROM expenses WHERE id=1").fetchone()[0], "Legacy Cost")
            self.assertEqual(conn.execute("SELECT role FROM users WHERE email='admin@raptor.local'").fetchone()[0], "admin")
            self.assertIsNotNone(conn.execute("SELECT role FROM users WHERE email='coach@raptor.local'").fetchone())


if __name__ == "__main__":
    unittest.main()
