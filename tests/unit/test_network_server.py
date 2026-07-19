import asyncio
import json

import websockets

from engine.game_engine import GameEngine
from model.setup import standard_starting_board
from network.event_bus import InMemoryEventBus
from network.server import LocalWebSocketGameServer


def test_websocket_server_logs_in_two_players_and_rejects_third():
    async def scenario():
        bus = InMemoryEventBus()
        engine = GameEngine(standard_starting_board(), event_bus=bus)
        async with LocalWebSocketGameServer(engine, bus, port=8876, tick_duration_ms=10):
            async with websockets.connect("ws://127.0.0.1:8876") as white_ws:
                await white_ws.send(json.dumps({"type": "login", "username": "alice"}))
                white_ack = json.loads(await white_ws.recv())
                assert white_ack["type"] == "login_ack"
                assert white_ack["payload"]["color"] == "white"

                joined = json.loads(await white_ws.recv())
                assert joined["type"] == "player_joined"
                assert joined["payload"]["username"] == "alice"

                async with websockets.connect("ws://127.0.0.1:8876") as black_ws:
                    await black_ws.send(json.dumps({"type": "login", "username": "bob"}))
                    black_ack = json.loads(await black_ws.recv())
                    assert black_ack["type"] == "login_ack"
                    assert black_ack["payload"]["color"] == "black"

                    player_joined_for_black = json.loads(await black_ws.recv())
                    game_started_for_black = json.loads(await black_ws.recv())
                    if player_joined_for_black["type"] == "game_started":
                        player_joined_for_black, game_started_for_black = game_started_for_black, player_joined_for_black
                    assert player_joined_for_black["type"] == "player_joined"
                    assert game_started_for_black["type"] == "game_started"

                    white_followups = [json.loads(await white_ws.recv()) for _ in range(2)]
                    types = {message["type"] for message in white_followups}
                    assert {"player_joined", "game_started"} == types

                    async with websockets.connect("ws://127.0.0.1:8876") as third_ws:
                        await third_ws.send(json.dumps({"type": "login", "username": "carol"}))
                        observer_ack = json.loads(await third_ws.recv())
                        assert observer_ack["type"] == "login_ack"
                        assert observer_ack["payload"]["role"] == "observer"
                        assert observer_ack["payload"]["color"] is None

    asyncio.run(scenario())


def test_websocket_server_routes_moves_through_engine():
    async def scenario():
        bus = InMemoryEventBus()
        engine = GameEngine(standard_starting_board(), event_bus=bus)
        async with LocalWebSocketGameServer(engine, bus, port=8877, tick_duration_ms=10):
            async with websockets.connect("ws://127.0.0.1:8877") as white_ws:
                await white_ws.send(json.dumps({"type": "login", "username": "alice"}))
                await white_ws.recv()
                await white_ws.recv()

                async with websockets.connect("ws://127.0.0.1:8877") as black_ws:
                    await black_ws.send(json.dumps({"type": "login", "username": "bob"}))
                    await black_ws.recv()
                    await black_ws.recv()
                    await black_ws.recv()
                    await white_ws.recv()
                    await white_ws.recv()

                    await white_ws.send(json.dumps({
                        "type": "move",
                        "source": {"row": 6, "col": 0},
                        "destination": {"row": 5, "col": 0},
                    }))
                    ack = json.loads(await white_ws.recv())
                    assert ack["type"] == "move_ack"
                    assert ack["payload"]["accepted"] is True

                    move_requested = json.loads(await white_ws.recv())
                    assert move_requested["type"] == "move_requested"
                    assert move_requested["payload"]["accepted"] is True
                    assert "motion" in move_requested["payload"]

    asyncio.run(scenario())


def test_websocket_server_blocks_observer_moves():
    async def scenario():
        bus = InMemoryEventBus()
        engine = GameEngine(standard_starting_board(), event_bus=bus)
        async with LocalWebSocketGameServer(engine, bus, port=8891, tick_duration_ms=10):
            async with websockets.connect("ws://127.0.0.1:8891") as white_ws:
                await white_ws.send(json.dumps({"type": "login", "username": "alice"}))
                await white_ws.recv()
                await white_ws.recv()

                async with websockets.connect("ws://127.0.0.1:8891") as black_ws:
                    await black_ws.send(json.dumps({"type": "login", "username": "bob"}))
                    await black_ws.recv()
                    await black_ws.recv()
                    await black_ws.recv()
                    await white_ws.recv()
                    await white_ws.recv()

                    async with websockets.connect("ws://127.0.0.1:8891") as observer_ws:
                        await observer_ws.send(json.dumps({"type": "login", "username": "carol"}))
                        observer_ack = json.loads(await observer_ws.recv())
                        assert observer_ack["payload"]["role"] == "observer"
                        await observer_ws.recv()
                        await observer_ws.send(json.dumps({
                            "type": "move",
                            "source": {"row": 6, "col": 0},
                            "destination": {"row": 5, "col": 0},
                        }))
                        ack = json.loads(await observer_ws.recv())
                        assert ack["type"] == "move_ack"
                        assert ack["payload"]["accepted"] is False
                        assert ack["payload"]["reason"] == "observer_read_only"

    asyncio.run(scenario())


def test_websocket_server_frees_player_seat_on_disconnect():
    async def scenario():
        bus = InMemoryEventBus()
        engine = GameEngine(standard_starting_board(), event_bus=bus)
        async with LocalWebSocketGameServer(engine, bus, port=8879, tick_duration_ms=10):
            async with websockets.connect("ws://127.0.0.1:8879") as white_ws:
                await white_ws.send(json.dumps({"type": "login", "username": "\udcd7miri"}))
                ack = json.loads(await white_ws.recv())
                assert ack["payload"]["username"] == "miri"
                await white_ws.recv()

            async with websockets.connect("ws://127.0.0.1:8879") as replacement_ws:
                await replacement_ws.send(json.dumps({"type": "login", "username": "new-player"}))
                ack = json.loads(await replacement_ws.recv())
                assert ack["payload"]["role"] == "white"

    asyncio.run(scenario())
