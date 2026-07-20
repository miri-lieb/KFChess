import asyncio
import getpass
import json

import websockets

from config import (
    MESSAGE_MOVE,
    MESSAGE_SNAPSHOT,
    NETWORK_HOST,
    NETWORK_PORT,
    PASSWORD_PROMPT,
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


def main():
    username = input(USERNAME_PROMPT).strip()
    password = getpass.getpass(PASSWORD_PROMPT)
    action = input("New user? Register [r] / Login [l]: ").strip().lower()
    register = action == "r"
    try:
        asyncio.run(_run_client(f"ws://{NETWORK_HOST}:{NETWORK_PORT}", username, password, register))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
