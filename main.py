import asyncio
from discord_bot import bot
import os
from match_handler import MatchHandler
from websocket_handler import WebSocketHandler

TOKEN = os.environ ["DISCORD_TOKEN"]
# WS_URL = "wss://socket.aoe2companion.com/listen?handler=ongoing-matches"
WS_URL = "ws://127.0.0.1:8765" # for testing

match_handler = MatchHandler ()
websocket_handler = WebSocketHandler (WS_URL, match_handler)

async def main():
    await asyncio.gather(
        websocket_handler.run(),
        bot.start(TOKEN),
    )

if __name__ == "__main__":
    asyncio.run(main())
