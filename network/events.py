import asyncio
import json
import logging

from config import (
    MESSAGE_GAME_OVER,
    MESSAGE_PLAYER_LEFT,
)
from engine.game_engine import GameEngine
from model.setup import standard_starting_board
from network.elo import compute_elo
from network.event_bus import NATSEventBus
from network.serialization import snapshot_to_dict

logger = logging.getLogger(__name__)

def schedule_broadcast(server, event):
    if server._loop is None:
        return
    server._loop.call_soon_threadsafe(
        lambda: asyncio.create_task(
            broadcast_all(server, {"type": event.type, "payload": event.payload})
        )
    )

async def broadcast_all(server, message):
    if not server._connections:
        return
    encoded = json.dumps(message)
    stale = []
    for connection in list(server._connections):
        try:
            await connection.send(encoded)
        except Exception:
            stale.append(connection)
    for connection in stale:
        await server._disconnect_session(connection)

async def broadcast_room(server, room_id, message):
    connections = server._room_connections.get(room_id)
    if not connections:
        return
    encoded = json.dumps(message)
    stale = []
    for connection in list(connections):
        try:
            await connection.send(encoded)
        except Exception:
            stale.append(connection)
    for connection in stale:
        server._room_connections.get(room_id, set()).discard(connection)
        await server._disconnect_session(connection)

async def save_game_over(server, event, engine, players):
    if server.db is not None:
        try:
            await server.db.save_game_state(snapshot_to_dict(engine))
        except Exception as exc:
            logger.warning("Failed to save game state: %s", exc)
    winner_color = event.payload.get("winner_color")
    if winner_color is None or len(players) != 2:
        return
    winner = next((p for p in players if p.color == winner_color), None)
    loser = next((p for p in players if p.color != winner_color), None)
    if winner is None or loser is None:
        return
    new_winner_elo, new_loser_elo = compute_elo(winner.elo, loser.elo)
    if server.db is not None:
        try:
            await server.db.update_elos(
                winner.username, new_winner_elo, loser.username, new_loser_elo
            )
        except Exception as exc:
            logger.warning("Failed to update ELOs: %s", exc)


async def on_game_over(server, event):
    await save_game_over(server, event, server.engine, server.lobby.players())

async def room_game_over(server, room, event):
    if server.db is not None:
        try:
            await server.db.save_game_state(snapshot_to_dict(room.engine))
        except Exception as exc:
            logger.warning("Failed to save room game state: %s", exc)
    winner_color = event.payload.get("winner_color")
    if winner_color is None or len(room.player_seats) != 2:
        return
    winner = next((p for p in room.player_seats if p.color == winner_color), None)
    loser = next((p for p in room.player_seats if p.color != winner_color), None)
    if winner is None or loser is None:
        return
    new_winner_elo, new_loser_elo = compute_elo(winner.elo, loser.elo)
    if server.db is not None:
        try:
            await server.db.update_elos(
                winner.username, new_winner_elo, loser.username, new_loser_elo
            )
        except Exception as exc:
            logger.warning("Failed to update room ELOs: %s", exc)


async def create_nats_bus(server, room_id, room):
    async def _connect():
        nats_bus = NATSEventBus(server.nats_url, room_id)
        await nats_bus.connect()
        server._room_nats[room_id] = nats_bus
        if nats_bus.is_connected:
            room.event_bus = nats_bus

        def room_broadcast(event):
            if server._loop is None:
                return
            message = {
                "type": event.type,
                "payload": {**event.payload, "room_id": room_id},
            }
            server._loop.call_soon_threadsafe(
                lambda rid=room_id, msg=message: asyncio.create_task(
                    broadcast_room(server, rid, msg)
                )
            )

        room.event_bus.subscribe(room_broadcast)

    if server._loop is not None and server._loop.is_running():
        server._loop.create_task(_connect())


def subscribe_room_events(server, room_id):
    if room_id in server._subscribed_rooms:
        return
    room = server.room_manager.get_room(room_id)
    if room is None or room.event_bus is None:
        return
    server._subscribed_rooms.add(room_id)

    def room_broadcast(event):
        if server._loop is None:
            return
        message = {
            "type": event.type,
            "payload": {**event.payload, "room_id": room_id},
        }
        server._loop.call_soon_threadsafe(
            lambda rid=room_id, msg=message: asyncio.create_task(
                broadcast_room(server, rid, msg)
            )
        )

    room.event_bus.subscribe(room_broadcast)

    def room_game_over_handler(event):
        if server._loop is None:
            return
        server._loop.call_soon_threadsafe(
            lambda: asyncio.create_task(
                room_game_over(server, room, event)
            )
        )

    room.event_bus.subscribe(room_game_over_handler, MESSAGE_GAME_OVER)

    if server.nats_url is not None:
        asyncio.create_task(create_nats_bus(server, room_id, room))