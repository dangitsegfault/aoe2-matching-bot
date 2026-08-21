import sqlite3
from pathlib import Path
import os

DB_FILE_PATH="/app/data/bot.db"
os.makedirs(os.path.dirname(DB_FILE_PATH), exist_ok=True)

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

    def add_member(self, guild_id, discord_id, aoe2_profile_id):
        try:
            with sqlite3.connect(self.db_path) as db:
                db.execute(
                    """
                    INSERT INTO members (guild_id, discord_id, aoe2_profile_id)
                    VALUES (?, ?, ?)
                    """,
                    (guild_id, discord_id, aoe2_profile_id),
                )

            return True

        except sqlite3.IntegrityError:
            return False

    def read_all_members_by_guild(self, guild_id):
        with sqlite3.connect(self.db_path) as db:
            rows = db.execute("""
                SELECT discord_id, aoe2_profile_id
                FROM members
                WHERE guild_id = ?
                ORDER BY discord_id
            """, (guild_id,)).fetchall()

        members = {}

        for discord_id, profile_id in rows:
            members.setdefault(discord_id, []).append(profile_id)

        return members

    def remove_member(self, guild_id, discord_id, aoe2_profile_id):
        with sqlite3.connect(self.db_path) as db:
            cursor = db.execute(
                """
                DELETE FROM members
                WHERE guild_id = ? AND discord_id = ? AND aoe2_profile_id = ?
                """,
                (guild_id, discord_id, aoe2_profile_id),
            )

        if cursor.rowcount > 0:
            return True

        return False

    def is_member_of_guild(self, guild_id, profile_id):
        with sqlite3.connect(self.db_path) as db:
            row = db.execute(
                """
                SELECT 1
                FROM members
                WHERE guild_id = ? AND aoe2_profile_id = ?
                LIMIT 1
                """,
                (guild_id, profile_id),
            ).fetchone()

        return row is not None

    def is_profile_registered(self, profile_id):
        with sqlite3.connect(self.db_path) as db:
            row = db.execute(
                """
                SELECT 1
                FROM members
                WHERE aoe2_profile_id = ?
                LIMIT 1
                """,
                (profile_id,),
            ).fetchone()

        return row is not None

    def set_spectate_channel(self, guild_id, channel_id):
        with sqlite3.connect(self.db_path) as db:
            db.execute("""
                INSERT INTO guilds (guild_id, spectate_channel_id)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    spectate_channel_id = excluded.spectate_channel_id
            """, (guild_id, channel_id))

    def set_lobby_channel(self, guild_id, channel_id):
        with sqlite3.connect(self.db_path) as db:
            db.execute("""
                INSERT INTO guilds (guild_id, lobby_channel_id)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    lobby_channel_id = excluded.lobby_channel_id
            """, (guild_id, channel_id))

    def get_channel_ids(self, guild_id):
        with sqlite3.connect(self.db_path) as db:
            row = db.execute("""
                SELECT spectate_channel_id, lobby_channel_id
                FROM guilds
                WHERE guild_id = ?
            """, (guild_id,)).fetchone()

        if row is None:
            return None

        return {
            "spectate_channel_id": row[0],
            "lobby_channel_id": row[1],
        }

    def get_guilds_by_profile_id (self, profile_id):
        with sqlite3.connect(self.db_path) as db:
            rows = db.execute("""
                SELECT guild_id
                FROM members
                WHERE aoe2_profile_id = ?
            """, (profile_id,)).fetchall()

        return [row[0] for row in rows]
        

db = DatabaseHandler(DB_FILE_PATH)
db.check_integrity()
