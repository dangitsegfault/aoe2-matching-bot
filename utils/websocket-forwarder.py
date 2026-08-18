# scriipt  to keep constant connection to the aoe2companion websocket and i can connect my code to a local websocket for development so that i do no abuse the aoe2companions socket by restarting my scripts

import asyncio
import websockets

AOE2_COMPANION_URL = "wss://socket.aoe2companion.com/listen?handler=ongoing-matches"
LOCAL_HOST = "127.0.0.1"
LOCAL_PORT = 8765

clients = set()
latest_message = None


async def broadcast(message):
    if not clients:
        return

    await asyncio.gather(
        *(client.send(message) for client in clients),
        return_exceptions=True,
    )


async def aoe2_connection():
    global latest_message

    while True:
        try:
            async with websockets.connect(
                AOE2_COMPANION_URL,
                max_size=None,
            ) as websocket:
                print("Connected to AoE2 Companion.")

                async for message in websocket:
                    latest_message = message
                    await broadcast(message)

        except Exception as e:
            print(f"AoE2 connection lost: {e}")
            await asyncio.sleep(5)


async def client_connection(websocket):
    clients.add(websocket)
    print("Bot connected.")

    try:
        if latest_message is not None:
            await websocket.send(latest_message)

        await websocket.wait_closed()

    finally:
        clients.remove(websocket)
        print("Bot disconnected.")


async def main():
    server = await websockets.serve(
        client_connection,
        LOCAL_HOST,
        LOCAL_PORT,
        max_size=None,
    )

    print(f"Forwarder listening on ws://{LOCAL_HOST}:{LOCAL_PORT}")

    await asyncio.gather(
        server.wait_closed(),
        aoe2_connection(),
    )


if __name__ == "__main__":
    asyncio.run(main())
