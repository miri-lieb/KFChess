import asyncio
import json
import queue
import threading

from config import TICK_DURATION_MS
from model.position import Position
from network.remote_state import RemoteController, RemoteEngineView, RemoteGameState
from view.renderer import OpenCVRenderer

import websockets


class NetworkBridge:
    def __init__(self, uri: str, username: str):
        self.uri = uri
        self.username = username
        self.incoming: queue.Queue[dict] = queue.Queue()
        self.outgoing: queue.Queue[dict | None] = queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()

    def stop(self):
        self.outgoing.put(None)
        self._thread.join(timeout=2)

    def send_move(self, source: Position, destination: Position) -> None:
        self.outgoing.put({
            "type": "move",
            "source": {"row": source.row, "col": source.col},
            "destination": {"row": destination.row, "col": destination.col},
        })

    def drain_messages(self) -> list[dict]:
        messages = []
        while True:
            try:
                messages.append(self.incoming.get_nowait())
            except queue.Empty:
                return messages

    async def _sender(self, websocket):
        await websocket.send(json.dumps({"type": "login", "username": self.username}))
        while True:
            message = await asyncio.to_thread(self.outgoing.get)
            if message is None:
                break
            await websocket.send(json.dumps(message))

    async def _receiver(self, websocket):
        async for raw_message in websocket:
            self.incoming.put(json.loads(raw_message))

    async def _main(self):
        async with websockets.connect(self.uri) as websocket:
            sender = asyncio.create_task(self._sender(websocket))
            receiver = asyncio.create_task(self._receiver(websocket))
            done, pending = await asyncio.wait({sender, receiver}, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
            for task in done:
                task.result()

    def _run(self):
        asyncio.run(self._main())


def main():
    username = input("Username: ").strip()
    bridge = NetworkBridge("ws://127.0.0.1:8765", username)
    bridge.start()

    engine = RemoteEngineView()
    state = RemoteGameState()
    controller = RemoteController(engine, state, bridge.send_move)
    renderer = OpenCVRenderer()

    try:
        while True:
            for message in bridge.drain_messages():
                if message.get("type") == "login_ack":
                    payload = message["payload"]
                    state.username = payload.get("username")
                    state.local_role = payload.get("role")
                    state.local_color = payload.get("color")
                    print(f"Connected as {state.local_role}.")
                elif message.get("type") == "move_ack" and not message.get("payload", {}).get("accepted", False):
                    print(f"Move rejected: {message['payload'].get('reason')}")
                elif message.get("type") == "error":
                    print(f"Server error: {message.get('reason')}")
                state.apply_message(engine, message)
            state.tick(engine, TICK_DURATION_MS)
            renderer.set_mouse_callback(controller, engine, state)
            renderer.render(engine, controller, state)
            if not renderer.handle_input(controller, engine, state):
                break
    finally:
        bridge.stop()
        renderer.cleanup()


if __name__ == "__main__":
    main()
