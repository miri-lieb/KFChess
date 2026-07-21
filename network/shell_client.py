import asyncio
import getpass
import json

import websockets

from config import (
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
    USERNAME_PROMPT,
)


async def _printer(websocket):
    async for raw_message in websocket:
        print(f"<< {raw_message}")


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


async def _run_client(uri: str, username: str, password: str, register: bool):
    async with websockets.connect(uri) as websocket:
        # Try to login first
        await websocket.send(json.dumps({
            "type": "login",
            "username": username,
            "password": password,
            "register": register,
        }))
        printer = asyncio.create_task(_printer(websocket))
        try:
            await _reader(websocket)
        finally:
            printer.cancel()


async def _run_rooms_client(uri: str, username: str, password: str):
    """Client with room selection menu."""
    async with websockets.connect(uri) as websocket:
        printer = asyncio.create_task(_printer(websocket))
        try:
            await _room_menu(websocket, username, password)
        finally:
            printer.cancel()


async def _room_menu(websocket, username: str, password: str):
    """Display room selection menu."""
    while True:
        print("\n=== Room Menu ===")
        print("1. Create new room")
        print("2. Join existing room")
        print("3. List available rooms")
        print("4. Direct login (classic mode)")
        choice = await asyncio.to_thread(input, "Choose [1-4]: ").strip()
        
        if choice == "1":
            await _create_room_flow(websocket, username)
            return
        elif choice == "2":
            await _join_room_flow(websocket, username, password)
            return
        elif choice == "3":
            await _list_rooms_flow(websocket)
        elif choice == "4":
            # Direct login without rooms
            await websocket.send(json.dumps({
                "type": "login",
                "username": username,
                "password": password,
                "register": False,
            }))
            await _reader(websocket)
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
    
    # Wait for response
    print("Creating room...")
    async for raw_message in websocket:
        try:
            message = json.loads(raw_message)
            if message.get("type") == MESSAGE_ROOM_CREATED:
                room_id = message["payload"]["room_id"]
                print(f"\n✓ Room created! Room ID: {room_id}")
                print("Share this ID with others to join")
                await _reader(websocket)
                return
            elif message.get("type") == "error":
                print(f"Error: {message.get('reason')}")
                return
        except json.JSONDecodeError:
            print(f"<< {raw_message}")


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
    
    # Wait for response
    print("Joining room...")
    async for raw_message in websocket:
        try:
            message = json.loads(raw_message)
            if message.get("type") == MESSAGE_ROOM_JOINED:
                print(f"✓ Joined room successfully!")
                await _reader(websocket)
                return
            elif message.get("type") == "error":
                print(f"Error: {message.get('reason')}")
                return
        except json.JSONDecodeError:
            print(f"<< {raw_message}")


async def _list_rooms_flow(websocket):
    """List available rooms."""
    await websocket.send(json.dumps({
        "type": MESSAGE_LIST_ROOMS,
    }))
    
    async for raw_message in websocket:
        try:
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
        except json.JSONDecodeError:
            print(f"<< {raw_message}")


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
