import asyncio
import json

import websockets


async def _printer(websocket):
    async for raw_message in websocket:
        print(f"<< {raw_message}")


async def _reader(websocket):
    while True:
        command = await asyncio.to_thread(input, "kfchess> ")
        parts = command.strip().split()
        if not parts:
            continue
        action = parts[0].lower()
        if action == "quit":
            return
        if action == "snapshot":
            await websocket.send(json.dumps({"type": "snapshot"}))
            continue
        if action == "move" and len(parts) == 5:
            await websocket.send(json.dumps({
                "type": "move",
                "source": {"row": int(parts[1]), "col": int(parts[2])},
                "destination": {"row": int(parts[3]), "col": int(parts[4])},
            }))
            continue
        print("Commands: move <src_row> <src_col> <dst_row> <dst_col> | snapshot | quit")


async def _run_client(uri: str):
    username = input("Username: ").strip()
    async with websockets.connect(uri) as websocket:
        await websocket.send(json.dumps({"type": "login", "username": username}))
        printer = asyncio.create_task(_printer(websocket))
        try:
            await _reader(websocket)
        finally:
            printer.cancel()


def main():
    try:
        asyncio.run(_run_client("ws://127.0.0.1:8765"))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

