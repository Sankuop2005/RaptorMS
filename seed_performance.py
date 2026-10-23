"""Seed realistic demo performance records for the current roster.

The seed is idempotent: it writes a migration marker and skips if performance
records already exist. Run with:

    python seed_performance.py
"""
from __future__ import annotations

from datetime import date, timedelta

import db


SEED_KEY = "performance_seed_v1"

BASE_SCORES = {
    "Sanku": 84,
    "Shisui": 88,
    "Naruto": 79,
    "Dazzler": 86,
    "Zero": 81,
    "Priyanshu": 82,
    "Manav Shinde ": 87,
    "Ayush Jangir": 85,
    "Sahil Dahiya ": 80,
    "Dhruv Sharma": 78,
    "Derke": 90,
    "Chronicle": 86,
    "Jamppi": 83,
    "PROFEK": 81,
    "Sayonara": 84,
}

CATEGORY_SETS = {
    "BGMI": [
        ("Firepower", 3, "BGMI scrim block: strong entry damage and 18 eliminations across four maps."),
        ("Survival", -2, "Final-zone discipline: 82% survival rate across the scrim block."),
        ("Clutch", 1, "Late-circle retakes: four clutch fights won under pressure."),
    ],
    "Free Fire": [
        ("Rushing", 2, "Clash squad block: fast entries and 12 finishes across the session."),
        ("Support", -3, "Utility and cover play: consistent trades in the Free Fire scrims."),
        ("Consistency", 1, "Six-match practice block: steady output with minimal early exits."),
    ],
    "Valorant": [
        ("Aim", 4, "Valorant scrim: 28% headshot rate across two maps."),
        ("Utility", -2, "Recon and smoke execution: clean retakes with minimal wasted utility."),
        ("Clutch", 2, "Late-round block: three 1v1 clutches converted."),
    ],
}

DATE_OFFSETS = (1, 0, -1)


def seed() -> dict:
    today = date.today()
    dates = [
        (today - timedelta(days=1)).isoformat(),
        (today - timedelta(days=8)).isoformat(),
        (today - timedelta(days=15)).isoformat(),
    ]

    with db.get_connection() as conn:
        if conn.execute("SELECT 1 FROM data_migrations WHERE key=?", (SEED_KEY,)).fetchone():
            return {"status": "skipped", "reason": "marker already present"}

        existing = conn.execute("SELECT COUNT(*) FROM performance_records").fetchone()[0]
        if existing:
            return {"status": "skipped", "reason": f"{existing} performance records already exist"}

        players = [dict(row) for row in conn.execute("SELECT id,name,team_id,game FROM players ORDER BY id")]
        rows = []
        for player in players:
            team_id = player.get("team_id")
            if not team_id:
                continue
            game = player.get("game") or "Other"
            categories = CATEGORY_SETS.get(game, [("Overall", 0, "Practice block performance.")])
            base = BASE_SCORES.get(player["name"], 80)
            for index, (category, modifier, notes) in enumerate(categories):
                score = max(0, min(100, base + modifier + DATE_OFFSETS[index]))
                rows.append((player["id"], team_id, category, score, dates[index], notes))

        conn.executemany(
            "INSERT INTO performance_records(player_id,team_id,category,score,date,notes) VALUES(?,?,?,?,?,?)",
            rows,
        )
        conn.execute(
            "INSERT INTO activity_events(message,kind) VALUES(?,?)",
            (f"Performance data seeded for {len(players)} players", "performance"),
        )
        conn.execute("INSERT INTO data_migrations(key) VALUES(?)", (SEED_KEY,))

        by_team = {
            row["name"]: row["records"]
            for row in conn.execute(
                """SELECT t.name, COUNT(*) AS records
                   FROM performance_records p JOIN teams t ON t.id = p.team_id
                   GROUP BY t.id ORDER BY t.id"""
            )
        }

    return {
        "status": "seeded",
        "records": len(rows),
        "players": len(players),
        "date_range": f"{dates[-1]} to {dates[0]}",
        "by_team": by_team,
    }


if __name__ == "__main__":
    result = seed()
    print(result)
