from discord_bot import bot
import os

TOKEN = os.environ ["DISCORD_TOKEN"]

bot.run(TOKEN)
