import asyncio
import getpass
import json
import queue
import threading

from config import (
    CONNECTED_AS_TEMPLATE,
    MESSAGE_ERROR,
    MESSAGE_LOGIN,
    MESSAGE_LOGIN_ACK,
    MESSAGE_MOVE,
    MESSAGE_MOVE_ACK,
    MOVE_REJECTED_PREFIX,
    NETWORK_HOST,
    NETWORK_PORT,
    PASSWORD_PROMPT,
    SERVER_ERROR_PREFIX,
    TICK_DURATION_MS,
    USERNAME_PROMPT,
)
from model.position import Position
from network.remote_state import RemoteController, RemoteEngineView, RemoteGameState
from view.renderer import OpenCVRenderer

import websockets


class NetworkBridge:
    def __init__(self, uri: str, username: str, password: str, register: bool):
        self.uri = uri
        self.username = username
        self.password = password
        self.register = register
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
            "type": MESSAGE_MOVE,
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
        await websocket.send(json.dumps({
            "type": MESSAGE_LOGIN,
            "username": self.username,
            "password": self.password,
            "register": self.register,
        }))
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
    username = input(USERNAME_PROMPT).strip()
    password = getpass.getpass(PASSWORD_PROMPT)
    action = input("New user? Register [r] / Login [l]: ").strip().lower()
    register = action == "r"

    bridge = NetworkBridge(f"ws://{NETWORK_HOST}:{NETWORK_PORT}", username, password, register)
    bridge.start()

    # Wait for login_ack or error before opening the window
    print("Connecting...")
    login_result = None
    for _ in range(50):  # up to 5 seconds
        for message in bridge.drain_messages():
            if message.get("type") == MESSAGE_LOGIN_ACK:
                login_result = message
            elif message.get("type") == MESSAGE_ERROR:
                print(f"{SERVER_ERROR_PREFIX}{message.get('reason')}")
                bridge.stop()
                return
        if login_result:
            break
        import time
        time.sleep(0.1)

    if login_result is None:
        print("Could not connect to server.")
        bridge.stop()
        return

    payload = login_result["payload"]
    engine = RemoteEngineView()
    state = RemoteGameState()
    state.username = payload.get("username")
    state.local_role = payload.get("role")
    state.local_color = payload.get("color")
    elo = payload.get("elo", "?")
    print(CONNECTED_AS_TEMPLATE.format(state.local_role) + f"  ELO: {elo}")
    state.apply_message(engine, login_result)

    controller = RemoteController(engine, state, bridge.send_move)
    renderer = OpenCVRenderer()

    try:
        while True:
            for message in bridge.drain_messages():
                if message.get("type") == MESSAGE_MOVE_ACK and not message.get("payload", {}).get("accepted", False):
                    print(f"{MOVE_REJECTED_PREFIX}{message['payload'].get('reason')}")
                elif message.get("type") == MESSAGE_ERROR:
                    print(f"{SERVER_ERROR_PREFIX}{message.get('reason')}")
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
