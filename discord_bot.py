import discord
from discord import app_commands
from database_handler import db
import os
import io

REDIRECT_URL = os.environ ["REDIRECT_URL"]
DEV_GUILD_ID = os.environ.get("DEV_GUILD_ID")

class DiscordBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)

        self.tree = app_commands.CommandTree(self)
        self.spectate_channel = None
        self.lobby_channel = None

    async def setup_hook(self):
        if DEV_GUILD_ID:
            guild = discord.Object(id=DEV_GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            commands = await self.tree.sync(guild=guild)
            print(f"Synced commands to dev guild {DEV_GUILD_ID}:")
        else:
            commands = await self.tree.sync()
            print("Synced commands globally:")

        for command in commands:
            print(f"  /{command.name}")

    async def on_ready(self):
        print(f"Logged in as {self.user}")

    def make_match_view(self, match_id):
        view = discord.ui.View()

        view.add_item(
            discord.ui.Button(
                label="Spectate",
                url=f"{REDIRECT_URL}/spectate/{match_id}",
            )
        )

        return view

    async def send_match_message(self, content, image, match_id, guild_id):
        print(f"send_match_message called for match {match_id}, guild {guild_id}")

        settings = db.get_channel_ids(guild_id)
        if settings is None:
            print(f"  no channel settings for guild {guild_id}")
            return None

        channel_id = settings["spectate_channel_id"]
        if channel_id is None:
            print(f"  spectate_channel_id not set for guild {guild_id}")
            return None

        channel = self.get_channel(channel_id)
        if channel is None:
            channel = await self.fetch_channel(channel_id)
        print(f"  resolved channel: {channel}")

        filename = f"match_{match_id}.png"
        file = discord.File(io.BytesIO(image.getvalue()), filename=filename)

        try:
            message = await channel.send(
                content=content,
                file=file,
                view=self.make_match_view(match_id),
            )
            print(f"  sent message {message.id}")
        except discord.HTTPException as e:
            print(f"  Failed to send match message: {e}")
            return None

        return message.id

    async def update_match_message(self, message_id, guild_id, content, image, match_id):
        print(f"update_match_message called for match {match_id}, guild {guild_id}")

        settings = db.get_channel_ids(guild_id)
        if settings is None:
            print(f"  no channel settings for guild {guild_id}")
            return None

        channel_id = settings["spectate_channel_id"]
        if channel_id is None:
            print(f"  spectate_channel_id not set for guild {guild_id}")
            return None

        channel = self.get_channel(channel_id)
        if channel is None:
            channel = await self.fetch_channel(channel_id)
        print(f"  resolved channel: {channel}")

        message = await channel.fetch_message(message_id)

        filename = f"match_{match_id}.png"
        file = discord.File(
            io.BytesIO(image.getvalue()),
            filename=filename,
        )
        try:
            message = await message.edit(
                content=content,
                attachments=[file],
                view=None,
            )
            print(f"  sent updated {message.id}")
        except discord.HTTPException as e:
            print(f"  Failed to update match message: {e}")
            return False

        return True


    
bot = DiscordBot()

@bot.tree.command(
    name="register",
    description="Register your AoE2 profile"
)

@app_commands.describe(profile_id="Your AoE2 Companion profile ID")
async def register(
        interaction: discord.Interaction,
        profile_id: int,
):
    success = db.add_member(
        interaction.guild_id,
        interaction.user.id,
        profile_id
    )

    if success:
        await interaction.response.send_message(
            f"Registered AoE2 profile `{profile_id}`.",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "You are already registered, or that AoE2 profile is already registered.",
            ephemeral=True
        )

@bot.tree.command(
    name="members",
    description="Show registered AoE2 accounts"
)
@app_commands.checks.has_permissions(administrator=True)
async def members(interaction: discord.Interaction):
    members = db.read_all_members_by_guild (interaction.guild.id)

    if not members:
        await interaction.response.send_message(
            "No members are registered.",
            ephemeral=True
        )
        return

    lines = ["**Registered AoE2 accounts:**"]

    for discord_id, profile_ids in members.items():
        try:
            user = await interaction.guild.fetch_member(discord_id)
            name = user.mention
        except discord.NotFound:
            name = f"`{discord_id}`"

        lines.append(f"\n{name}")

        for profile_id in profile_ids:
            lines.append(f"  └─ `{profile_id}`")

    await interaction.response.send_message("\n".join(lines),
                                            ephemeral=True
                                            )

@bot.tree.command(
    name="unregister",
    description="Unregister an AoE2 profile"
)
@app_commands.describe(profile_id="Your AoE2 Companion profile ID")
async def unregister(
        interaction: discord.Interaction,
        profile_id: int,
):
    success = db.remove_member(
        interaction.guild.id,
        interaction.user.id,
        profile_id,
    )

    if success:
        await interaction.response.send_message(
            f"Unregistered AoE2 profile `{profile_id}`.",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"Your AoE2 profile `{profile_id}` is not registered.",
            ephemeral=True
        )

@bot.tree.command(
    name="privileged_register",
    description="Register an AoE2 profile for another member"
)
@app_commands.describe(
    user="Discord member to register",
    profile_id="AoE2 Companion profile ID"
)
@app_commands.checks.has_permissions(administrator=True)
async def privileged_register(
        interaction: discord.Interaction,
        user: discord.Member,
        profile_id: int,
):
    success = db.add_member(
        interaction.guild.id,
        user.id,
        profile_id,
    )

    if success:
        await interaction.response.send_message(
            f"Registered AoE2 profile `{profile_id}` for {user.mention}.",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "That AoE2 profile is already registered.",
            ephemeral=True
        )

@bot.tree.command(
    name="privileged_unregister",
    description="Unregister an AoE2 profile for another member"
)
@app_commands.describe(
    user="Discord member to unregister",
    profile_id="AoE2 Companion profile ID"
)
@app_commands.checks.has_permissions(administrator=True)
async def privileged_unregister(
        interaction: discord.Interaction,
        user: discord.Member,
        profile_id: int,
):
    success = db.remove_member(
        interaction.guild.id,
        user.id,
        profile_id,
    )

    if success:
        await interaction.response.send_message(
            f"Unregistered AoE2 profile `{profile_id}` from {user.mention}.",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "That AoE2 profile is not registered to that member.",
            ephemeral=True
        )

@bot.tree.command(
    name="set_spectate_channel",
    description="Set this channel for spectate messages"
)
@app_commands.checks.has_permissions(administrator=True)
async def set_spectate_channel(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    channel_id = interaction.channel.id

    db.set_spectate_channel(guild_id, channel_id)

    bot.spectate_channel = interaction.channel

    await interaction.response.send_message(
        f"Spectate channel set to {interaction.channel.mention}.",
        ephemeral=True
    )

@bot.tree.command(
    name="set_lobby_channel",
    description="Set this channel for lobby messages"
)
@app_commands.checks.has_permissions(administrator=True)
async def set_lobby_channel(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    channel_id = interaction.channel.id

    db.set_lobby_channel(guild_id, channel_id)

    bot.lobby_channel = interaction.channel

    await interaction.response.send_message(
        f"Lobby channel set to {interaction.channel.mention}.",
        ephemeral=True
    )
