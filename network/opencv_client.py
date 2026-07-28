import asyncio
import json
import queue
import sys
import threading
import time

import cv2

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
    SERVER_ERROR_PREFIX,
    TICK_DURATION_MS,
    WINDOW_TITLE,
)
from model.position import Position
from network.remote_state import RemoteController, RemoteEngineView, RemoteGameState
from view.auth_renderer import AuthInput, create_auth_canvas, render_auth_screen
from view.lobby_renderer import LobbyState, create_lobby_canvas, render_lobby_screen
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


def _run_auth_screen(bridge: NetworkBridge) -> tuple[str, str] | None:
    """Run the OpenCV auth screen. Returns (username, password) on success, None to quit."""
    window_name = WINDOW_TITLE
    cv2.namedWindow(window_name)

    auth_input = AuthInput()
    canvas = create_auth_canvas()

    while True:
        render_auth_screen(canvas, auth_input)
        cv2.imshow(window_name, canvas)
        key = cv2.waitKey(50)
        auth_input.handle_key(key)

        data = auth_input.consume_submit()
        if data is not None:
            tab, username, password = data
            is_register = tab == "register"
            bridge.send_message({
                "type": MESSAGE_LOGIN,
                "username": username,
                "password": password,
                "register": is_register,
            })
            deadline = time.time() + 5.0
            response = None
            while time.time() < deadline:
                for message in bridge.drain_messages():
                    msg_type = message.get("type")
                    if msg_type == MESSAGE_LOGIN_ACK:
                        response = message
                        break
                    if msg_type == MESSAGE_ERROR:
                        reason = message.get("reason", "unknown")
                        friendly = {
                            "invalid_credentials": "Invalid username or password",
                            "user_already_exists": "Username already taken",
                            "username_required": "Username is required",
                        }.get(reason, reason)
                        auth_input.set_error(friendly)
                        break
                if response is not None:
                    break
                time.sleep(0.05)

            if response is not None:
                cv2.destroyWindow(window_name)
                return username, password

            if not auth_input.error_msg:
                auth_input.set_error("Server did not respond")

        if key == 27 and not auth_input.username and not auth_input.password:
            break

    cv2.destroyWindow(window_name)
    return None


def _run_lobby_screen(bridge: NetworkBridge, username: str, password: str) -> dict | None:
    window_name = WINDOW_TITLE
    cv2.namedWindow(window_name)

    lobby = LobbyState()
    lobby.username = username
    canvas = create_lobby_canvas()

    click_pos = []

    def mouse_callback(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            click_pos.append((x, y))

    cv2.setMouseCallback(window_name, mouse_callback)

    def refresh_rooms():
        bridge.send_message({"type": MESSAGE_LIST_ROOMS})

    refresh_rooms()

    while True:
        # Handle mouse clicks
        while click_pos:
            mx, my = click_pos.pop(0)
            action = lobby.handle_click(mx, my)
            if action is not None:
                atype, avalue = action
                lobby.set_waiting(atype)
                send_map = {
                    "create": (MESSAGE_CREATE_ROOM, {"room_name": avalue}),
                    "join_id": (MESSAGE_JOIN_ROOM, {"room_id": avalue}),
                    "join_room": (MESSAGE_JOIN_ROOM, {"room_id": avalue}),
                }
                msg_type, extra = send_map[atype]
                bridge.send_message({
                    "type": msg_type, "username": username,
                    "password": password, **extra,
                })

        # Drain incoming messages
        for message in bridge.drain_messages():
            msg_type = message.get("type")
            if msg_type == MESSAGE_ROOMS_LIST:
                lobby.rooms = message.get("payload", {}).get("rooms", [])
                lobby.needs_refresh = False
            elif msg_type in (MESSAGE_ROOM_CREATED, MESSAGE_ROOM_JOINED):
                lobby.clear_waiting()
                cv2.destroyWindow(window_name)
                return message
            elif msg_type == MESSAGE_ERROR:
                lobby.clear_waiting()
                reason = message.get("reason", "Operation failed")
                lobby.set_error(reason)

        if lobby.needs_refresh:
            refresh_rooms()

        key = cv2.waitKey(50)
        action = lobby.handle_key(key)

        if action is not None:
            atype, avalue = action
            lobby.set_waiting(atype)
            send_map = {
                "create": (MESSAGE_CREATE_ROOM, {"room_name": avalue}),
                "join_id": (MESSAGE_JOIN_ROOM, {"room_id": avalue}),
                "join_room": (MESSAGE_JOIN_ROOM, {"room_id": avalue}),
            }
            msg_type, extra = send_map[atype]
            bridge.send_message({
                "type": msg_type, "username": username,
                "password": password, **extra,
            })

        if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
            break

        render_lobby_screen(canvas, lobby)
        cv2.imshow(window_name, canvas)

        if key == 27 and not lobby.room_name_input and not lobby.join_id_input and not lobby.rooms:
            break

    cv2.destroyWindow(window_name)
    return None


def main():
    bridge = NetworkBridge(f"ws://{NETWORK_HOST}:{NETWORK_PORT}")
    bridge.start()

    auth_result = _run_auth_screen(bridge)
    if auth_result is None:
        bridge.stop()
        return
    username, password = auth_result

    entry_result = _run_lobby_screen(bridge, username, password)

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
