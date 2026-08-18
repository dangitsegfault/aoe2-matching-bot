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

    # async def setup_hook(self):
    #     commands = await self.tree.sync()

    #     print("Synced commands:")
    #     for command in commands:
    #         print(f"  /{command.name}")

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
