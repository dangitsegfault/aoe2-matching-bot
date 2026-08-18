import discord
from discord import app_commands
from database import DatabaseHandler
import os

GUILD_ID = os.environ ["GUILD_ID"]

db = DatabaseHandler("data/bot.db")
db.check_integrity()

class DiscordBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)

        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)

        self.tree.copy_global_to(guild=guild)
        commands = await self.tree.sync(guild=guild)

        print("Synced commands:")
        for command in commands:
            print(f"  /{command.name}")

    async def on_ready(self):
        print(f"Logged in as {self.user}")

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
        interaction.user.id,
        profile_id,
    )

    if success:
        await interaction.response.send_message(
            f"Registered AoE2 profile `{profile_id}`."
        )
    else:
        await interaction.response.send_message(
            "You are already registered, or that AoE2 profile is already registered."
        )

@bot.tree.command(
    name="members",
    description="Show registered AoE2 accounts"
)
@app_commands.checks.has_permissions(administrator=True)
async def members(interaction: discord.Interaction):
    members = db.get_all_members()

    if not members:
        await interaction.response.send_message(
            "No members are registered."
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

    await interaction.response.send_message("\n".join(lines))

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
        interaction.user.id,
        profile_id,
    )

    if success:
        await interaction.response.send_message(
            f"Unregistered AoE2 profile `{profile_id}`."
        )
    else:
        await interaction.response.send_message(
            f"Your AoE2 profile `{profile_id}` is not registered."
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
        user.id,
        profile_id,
    )

    if success:
        await interaction.response.send_message(
            f"Registered AoE2 profile `{profile_id}` for {user.mention}."
        )
    else:
        await interaction.response.send_message(
            "That AoE2 profile is already registered."
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
        user.id,
        profile_id,
    )

    if success:
        await interaction.response.send_message(
            f"Unregistered AoE2 profile `{profile_id}` from {user.mention}."
        )
    else:
        await interaction.response.send_message(
            "That AoE2 profile is not registered to that member."
        )
