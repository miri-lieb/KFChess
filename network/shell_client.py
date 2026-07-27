import asyncio
import getpass
import json

import websockets

from config import (
    MESSAGE_LOGIN,
    MESSAGE_LOGIN_ACK,
    MESSAGE_MOVE,
    MESSAGE_SNAPSHOT,
    MESSAGE_CREATE_ROOM,
    MESSAGE_JOIN_ROOM,
    MESSAGE_LIST_ROOMS,
    MESSAGE_ROOM_CREATED,
    MESSAGE_ROOM_JOINED,
    MESSAGE_ROOMS_LIST,
    NETWORK_HOST,
    NETWORK_PORT,
    PASSWORD_PROMPT,
    ROOM_NAME_PROMPT,
    ROOM_ID_PROMPT,
    SHELL_COMMAND_MOVE,
    SHELL_COMMAND_QUIT,
    SHELL_COMMAND_SNAPSHOT,
    SHELL_COMMAND_HINT,
    SHELL_PROMPT,
    TICK_DURATION_MS,
    USERNAME_PROMPT,
)
from model.position import Position
from network.remote_state import RemoteController, RemoteEngineView, RemoteGameState


async def _gui_loop(engine, state, controller):
    """Render OpenCV GUI window and process user mouse clicks."""
    try:
        from view.renderer import OpenCVRenderer
        renderer = OpenCVRenderer()
    except Exception as exc:
        print(f"Could not open visual window: {exc}")
        return

    try:
        while True:
            state.tick(engine, TICK_DURATION_MS)
            renderer.set_mouse_callback(controller, engine, state)
            renderer.render(engine, controller, state)
            if not renderer.handle_input(controller, engine, state):
                break
            await asyncio.sleep(TICK_DURATION_MS / 1000.0)
    except Exception:
        pass
    finally:
        renderer.cleanup()


async def _receiver_and_printer(websocket, engine, state):
    async for raw_message in websocket:
        print(f"<< {raw_message}")
        try:
            message = json.loads(raw_message)
            state.apply_message(engine, message)
        except Exception:
            pass


async def _reader(websocket):
    while True:
        command = await asyncio.to_thread(input, SHELL_PROMPT)
        parts = command.strip().split()
        if not parts:
            continue
        action = parts[0].lower()
        if action == SHELL_COMMAND_QUIT:
            return
        if action == SHELL_COMMAND_SNAPSHOT:
            await websocket.send(json.dumps({"type": MESSAGE_SNAPSHOT}))
            continue
        if action == SHELL_COMMAND_MOVE and len(parts) == 5:
            await websocket.send(json.dumps({
                "type": MESSAGE_MOVE,
                "source": {"row": int(parts[1]), "col": int(parts[2])},
                "destination": {"row": int(parts[3]), "col": int(parts[4])},
            }))
            continue
        print(SHELL_COMMAND_HINT)


async def _start_game_session(websocket, initial_message: dict):
    payload = initial_message.get("payload", {})
    engine = RemoteEngineView()
    state = RemoteGameState()
    state.username = payload.get("username")
    state.local_role = payload.get("role")
    state.local_color = payload.get("color")
    state.apply_message(engine, initial_message)

    def send_move_fn(source: Position, destination: Position):
        asyncio.create_task(websocket.send(json.dumps({
            "type": MESSAGE_MOVE,
            "source": {"row": source.row, "col": source.col},
            "destination": {"row": destination.row, "col": destination.col},
        })))

    controller = RemoteController(engine, state, send_move_fn)

    print("\n✓ Opening visual GUI game window...")

    gui_task = asyncio.create_task(_gui_loop(engine, state, controller))
    printer_task = asyncio.create_task(_receiver_and_printer(websocket, engine, state))
    reader_task = asyncio.create_task(_reader(websocket))

    done, pending = await asyncio.wait(
        {gui_task, printer_task, reader_task},
        return_when=asyncio.FIRST_COMPLETED,
    )
    for task in pending:
        task.cancel()


async def _run_client(uri: str, username: str, password: str, register: bool):
    async with websockets.connect(uri) as websocket:
        await websocket.send(json.dumps({
            "type": MESSAGE_LOGIN,
            "username": username,
            "password": password,
            "register": register,
        }))
        try:
            raw_message = await asyncio.wait_for(websocket.recv(), timeout=5)
            message = json.loads(raw_message)
            if message.get("type") == MESSAGE_LOGIN_ACK:
                await _start_game_session(websocket, message)
            else:
                print(f"Error: {message.get('reason')}")
        except Exception as exc:
            print(f"Error: {exc}")


async def _run_rooms_client(uri: str, username: str, password: str):
    """Client with room selection menu."""
    async with websockets.connect(uri) as websocket:
        await _room_menu(websocket, username, password)


