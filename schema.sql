CREATE TABLE members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_id INTEGER NOT NULL,
    aoe2_profile_id INTEGER NOT NULL UNIQUE,
    added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS settings (
    guild_id INTEGER PRIMARY KEY,
    spectate_channel_id INTEGER,
    lobby_channel_id INTEGER
);
