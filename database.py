# CREATE TABLE members (
#     discord_id INTEGER PRIMARY KEY,
#     aoe2_profile_id INTEGER NOT NULL UNIQUE,
#     added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
# );

import sqlite3
from pathlib import Path

class DatabaseHandler:
    def __init__(self, db_path=""):
        self.db_path = Path(db_path)

    def check_integrity(self):
        if not self.db_path.exists():
            self.create_new ()

        try:
            with sqlite3.connect(self.db_path) as db:
                result = db.execute(
                    "PRAGMA integrity_check;"
                ).fetchone()[0]

                return result == "ok"

        except sqlite3.DatabaseError:
            return False        

    def create_new(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        schema_path = Path(__file__).parent / "schema.sql"
        schema = schema_path.read_text()

        with sqlite3.connect(self.db_path) as db:
            db.executescript(schema)

    def add_member(self, discord_id, aoe2_profile_id):
        try:
            with sqlite3.connect(self.db_path) as db:
                db.execute(
                    """
                    INSERT INTO members (discord_id, aoe2_profile_id)
                    VALUES (?, ?)
                    """,
                    (discord_id, aoe2_profile_id),
                )

            return True

        except sqlite3.IntegrityError:
            return False

    def remove_member():
        return

    def get_member():
        return

    def get_all_members(self):
        with sqlite3.connect(self.db_path) as db:
            rows = db.execute("""
                SELECT discord_id, aoe2_profile_id
                FROM members
                ORDER BY discord_id
            """).fetchall()

        members = {}

        for discord_id, profile_id in rows:
            members.setdefault(discord_id, []).append(profile_id)

        return members

    def update_member():
        return
