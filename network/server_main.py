import asyncio

from network.server import create_local_server


async def _run_server():
    async with create_local_server() as server:
        print(f"Local WebSocket server listening on ws://{server.host}:{server.port}")
        await asyncio.Future()


def main():
    try:
        asyncio.run(_run_server())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

