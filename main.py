import asyncio
from discord_bot import bot
import os
from match_handler import MatchHandler
from websocket_handler import WebSocketHandler

BOT_TOKEN = os.environ ["DISCORD_TOKEN"]
WS_SPECTATE_URL = os.environ.get ("WS_SPECTATE_URL", "ws://127.0.0.1:8765")

match_handler = MatchHandler ()
websocket_handler = WebSocketHandler (WS_SPECTATE_URL, match_handler)

async def main():
    await asyncio.gather(
        websocket_handler.run(),
        bot.start(BOT_TOKEN),
    )

if __name__ == "__main__":
    asyncio.run(main())
