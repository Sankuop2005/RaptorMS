import contextlib
import unittest
import uuid

import db


class PlayerAvatarTests(unittest.TestCase):
    """Player avatar art: schema, one-time assignment, and validation."""

    def setUp(self):
        self.original = db.DB_PATH
        self.temp = db.ROOT / "work" / f"avatar-test-{uuid.uuid4().hex}.sqlite3"
        self.temp.parent.mkdir(parents=True, exist_ok=True)
        db.DB_PATH = self.temp

    def tearDown(self):
        db.DB_PATH = self.original
        with contextlib.suppress(OSError):
            self.temp.unlink()

    def test_avatar_column_exists_and_is_seeded_on_fresh_database(self):
        db.initialize()
        with db.get_connection() as conn:
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(players)")}
            self.assertIn("avatar", columns)
            avatars = [row["avatar"] for row in conn.execute("SELECT avatar FROM players")]
        self.assertTrue(avatars, "fresh database should seed players")
        for avatar in avatars:
            self.assertIn(avatar, db.AVATARS)

    def test_existing_database_gains_column_without_losing_players(self):
        db.initialize()
        with db.get_connection() as conn:
            before = conn.execute("SELECT COUNT(*) FROM players").fetchone()[0]
            conn.execute("ALTER TABLE players DROP COLUMN avatar")
        db.initialize()
        with db.get_connection() as conn:
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(players)")}
            after = conn.execute("SELECT COUNT(*) FROM players").fetchone()[0]
        self.assertIn("avatar", columns)
        self.assertEqual(before, after)

    def test_assignment_is_one_time_and_does_not_reshuffle(self):
        db.initialize()
        with db.get_connection() as conn:
            first = {row["id"]: row["avatar"] for row in conn.execute("SELECT id, avatar FROM players")}
        self.assertTrue(all(first.values()))
        # an admin clears one player's art, then initialize() runs again:
        # the migration guard must leave that choice alone.
        cleared_id = next(iter(first))
        with db.get_connection() as conn:
            conn.execute("UPDATE players SET avatar='' WHERE id=?", (cleared_id,))
        db.assign_player_avatars()
        with db.get_connection() as conn:
            second = {row["id"]: row["avatar"] for row in conn.execute("SELECT id, avatar FROM players")}
        for player_id, avatar in first.items():
            expected = "" if player_id == cleared_id else avatar
            self.assertEqual(second[player_id], expected, f"player {player_id} was reshuffled")

    def test_assignment_runs_only_once_for_the_whole_roster(self):
        db.initialize()
        db.assign_player_avatars()
        with db.get_connection() as conn:
            rows = conn.execute("SELECT COUNT(*) FROM players WHERE avatar IS NULL OR avatar=''").fetchone()[0]
        self.assertEqual(rows, 0)

    def test_all_shipped_art_appears_across_the_roster(self):
        db.initialize()
        with db.get_connection() as conn:
            used = {row["avatar"] for row in conn.execute("SELECT avatar FROM players")}
        self.assertEqual(used, set(db.AVATARS))

    def _values(self, player, **overrides):
        """A complete players record — save_record validates required fields on
        every write, and the real dialog always submits the whole form."""
        values = {key: player.get(key) for key in ("name", "ign", "role", "team_id", "status", "game", "joined_at", "avatar")}
        values.update(overrides)
        return values

    def test_avatar_field_is_accepted_by_save_record(self):
        db.initialize()
        player = db.list_records("players")[0]
        saved = db.save_record("players", player["id"], self._values(player, avatar="04-oni.png"))
        self.assertEqual(saved["avatar"], "04-oni.png")

    def test_unknown_art_is_rejected(self):
        db.initialize()
        player = db.list_records("players")[0]
        for bad in ("../../../etc/passwd", "09-hexmonogram.png", "01-hood.png.jpg"):
            with self.assertRaises(ValueError):
                db.save_record("players", player["id"], self._values(player, avatar=bad))

    def test_update_without_avatar_field_does_not_clear_existing_art(self):
        db.initialize()
        player = db.list_records("players")[0]
        db.save_record("players", player["id"], self._values(player, avatar="06-skull.png"))
        values = self._values(player)
        del values["avatar"]
        db.save_record("players", player["id"], values)
        refreshed = next(p for p in db.list_records("players") if p["id"] == player["id"])
        self.assertEqual(refreshed["avatar"], "06-skull.png")
        self.assertEqual(refreshed["role"], player["role"])

    def test_role_edit_keeps_existing_art(self):
        db.initialize()
        player = db.list_records("players")[0]
        db.save_record("players", player["id"], self._values(player, avatar="06-skull.png"))
        # the dialog re-renders from the saved record, so it re-submits the
        # current art alongside the edited role
        current = next(p for p in db.list_records("players") if p["id"] == player["id"])
        saved = db.save_record("players", player["id"], self._values(current, role="Support"))
        self.assertEqual(saved["avatar"], "06-skull.png")
        self.assertEqual(saved["role"], "Support")

    def test_empty_avatar_clears_art_and_is_allowed(self):
        db.initialize()
        player = db.list_records("players")[0]
        db.save_record("players", player["id"], self._values(player, avatar="06-skull.png"))
        saved = db.save_record("players", player["id"], self._values(player, avatar=""))
        self.assertEqual(saved["avatar"], "")


if __name__ == "__main__":
    unittest.main()
