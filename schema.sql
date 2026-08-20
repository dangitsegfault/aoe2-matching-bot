CREATE TABLE IF NOT EXISTS guilds (
    guild_id INTEGER PRIMARY KEY,
    spectate_channel_id INTEGER,
    lobby_channel_id INTEGER
);

CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_id INTEGER NOT NULL,
    aoe2_profile_id INTEGER NOT NULL,
    guild_id INTEGER NOT NULL,
    added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id),
    UNIQUE (aoe2_profile_id, guild_id)
);
