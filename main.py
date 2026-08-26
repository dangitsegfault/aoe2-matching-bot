import asyncio
from discord_bot import bot
import os
from match_handler import MatchHandler
from websocket_handler import WebSocketHandler

BOT_TOKEN = os.environ ["DISCORD_TOKEN"]
WS_MATCH_STARTED_URL = "wss://socket.aoe2companion.com/listen?handler=ongoing-matches"
WS_MATCH_FINISHED_URL = "wss://socket.aoe2companion.com/listen?handler=match-finished"

match_started_handler = MatchHandler ()
match_started_websocket_handler = WebSocketHandler (
    WS_MATCH_STARTED_URL,
    match_started_handler.parse_matches_started)

async def main():
    await asyncio.gather(
        match_started_websocket_handler.run(),
        bot.start(BOT_TOKEN),
    )

if __name__ == "__main__":
    asyncio.run(main())
