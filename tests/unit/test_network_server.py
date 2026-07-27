import asyncio
import json

import websockets

from engine.game_engine import GameEngine
from model.setup import standard_starting_board
from network.event_bus import InMemoryEventBus
from network.server import LocalWebSocketGameServer


async def _drain(ws, timeout=0.2):
    """Drain all pending messages from a websocket without blocking forever."""
    messages = []
    try:
        while True:
            msg = await asyncio.wait_for(ws.recv(), timeout=timeout)
            messages.append(json.loads(msg))
    except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed):
        pass
    return messages


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


def test_websocket_server_room_create_and_join():
    async def scenario():
        bus = InMemoryEventBus()
        engine = GameEngine(standard_starting_board(), event_bus=bus)
        async with LocalWebSocketGameServer(engine, bus, port=8888, tick_duration_ms=10):
            async with websockets.connect("ws://127.0.0.1:8888") as creator_ws:
                await creator_ws.send(json.dumps({
                    "type": "create_room",
                    "username": "alice",
                    "room_name": "Test Room",
                }))
                created_msg = json.loads(await creator_ws.recv())
                assert created_msg["type"] == "room_created"
                assert created_msg["payload"]["room_name"] == "Test Room"
                assert created_msg["payload"]["role"] == "white"
                assert "snapshot" in created_msg["payload"]
                room_id = created_msg["payload"]["room_id"]

                async with websockets.connect("ws://127.0.0.1:8888") as joiner_ws:
                    await joiner_ws.send(json.dumps({
                        "type": "join_room",
                        "username": "bob",
                        "room_id": room_id,
                    }))
                    joined_msg = json.loads(await joiner_ws.recv())
                    assert joined_msg["type"] == "room_joined"
                    assert joined_msg["payload"]["room_id"] == room_id
                    assert joined_msg["payload"]["role"] == "black"
                    assert "snapshot" in joined_msg["payload"]

    asyncio.run(scenario())


def test_two_rooms_are_isolated():
    """Moves in Room A must not appear in Room B."""
    async def scenario():
        bus = InMemoryEventBus()
        engine = GameEngine(standard_starting_board(), event_bus=bus)
        async with LocalWebSocketGameServer(engine, bus, port=8899, tick_duration_ms=10):
            # --- Room A: alice (white) + bob (black) ---
            async with websockets.connect("ws://127.0.0.1:8899") as alice_ws:
                await alice_ws.send(json.dumps({
                    "type": "create_room",
                    "username": "alice",
                    "room_name": "Room A",
                }))
                created = json.loads(await alice_ws.recv())
                assert created["type"] == "room_created"
                room_a_id = created["payload"]["room_id"]

                async with websockets.connect("ws://127.0.0.1:8899") as bob_ws:
                    await bob_ws.send(json.dumps({
                        "type": "join_room",
                        "username": "bob",
                        "room_id": room_a_id,
                    }))
                    joined_a = json.loads(await bob_ws.recv())
                    assert joined_a["type"] == "room_joined"

                    # Drain player_joined from alice
                    await _drain(alice_ws)

                    # --- Room B: carol (white) + dave (black) ---
                    async with websockets.connect("ws://127.0.0.1:8899") as carol_ws:
                        await carol_ws.send(json.dumps({
                            "type": "create_room",
                            "username": "carol",
                            "room_name": "Room B",
                        }))
                        created_b = json.loads(await carol_ws.recv())
                        assert created_b["type"] == "room_created"
                        room_b_id = created_b["payload"]["room_id"]
                        assert room_b_id != room_a_id

                        async with websockets.connect("ws://127.0.0.1:8899") as dave_ws:
                            await dave_ws.send(json.dumps({
                                "type": "join_room",
                                "username": "dave",
                                "room_id": room_b_id,
                            }))
                            joined_b = json.loads(await dave_ws.recv())
                            assert joined_b["type"] == "room_joined"

                            # Drain player_joined from carol
                            await _drain(carol_ws)

                            # Alice makes a move in Room A
                            await alice_ws.send(json.dumps({
                                "type": "move",
                                "source": {"row": 6, "col": 0},
                                "destination": {"row": 5, "col": 0},
                            }))
                            ack = json.loads(await alice_ws.recv())
                            assert ack["type"] == "move_ack"
                            assert ack["payload"]["accepted"] is True

                            # Wait briefly for any cross-room leakage
                            await asyncio.sleep(0.1)

                            # Room B connections must NOT have received the move
                            carol_msgs = await _drain(carol_ws, timeout=0.1)
                            dave_msgs = await _drain(dave_ws, timeout=0.1)
                            carol_types = [m["type"] for m in carol_msgs]
                            dave_types = [m["type"] for m in dave_msgs]
                            assert "move_requested" not in carol_types, f"Room B (carol) got leaked event: {carol_types}"
                            assert "move_requested" not in dave_types, f"Room B (dave) got leaked event: {dave_types}"

                            # Room A connections SHOULD have received the move
                            bob_msgs = await _drain(bob_ws, timeout=0.5)
                            bob_types = [m["type"] for m in bob_msgs]
                            assert "move_requested" in bob_types, f"Room A (bob) missed event: {bob_types}"

    asyncio.run(scenario())


def test_remote_state_ignores_wrong_room_messages():
    """RemoteGameState.apply_message ignores messages tagged with a different room_id."""
    from network.remote_state import RemoteEngineView, RemoteGameState

    engine = RemoteEngineView()
    state = RemoteGameState()
    state.current_room_id = "ROOM_A"

    state.apply_message(engine, {
        "type": "move_requested",
        "payload": {
            "room_id": "ROOM_B",
            "accepted": True,
            "motion": {
                "piece": {"id": "x", "color": "white", "kind": "pawn", "cell": {"row": 6, "col": 0}, "state": "idle"},
                "source": {"row": 6, "col": 0},
                "destination": {"row": 5, "col": 0},
                "duration_ms": 1000,
                "order": 1,
                "start_time_ms": 0,
                "finish_time_ms": 1000,
                "return_to_fallback": False,
            },
            "elapsed_time_ms": 0,
        },
    })
    assert len(engine.arbiter.active_motions) == 0

    # Same room_id should be applied
    state.apply_message(engine, {
        "type": "move_requested",
        "payload": {
            "room_id": "ROOM_A",
            "accepted": True,
            "motion": {
                "piece": {"id": "p1", "color": "white", "kind": "pawn", "cell": {"row": 6, "col": 0}, "state": "idle"},
                "source": {"row": 6, "col": 0},
                "destination": {"row": 5, "col": 0},
                "duration_ms": 1000,
                "order": 1,
                "start_time_ms": 0,
                "finish_time_ms": 1000,
                "return_to_fallback": False,
            },
            "elapsed_time_ms": 0,
        },
    })
    assert len(engine.arbiter.active_motions) == 1

