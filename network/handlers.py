import json
import logging

from config import (
    MESSAGE_ERROR,
    MESSAGE_GAME_STARTED,
    MESSAGE_LOGIN_ACK,
    MESSAGE_MOVE_ACK,
    MESSAGE_PLAYER_JOINED,
    MESSAGE_ROOM_CREATED,
    MESSAGE_ROOM_JOINED,
    MESSAGE_ROOMS_LIST,
    MESSAGE_SNAPSHOT,
    REASON_EMPTY_SOURCE,
    REASON_INVALID_MOVE_PAYLOAD,
    REASON_INVALID_ROOM_NAME,
    REASON_LOGIN_REQUIRED,
    REASON_OBSERVER_READ_ONLY,
    REASON_ROOM_FULL,
    REASON_ROOM_NOT_FOUND,
    REASON_WRONG_PLAYER_COLOR,
    ROLE_OBSERVER,
)
from network.events import subscribe_room_events
from network.serialization import position_from_dict, snapshot_to_dict

logger = logging.getLogger(__name__)

async def handle_login(server, websocket, message):
    username = str(message.get("username", ""))
    password = str(message.get("password", ""))
    register = bool(message.get("register", False))
    try:
        if register:
            seat = await server.lobby.register(username, password)
        else:
            seat = await server.lobby.login(username, password)
    except Exception as exc:
        await websocket.send(
            json.dumps({"type": MESSAGE_ERROR, "reason": str(exc)})
        )
        await websocket.close()
        return
    server._sessions[websocket] = seat
    if seat.color is not None:
        server.engine.players[seat.color].name = seat.username
    await websocket.send(json.dumps({
        "type": MESSAGE_LOGIN_ACK,
        "payload": {
            "username": seat.username,
            "role": seat.role,
            "color": seat.color,
            "elo": seat.elo,
            "snapshot": snapshot_to_dict(server.engine),
        },
    }))
    server.event_bus.publish(
        MESSAGE_PLAYER_JOINED,
        {"username": seat.username, "role": seat.role, "color": seat.color},
    )
    if server.lobby.is_ready() and not server._game_started:
        server._game_started = True
        server.event_bus.publish(MESSAGE_GAME_STARTED, {
            "players": [
                {
                    "username": player.username,
                    "role": player.role,
                    "color": player.color,
                    "elo": player.elo,
                }
                for player in server.lobby.players()
            ],
            "snapshot": snapshot_to_dict(server.engine),
        })

async def handle_relogin(server, websocket, seat):
    await websocket.send(json.dumps({
        "type": MESSAGE_LOGIN_ACK,
        "payload": {
            "username": seat.username,
            "role": seat.role,
            "color": seat.color,
            "elo": seat.elo,
            "snapshot": snapshot_to_dict(server.engine),
        },
    }))

async def handle_move(server, websocket, seat, message, room_id):
    try:
        source = position_from_dict(message["source"])
        destination = position_from_dict(message["destination"])
    except (KeyError, TypeError, ValueError):
        await websocket.send(
            json.dumps({"type": MESSAGE_ERROR, "reason": REASON_INVALID_MOVE_PAYLOAD})
        )
        return

    engine = server.engine
    if room_id:
        room = server.room_manager.get_room(room_id)
        if room and room.engine:
            engine = room.engine

    if seat.role == ROLE_OBSERVER:
        await websocket.send(json.dumps({
            "type": MESSAGE_MOVE_ACK,
            "payload": {"accepted": False, "reason": REASON_OBSERVER_READ_ONLY},
        }))
        return
    piece = engine.board.get_piece(source)
    if piece is None:
        await websocket.send(json.dumps({
            "type": MESSAGE_MOVE_ACK,
            "payload": {"accepted": False, "reason": REASON_EMPTY_SOURCE},
        }))
        return
    if piece.color != seat.color:
        await websocket.send(json.dumps({
            "type": MESSAGE_MOVE_ACK,
            "payload": {"accepted": False, "reason": REASON_WRONG_PLAYER_COLOR},
        }))
        return

    result = engine.request_move(source, destination)
    await websocket.send(json.dumps({
        "type": MESSAGE_MOVE_ACK,
        "payload": {
            "accepted": result.is_accepted,
            "reason": result.reason,
        },
    }))


