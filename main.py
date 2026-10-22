import asyncio
from discord_bot import bot
import os
from match_handler import MatchHandler
from lobby_handler import lobby_handler
from websocket_handler import WebSocketHandler

BOT_TOKEN = os.environ ["DISCORD_TOKEN"]
WS_MATCH_STARTED_URL = "ws://host.containers.internal:8765" if os.getenv ("TESTING") else "wss://socket.aoe2companion.com/listen?handler=match-started"
WS_MATCH_FINISHED_URL = "ws://host.containers.internal:8766" if os.getenv ("TESTING") else "wss://socket.aoe2companion.com/listen?handler=match-finished"
WS_LOBBIES_URL = "ws://host.containers.internal:8767" if os.getenv ("TESTING") else "wss://socket.aoe2companion.com/listen?handler=lobbies"

match_handler = MatchHandler ()
match_started_websocket_handler = WebSocketHandler (
    WS_MATCH_STARTED_URL,
    match_handler.parse_matches_started)
match_finished_websocket_handler = WebSocketHandler (
    WS_MATCH_FINISHED_URL,
    match_handler.parse_matches_finished)
lobbies_websocket_handler = WebSocketHandler (
    WS_LOBBIES_URL,
    lobby_handler.parse_lobbies)


async def main():
    await asyncio.gather(
        match_started_websocket_handler.run(),
        match_finished_websocket_handler.run(),
        lobbies_websocket_handler.run(),
        # lobby_handler.print_interested_lobbies(),
        bot.start(BOT_TOKEN),
    )

if __name__ == "__main__":
    asyncio.run(main())
