import sqlite3
from pathlib import Path

class DatabaseHandler:
    def __init__(self, db_path=""):
        self.db_path = Path(db_path)
        self.members = {}

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

            self.members.setdefault(discord_id, []).append(aoe2_profile_id)
            return True

        except sqlite3.IntegrityError:
            return False

    def read_all_members_in_db(self):
        with sqlite3.connect(self.db_path) as db:
            rows = db.execute("""
                SELECT discord_id, aoe2_profile_id
                FROM members
                ORDER BY discord_id
            """).fetchall()

        members = {}

        for discord_id, profile_id in rows:
            members.setdefault(discord_id, []).append(profile_id)

        self.members = members

    def remove_member(self, discord_id, aoe2_profile_id):
        with sqlite3.connect(self.db_path) as db:
            cursor = db.execute(
                """
                DELETE FROM members
                WHERE discord_id = ? AND aoe2_profile_id = ?
                """,
                (discord_id, aoe2_profile_id),
            )

        if cursor.rowcount > 0:
            profiles = self.members.get(discord_id)

            if profiles:
                profiles.remove(aoe2_profile_id)

                if not profiles:
                    del self.members[discord_id]

            return True

        return False

    def is_member(self, profile_id):
        return any(
            profile_id in profiles
            for profiles in self.members.values()
        )

    def set_spectate_channel(self, guild_id, channel_id):
        with sqlite3.connect(self.db_path) as db:
            db.execute("""
                INSERT INTO settings (guild_id, spectate_channel_id)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    spectate_channel_id = excluded.spectate_channel_id
            """, (guild_id, channel_id))

    def set_lobby_channel(self, guild_id, channel_id):
        with sqlite3.connect(self.db_path) as db:
            db.execute("""
                INSERT INTO settings (guild_id, lobby_channel_id)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    lobby_channel_id = excluded.lobby_channel_id
            """, (guild_id, channel_id))

    def get_channel_ids(self):
        with sqlite3.connect(self.db_path) as db:
            row = db.execute("""
                SELECT guild_id, spectate_channel_id, lobby_channel_id
                FROM settings
            """).fetchone()

        if row is None:
            return None

        return {
            "guild_id": row[0],
            "spectate_channel_id": row[1],
            "lobby_channel_id": row[2],
        }

db = DatabaseHandler("data/bot.db")
db.check_integrity()
db.read_all_members_in_db()
