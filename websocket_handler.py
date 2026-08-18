import asyncio
import json
import websockets


class WebSocketHandler:
    def __init__(self, url, match_handler, socket_size = 10*1024*1024):
        self.url = url
        self.match_handler = match_handler
        self.running = True
        self.socket_size = socket_size

    async def run(self):
        while self.running:
            try:
                async with websockets.connect(
                    self.url,
                    max_size=self.socket_size,
                ) as websocket:
                    print("WebSocket connected.")

                    async for message in websocket:
                        data = json.loads(message)
                        self.match_handler.update(data)

            except (
                websockets.ConnectionClosed,
                ConnectionError,
                asyncio.TimeoutError,
            ) as e:
                print(f"WebSocket disconnected: {e}")

                if self.running:
                    await asyncio.sleep(5)

    def stop(self):
        self.running = False