async def handle_create_room(server, websocket, message):
    username = str(message.get("username", "")).strip()
    room_name = str(message.get("room_name", "")).strip()
    password = str(message.get("password", ""))

    if not username:
        await websocket.send(
            json.dumps({"type": MESSAGE_ERROR, "reason": REASON_LOGIN_REQUIRED})
        )
        return

    if not room_name or len(room_name) > 100:
        await websocket.send(
            json.dumps({"type": MESSAGE_ERROR, "reason": REASON_INVALID_ROOM_NAME})
        )
        return

    try:
        room_id = await server.room_manager.create_room(room_name, username)
        role, seat = await server.room_manager.join_room(room_id, username, password)
        room = server.room_manager.get_room(room_id)
        server._sessions[websocket] = (seat, room_id)
        server._connections.discard(websocket)
        server._room_connections.setdefault(room_id, set()).add(websocket)
        if seat.color is not None and room.engine:
            room.engine.players[seat.color].name = seat.username
        await websocket.send(json.dumps({
            "type": MESSAGE_ROOM_CREATED,
            "payload": {
                "room_id": room_id,
                "room_name": room_name,
                "username": seat.username,
                "role": seat.role,
                "color": seat.color,
                "elo": seat.elo,
                "snapshot": snapshot_to_dict(room.engine) if room.engine else {},
            },
        }))
        subscribe_room_events(server, room_id)
        room.event_bus.publish(MESSAGE_PLAYER_JOINED, {
            "username": seat.username,
            "role": seat.role,
            "color": seat.color,
        })
    except Exception as exc:
        await websocket.send(
            json.dumps({"type": MESSAGE_ERROR, "reason": str(exc)})
        )


async def handle_join_room(server, websocket, message):
    username = str(message.get("username", "")).strip()
    password = str(message.get("password", ""))
    room_id = str(message.get("room_id", "")).strip().upper()

    if not username:
        await websocket.send(
            json.dumps({"type": MESSAGE_ERROR, "reason": REASON_LOGIN_REQUIRED})
        )
        return

    if not room_id:
        await websocket.send(
            json.dumps({"type": MESSAGE_ERROR, "reason": REASON_ROOM_NOT_FOUND})
        )
        return

    try:
        role, seat = await server.room_manager.join_room(room_id, username, password)
        room = server.room_manager.get_room(room_id)
        server._sessions[websocket] = (seat, room_id)
        server._connections.discard(websocket)
        server._room_connections.setdefault(room_id, set()).add(websocket)
        if seat.color is not None and room.engine:
            room.engine.players[seat.color].name = seat.username
        await websocket.send(json.dumps({
            "type": MESSAGE_ROOM_JOINED,
            "payload": {
                "room_id": room_id,
                "username": seat.username,
                "role": seat.role,
                "color": seat.color,
                "elo": seat.elo,
                "snapshot": snapshot_to_dict(room.engine) if room.engine else {},
            },
        }))
        subscribe_room_events(server, room_id)
        room.event_bus.publish(MESSAGE_PLAYER_JOINED, {
            "username": seat.username,
            "role": seat.role,
            "color": seat.color,
        })
    except Exception as exc:
        await websocket.send(
            json.dumps({"type": MESSAGE_ERROR, "reason": str(exc)})
        )


async def handle_list_rooms(server, websocket, message):
    try:
        rooms = await server.room_manager.list_rooms()
        await websocket.send(json.dumps({
            "type": MESSAGE_ROOMS_LIST,
            "payload": {"rooms": rooms},
        }))
    except Exception as exc:
        await websocket.send(
            json.dumps({"type": MESSAGE_ERROR, "reason": str(exc)})
        )


async def handle_snapshot(server, websocket, message, room_id):
    engine = server.engine
    if room_id:
        room = server.room_manager.get_room(room_id)
        if room and room.engine:
            engine = room.engine
    await websocket.send(
        json.dumps({"type": MESSAGE_SNAPSHOT, "payload": snapshot_to_dict(engine)})
    )