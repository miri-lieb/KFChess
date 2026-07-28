import asyncio
import logging

from network.server import create_local_server


async def _run_server():
    server = await create_local_server()
    async with server:
        print(f"Local WebSocket server listening on ws://{server.host}:{server.port}")
        await asyncio.Future()


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        asyncio.run(_run_server())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
