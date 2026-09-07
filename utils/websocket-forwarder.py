# scriipt  to keep constant connection to the aoe2companion websocket and i can connect my code to a local websocket for development so that i do no abuse the aoe2companions socket by restarting my scripts

# Script to keep constant connections to the AoE2 Companion WebSockets
# so development restarts don't repeatedly reconnect to the service.

import asyncio
import websockets


CONNECTIONS = [
    {
        "name": "ongoing-matches",
        "aoe2_url": "wss://socket.aoe2companion.com/listen?handler=match-started",
        "local_host": "0.0.0.0",
        "local_port": 8765,
    },
    {
        "name": "lobbies",
        "aoe2_url": "wss://socket.aoe2companion.com/listen?handler=match-finished",
        "local_host": "0.0.0.0",
        "local_port": 8766,
    },
]


async def broadcast(clients, message):
    if not clients:
        return

    await asyncio.gather(
        *(client.send(message) for client in clients),
        return_exceptions=True,
    )


async def aoe2_connection(connection, clients, state):
    while True:
        try:
            async with websockets.connect(
                connection["aoe2_url"],
                max_size=None,
            ) as websocket:
                print(f"Connected to AoE2 Companion: {connection['name']}")

                async for message in websocket:
                    state["latest_message"] = message
                    await broadcast(clients, message)

        except Exception as e:
            print(
                f"{connection['name']} connection lost: {e}"
            )
            await asyncio.sleep(5)


async def client_connection(websocket, clients, state, name):
    clients.add(websocket)
    print(f"Bot connected to {name}.")

    try:
        if state["latest_message"] is not None:
            await websocket.send(state["latest_message"])

        await websocket.wait_closed()

    finally:
        clients.discard(websocket)
        print(f"Bot disconnected from {name}.")


async def run_connection(connection):
    clients = set()

    state = {
        "latest_message": None,
    }

    server = await websockets.serve(
        lambda websocket: client_connection(
            websocket,
            clients,
            state,
            connection["name"],
        ),
        connection["local_host"],
        connection["local_port"],
        max_size=None,
    )

    print(
        f"{connection['name']} forwarder listening on "
        f"ws://{connection['local_host']}:{connection['local_port']}"
    )

    await asyncio.gather(
        server.wait_closed(),
        aoe2_connection(connection, clients, state),
    )


async def main():
    await asyncio.gather(
        *(run_connection(connection) for connection in CONNECTIONS)
    )


if __name__ == "__main__":
    asyncio.run(main())