async def _room_menu(websocket, username: str, password: str):
    """Display room selection menu."""
    while True:
        print("\n=== Room Menu ===")
        print("1. Create new room")
        print("2. Join existing room")
        print("3. List available rooms")
        print("4. Direct login (classic mode)")
        choice = (await asyncio.to_thread(input, "Choose [1-4]: ")).strip()

        if choice == "1":
            await _create_room_flow(websocket, username)
            return
        elif choice == "2":
            await _join_room_flow(websocket, username, password)
            return
        elif choice == "3":
            await _list_rooms_flow(websocket)
        elif choice == "4":
            await websocket.send(json.dumps({
                "type": MESSAGE_LOGIN,
                "username": username,
                "password": password,
                "register": False,
            }))
            try:
                raw_message = await asyncio.wait_for(websocket.recv(), timeout=5)
                message = json.loads(raw_message)
                if message.get("type") == MESSAGE_LOGIN_ACK:
                    await _start_game_session(websocket, message)
                else:
                    print(f"Error: {message.get('reason')}")
            except Exception as exc:
                print(f"Error: {exc}")
            return
        else:
            print("Invalid choice")


async def _create_room_flow(websocket, username: str):
    """Create a new room."""
    room_name = await asyncio.to_thread(input, ROOM_NAME_PROMPT)
    room_name = room_name.strip()

    if room_name.lower() == "exit" or not room_name:
        return

    await websocket.send(json.dumps({
        "type": MESSAGE_CREATE_ROOM,
        "username": username,
        "room_name": room_name,
    }))

    print("Creating room...")
    try:
        raw_message = await asyncio.wait_for(websocket.recv(), timeout=5)
        message = json.loads(raw_message)
        if message.get("type") == MESSAGE_ROOM_CREATED:
            room_id = message["payload"]["room_id"]
            print(f"\n✓ Room created! Room ID: {room_id}")
            print("Share this ID with others to join")
            await _start_game_session(websocket, message)
            return
        elif message.get("type") == "error":
            print(f"Error: {message.get('reason')}")
            return
    except asyncio.TimeoutError:
        print("Error: Server did not respond in time")
        return
    except json.JSONDecodeError:
        print("Error: Invalid response from server")


async def _join_room_flow(websocket, username: str, password: str):
    """Join an existing room."""
    room_id = await asyncio.to_thread(input, ROOM_ID_PROMPT)
    room_id = room_id.strip().upper()

    if room_id.lower() == "exit" or not room_id:
        return

    await websocket.send(json.dumps({
        "type": MESSAGE_JOIN_ROOM,
        "username": username,
        "password": password,
        "room_id": room_id,
    }))

    print("Joining room...")
    try:
        raw_message = await asyncio.wait_for(websocket.recv(), timeout=5)
        message = json.loads(raw_message)
        if message.get("type") == MESSAGE_ROOM_JOINED:
            print(f"✓ Joined room successfully as {message['payload']['role']}!")
            await _start_game_session(websocket, message)
            return
        elif message.get("type") == "error":
            print(f"Error: {message.get('reason')}")
            return
    except asyncio.TimeoutError:
        print("Error: Server did not respond in time")
        return
    except json.JSONDecodeError:
        print("Error: Invalid response from server")


async def _list_rooms_flow(websocket):
    """List available rooms."""
    await websocket.send(json.dumps({
        "type": MESSAGE_LIST_ROOMS,
    }))

    try:
        raw_message = await asyncio.wait_for(websocket.recv(), timeout=5)
        message = json.loads(raw_message)
        if message.get("type") == MESSAGE_ROOMS_LIST:
            rooms = message["payload"].get("rooms", [])
            if not rooms:
                print("\nNo available rooms")
            else:
                print("\n=== Available Rooms ===")
                for room in rooms:
                    print(f"ID: {room['id']} | Name: {room['name']} | Creator: {room['creator']} | Players: {room.get('players', 0)}/2")
            return
        elif message.get("type") == "error":
            print(f"Error: {message.get('reason')}")
            return
    except asyncio.TimeoutError:
        print("Error: Server did not respond in time")
        return
    except json.JSONDecodeError:
        print("Error: Invalid response from server")


def main():
    username = input(USERNAME_PROMPT).strip()
    password = getpass.getpass(PASSWORD_PROMPT)

    print("\n=== Login Mode ===")
    print("1. Use Room system (new)")
    print("2. Direct login (classic mode)")
    mode = input("Choose [1-2]: ").strip()

    try:
        if mode == "1":
            asyncio.run(_run_rooms_client(f"ws://{NETWORK_HOST}:{NETWORK_PORT}", username, password))
        else:
            action = input("New user? Register [r] / Login [l]: ").strip().lower()
            register = action == "r"
            asyncio.run(_run_client(f"ws://{NETWORK_HOST}:{NETWORK_PORT}", username, password, register))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
