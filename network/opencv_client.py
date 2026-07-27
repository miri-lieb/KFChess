import asyncio
import getpass
import json
import queue
import sys
import threading
import time

from config import (
    CONNECTED_AS_TEMPLATE,
    MESSAGE_CREATE_ROOM,
    MESSAGE_ERROR,
    MESSAGE_JOIN_ROOM,
    MESSAGE_LIST_ROOMS,
    MESSAGE_LOGIN,
    MESSAGE_LOGIN_ACK,
    MESSAGE_MOVE,
    MESSAGE_MOVE_ACK,
    MESSAGE_ROOM_CREATED,
    MESSAGE_ROOM_JOINED,
    MESSAGE_ROOMS_LIST,
    MOVE_REJECTED_PREFIX,
    NETWORK_HOST,
    NETWORK_PORT,
    PASSWORD_PROMPT,
    ROOM_ID_PROMPT,
    ROOM_NAME_PROMPT,
    SERVER_ERROR_PREFIX,
    TICK_DURATION_MS,
    USERNAME_PROMPT,
)
from model.position import Position
from network.remote_state import RemoteController, RemoteEngineView, RemoteGameState
from view.renderer import OpenCVRenderer

import websockets


class NetworkBridge:
    def __init__(self, uri: str):
        self.uri = uri
        self.incoming: queue.Queue[dict] = queue.Queue()
        self.outgoing: queue.Queue[dict | None] = queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()

    def stop(self):
        self.outgoing.put(None)
        self._thread.join(timeout=2)

    def send_message(self, message: dict) -> None:
        self.outgoing.put(message)

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


def wait_for_response(bridge: NetworkBridge, expected_types: set[str], timeout_seconds: float = 5.0) -> dict | None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        for message in bridge.drain_messages():
            msg_type = message.get("type")
            if msg_type in expected_types:
                return message
            if msg_type == MESSAGE_ERROR:
                print(f"{SERVER_ERROR_PREFIX}{message.get('reason')}")
                return None
        time.sleep(0.05)
    print("Error: Server response timed out.")
    return None


def main():
    username = input(USERNAME_PROMPT).strip()
    password = getpass.getpass(PASSWORD_PROMPT)

    bridge = NetworkBridge(f"ws://{NETWORK_HOST}:{NETWORK_PORT}")
    bridge.start()

    entry_result = None

    while entry_result is None:
        print("\n=== Room Menu ===")
        print("1. Create new room")
        print("2. Join existing room")
        print("3. List available rooms")
        print("4. Direct login (classic mode)")
        choice = input("Choose [1-4]: ").strip()

        if choice == "1":
            room_name = input(ROOM_NAME_PROMPT).strip()
            if not room_name or room_name.lower() == "exit":
                continue
            bridge.send_message({
                "type": MESSAGE_CREATE_ROOM,
                "username": username,
                "password": password,
                "room_name": room_name,
            })
            print("Creating room...")
            entry_result = wait_for_response(bridge, {MESSAGE_ROOM_CREATED})

        elif choice == "2":
            room_id = input(ROOM_ID_PROMPT).strip().upper()
            if not room_id or room_id.lower() == "exit":
                continue
            bridge.send_message({
                "type": MESSAGE_JOIN_ROOM,
                "username": username,
                "password": password,
                "room_id": room_id,
            })
            print("Joining room...")
            entry_result = wait_for_response(bridge, {MESSAGE_ROOM_JOINED})

        elif choice == "3":
            bridge.send_message({
                "type": MESSAGE_LIST_ROOMS,
            })
            response = wait_for_response(bridge, {MESSAGE_ROOMS_LIST})
            if response:
                rooms = response.get("payload", {}).get("rooms", [])
                if not rooms:
                    print("\nNo available rooms.")
                else:
                    print("\n=== Available Rooms ===")
                    for room in rooms:
                        print(f"ID: {room['id']} | Name: {room['name']} | Creator: {room['creator']} | Players: {room.get('players', 0)}/2")

        elif choice == "4":
            action = input("New user? Register [r] / Login [l]: ").strip().lower()
            register = action == "r"
            bridge.send_message({
                "type": MESSAGE_LOGIN,
                "username": username,
                "password": password,
                "register": register,
            })
            print("Logging in...")
            entry_result = wait_for_response(bridge, {MESSAGE_LOGIN_ACK})

        else:
            print("Invalid choice")

    if entry_result is None:
        bridge.stop()
        return

    payload = entry_result.get("payload", {})
    engine = RemoteEngineView()
    state = RemoteGameState()
    state.username = payload.get("username", username)
    state.local_role = payload.get("role")
    state.local_color = payload.get("color")
    elo = payload.get("elo", "?")
    room_id = payload.get("room_id")

    if room_id:
        print(f"Successfully joined room '{room_id}' as {state.local_role}! ELO: {elo}")
    else:
        print(CONNECTED_AS_TEMPLATE.format(state.local_role) + f"  ELO: {elo}")

    state.apply_message(engine, entry_result)

    controller = RemoteController(engine, state, bridge.send_move)

    print("Opening visual game window...")
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
