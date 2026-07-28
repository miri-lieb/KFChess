import asyncio
import contextlib
import json
import logging
from typing import Optional

import websockets

from config import (
    MESSAGE_ERROR,
    MESSAGE_GAME_OVER,
    MESSAGE_GAME_STARTED,
    MESSAGE_LOGIN,
    MESSAGE_LOGIN_ACK,
    MESSAGE_MOVE,
    MESSAGE_MOVE_ACK,
    MESSAGE_PLAYER_JOINED,
    MESSAGE_PLAYER_LEFT,
    MESSAGE_SNAPSHOT,
    MESSAGE_CREATE_ROOM,
    MESSAGE_JOIN_ROOM,
    MESSAGE_LIST_ROOMS,
    MESSAGE_ROOM_CREATED,
    MESSAGE_ROOM_JOINED,
    MESSAGE_ROOMS_LIST,
    NATS_URL,
    NETWORK_HOST,
    NETWORK_PORT,
    PG_DSN,
    ROLE_OBSERVER,
    REASON_EMPTY_SOURCE,
    REASON_INVALID_JSON,
    REASON_INVALID_MOVE_PAYLOAD,
    REASON_LOGIN_REQUIRED,
    REASON_OBSERVER_READ_ONLY,
    REASON_UNKNOWN_MESSAGE_TYPE,
    REASON_WRONG_PLAYER_COLOR,
    REASON_ROOM_NOT_FOUND,
    REASON_ROOM_FULL,
    REASON_INVALID_ROOM_NAME,
    TICK_DURATION_MS,
)
from engine.game_engine import GameEngine
from model.setup import standard_starting_board
from network.db import UserDB
from network.elo import compute_elo
from network.event_bus import GameEvent, InMemoryEventBus, NATSEventBus
from network.lobby import LobbyError, PlayerSeat, ShellLoginLobby, RoomManager
from network.serialization import engine_from_snapshot, position_from_dict, snapshot_to_dict

logger = logging.getLogger(__name__)


class LocalWebSocketGameServer:
    def __init__(
        self,
        engine: GameEngine,
        event_bus: InMemoryEventBus,
        lobby: Optional[ShellLoginLobby] = None,
        db: Optional[UserDB] = None,
        host: str = NETWORK_HOST,
        port: int = NETWORK_PORT,
        tick_duration_ms: int = TICK_DURATION_MS,
        nats_url: Optional[str] = None,
    ):
        self.engine = engine
        self.event_bus = event_bus
        self.lobby = lobby or ShellLoginLobby()
        self.db = db
        self.nats_url = nats_url
        self.room_manager = RoomManager(
            db,
            engine_factory=lambda bus: GameEngine(standard_starting_board(), event_bus=bus),
        )
        self.host = host
        self.port = port
        self.tick_duration_ms = tick_duration_ms
        self._server = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._tick_task: Optional[asyncio.Task] = None
        self._connections: set = set()
        self._room_connections: dict[str, set] = {}
        self._subscribed_rooms: set[str] = set()
        self._room_nats: dict[str, NATSEventBus] = {}
        self._sessions: dict[object, tuple] = {}
        self._game_started = False
        self.event_bus.subscribe(self._schedule_broadcast)
        self.event_bus.subscribe(self._on_game_over, MESSAGE_GAME_OVER)

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.stop()

    async def start(self):
        self._loop = asyncio.get_running_loop()
        self._server = await websockets.serve(self._handle_connection, self.host, self.port)
        self._tick_task = asyncio.create_task(self._tick_loop())
        return self

    async def stop(self):
        if self._tick_task is not None:
            self._tick_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._tick_task
            self._tick_task = None
        for nats_bus in self._room_nats.values():
            await nats_bus.close()
        self._room_nats.clear()
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        if self._connections:
            await asyncio.gather(
                *(connection.close() for connection in list(self._connections)),
                return_exceptions=True,
            )
        self._connections.clear()
        for conns in self._room_connections.values():
            await asyncio.gather(
                *(connection.close() for connection in list(conns)),
                return_exceptions=True,
            )
        self._room_connections.clear()
        self._sessions.clear()
        if self.db is not None:
            await self.db.close()

    def _schedule_broadcast(self, event: GameEvent) -> None:
        if self._loop is None:
            return
        self._loop.call_soon_threadsafe(
            lambda: asyncio.create_task(
                self._broadcast({"type": event.type, "payload": event.payload})
            )
        )

    async def _on_game_over(self, event: GameEvent) -> None:
        await self._save_game_over(event, self.engine, self.lobby.players())

    def _on_game_over_sync(self, event: GameEvent) -> None:
        if self._loop is None:
            return
        self._loop.call_soon_threadsafe(
            lambda: asyncio.create_task(self._on_game_over(event))
        )

    async def _save_game_over(
        self, event: GameEvent, engine: GameEngine, players: list
    ) -> None:
        if self.db is not None:
            try:
                await self.db.save_game_state(snapshot_to_dict(engine))
            except Exception as exc:
                logger.warning("Failed to save game state: %s", exc)
        winner_color = event.payload.get("winner_color")
        if winner_color is None:
            return
        if len(players) != 2:
            return
        winner = next((p for p in players if p.color == winner_color), None)
        loser = next((p for p in players if p.color != winner_color), None)
        if winner is None or loser is None:
            return
        new_winner_elo, new_loser_elo = compute_elo(winner.elo, loser.elo)
        if self.db is not None:
            try:
                await self.db.update_elos(
                    winner.username, new_winner_elo, loser.username, new_loser_elo
                )
            except Exception as exc:
                logger.warning("Failed to update ELOs: %s", exc)

    async def _broadcast(self, message: dict) -> None:
        if not self._connections:
            return
        encoded = json.dumps(message)
        stale = []
        for connection in list(self._connections):
            try:
                await connection.send(encoded)
            except Exception:
                stale.append(connection)
        for connection in stale:
            await self._disconnect_session(connection)

    def _subscribe_to_room(self, room_id: str) -> None:
        if room_id in self._subscribed_rooms:
            return
        room = self.room_manager.get_room(room_id)
        if room is None or room.event_bus is None:
            return
        self._subscribed_rooms.add(room_id)

        def room_broadcast(event: GameEvent) -> None:
            if self._loop is None:
                return
            message = {
                "type": event.type,
                "payload": {**event.payload, "room_id": room_id},
            }
            self._loop.call_soon_threadsafe(
                lambda rid=room_id, msg=message: asyncio.create_task(
                    self._broadcast_to_room(rid, msg)
                )
            )

        room.event_bus.subscribe(room_broadcast)

        def room_game_over(event: GameEvent) -> None:
            if self._loop is None:
                return
            self._loop.call_soon_threadsafe(
                lambda: asyncio.create_task(
                    self._room_game_over(room, event)
                )
            )

        room.event_bus.subscribe(room_game_over, MESSAGE_GAME_OVER)

        if self.nats_url is not None:
            self._create_nats_bus(room_id, room)

    def _create_nats_bus(self, room_id: str, room) -> None:
        async def _connect():
            nats_bus = NATSEventBus(self.nats_url, room_id)
            await nats_bus.connect()
            self._room_nats[room_id] = nats_bus
            if nats_bus.is_connected:
                room.event_bus = nats_bus
                room.event_bus.subscribe(room_broadcast)

        if self._loop is not None and self._loop.is_running():
            self._loop.create_task(_connect())

    async def _room_game_over(self, room, event: GameEvent) -> None:
        if self.db is not None:
            try:
                await self.db.save_game_state(snapshot_to_dict(room.engine))
            except Exception as exc:
                logger.warning("Failed to save room game state: %s", exc)
        winner_color = event.payload.get("winner_color")
        if winner_color is None:
            return
        if len(room.player_seats) != 2:
            return
        winner = next((p for p in room.player_seats if p.color == winner_color), None)
        loser = next((p for p in room.player_seats if p.color != winner_color), None)
        if winner is None or loser is None:
            return
        new_winner_elo, new_loser_elo = compute_elo(winner.elo, loser.elo)
        if self.db is not None:
            try:
                await self.db.update_elos(
                    winner.username, new_winner_elo, loser.username, new_loser_elo
                )
            except Exception as exc:
                logger.warning("Failed to update room ELOs: %s", exc)

    async def _broadcast_to_room(self, room_id: str, message: dict) -> None:
        connections = self._room_connections.get(room_id)
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
            self._room_connections.get(room_id, set()).discard(connection)
            await self._disconnect_session(connection)

    async def _tick_loop(self):
        while True:
            await asyncio.sleep(self.tick_duration_ms / 1000)
            self.engine.wait(self.tick_duration_ms)
            for room in list(self.room_manager._rooms.values()):
                if room.engine is not None:
                    room.engine.wait(self.tick_duration_ms)

    async def _handle_connection(self, websocket):
        self._connections.add(websocket)
        try:
            async for raw_message in websocket:
                await self._handle_message(websocket, raw_message)
        finally:
            await self._disconnect_session(websocket)

    async def _handle_message(self, websocket, raw_message: str):
        try:
            message = json.loads(raw_message)
        except json.JSONDecodeError:
            await websocket.send(
                json.dumps({"type": MESSAGE_ERROR, "reason": REASON_INVALID_JSON})
            )
            return

        message_type = str(message.get("type", "")).strip().lower()
        session = self._sessions.get(websocket)

        if session is None:
            seat = None
            room_id = None
        elif isinstance(session, tuple):
            seat, room_id = session
        else:
            seat = session
            room_id = None

        if seat is None:
            if message_type == MESSAGE_LOGIN:
                await self._handle_login(websocket, message)
                return
            if message_type == MESSAGE_CREATE_ROOM:
                await self._handle_create_room(websocket, message)
                return
            if message_type == MESSAGE_JOIN_ROOM:
                await self._handle_join_room(websocket, message)
                return
            if message_type == MESSAGE_LIST_ROOMS:
                await self._handle_list_rooms(websocket, message)
                return
            await websocket.send(
                json.dumps({"type": MESSAGE_ERROR, "reason": REASON_LOGIN_REQUIRED})
            )
            return

        if message_type == MESSAGE_MOVE:
            await self._handle_move(websocket, seat, message, room_id)
            return
        if message_type == MESSAGE_SNAPSHOT:
            engine = self.engine
            if room_id:
                room = self.room_manager.get_room(room_id)
                if room and room.engine:
                    engine = room.engine
            await websocket.send(
                json.dumps({"type": MESSAGE_SNAPSHOT, "payload": snapshot_to_dict(engine)})
            )
            return
        await websocket.send(
            json.dumps({"type": MESSAGE_ERROR, "reason": REASON_UNKNOWN_MESSAGE_TYPE})
        )

    async def _handle_login(self, websocket, message: dict):
        username = str(message.get("username", ""))
        password = str(message.get("password", ""))
        register = bool(message.get("register", False))
        try:
            if register:
                seat = await self.lobby.register(username, password)
            else:
                seat = await self.lobby.login(username, password)
        except LobbyError as exc:
            await websocket.send(
                json.dumps({"type": MESSAGE_ERROR, "reason": str(exc)})
            )
            await websocket.close()
            return
        self._sessions[websocket] = seat
        if seat.color is not None:
            self.engine.players[seat.color].name = seat.username
        await websocket.send(json.dumps({
            "type": MESSAGE_LOGIN_ACK,
            "payload": {
                "username": seat.username,
                "role": seat.role,
                "color": seat.color,
                "elo": seat.elo,
                "snapshot": snapshot_to_dict(self.engine),
            },
        }))
        self.event_bus.publish(
            MESSAGE_PLAYER_JOINED,
            {"username": seat.username, "role": seat.role, "color": seat.color},
        )
        if self.lobby.is_ready() and not self._game_started:
            self._game_started = True
            self.event_bus.publish(MESSAGE_GAME_STARTED, {
                "players": [
                    {
                        "username": player.username,
                        "role": player.role,
                        "color": player.color,
                        "elo": player.elo,
                    }
                    for player in self.lobby.players()
                ],
                "snapshot": snapshot_to_dict(self.engine),
            })

    async def _handle_move(
        self,
        websocket,
        seat: PlayerSeat,
        message: dict,
        room_id: Optional[str] = None,
    ):
        try:
            source = position_from_dict(message["source"])
            destination = position_from_dict(message["destination"])
        except (KeyError, TypeError, ValueError):
            await websocket.send(
                json.dumps(
                    {"type": MESSAGE_ERROR, "reason": REASON_INVALID_MOVE_PAYLOAD}
                )
            )
            return

        engine = self.engine
        if room_id:
            room = self.room_manager.get_room(room_id)
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

    async def _handle_create_room(self, websocket, message: dict):
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
            room_id = await self.room_manager.create_room(room_name, username)
            role, seat = await self.room_manager.join_room(room_id, username, password)
            room = self.room_manager.get_room(room_id)
            self._sessions[websocket] = (seat, room_id)
            self._connections.discard(websocket)
            self._room_connections.setdefault(room_id, set()).add(websocket)
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
            self._subscribe_to_room(room_id)
            room.event_bus.publish(MESSAGE_PLAYER_JOINED, {
                "username": seat.username,
                "role": seat.role,
                "color": seat.color,
            })
        except Exception as exc:
            await websocket.send(
                json.dumps({"type": MESSAGE_ERROR, "reason": str(exc)})
            )

    async def _handle_join_room(self, websocket, message: dict):
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
            role, seat = await self.room_manager.join_room(room_id, username, password)
            room = self.room_manager.get_room(room_id)
            self._sessions[websocket] = (seat, room_id)
            self._connections.discard(websocket)
            self._room_connections.setdefault(room_id, set()).add(websocket)
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
            self._subscribe_to_room(room_id)
            room.event_bus.publish(MESSAGE_PLAYER_JOINED, {
                "username": seat.username,
                "role": seat.role,
                "color": seat.color,
            })
        except Exception as exc:
            await websocket.send(
                json.dumps({"type": MESSAGE_ERROR, "reason": str(exc)})
            )

    async def _handle_list_rooms(self, websocket, message: dict):
        try:
            rooms = await self.room_manager.list_rooms()
            await websocket.send(json.dumps({
                "type": MESSAGE_ROOMS_LIST,
                "payload": {"rooms": rooms},
            }))
        except Exception as exc:
            await websocket.send(
                json.dumps({"type": MESSAGE_ERROR, "reason": str(exc)})
            )

    async def _disconnect_session(self, websocket) -> None:
        self._connections.discard(websocket)
        session = self._sessions.pop(websocket, None)
        if session is None:
            return
        if isinstance(session, tuple):
            seat, room_id = session
            room_conns = self._room_connections.get(room_id)
            if room_conns is not None:
                room_conns.discard(websocket)
        else:
            seat = session
            room_id = None

        if room_id is not None:
            room = self.room_manager.get_room(room_id)
            if room is not None:
                if room.engine is not None and seat.color is not None:
                    room.engine.players[seat.color].name = None
                if seat.role != ROLE_OBSERVER and room.engine is not None:
                    if self.db is not None and not room.engine.game_over:
                        try:
                            await self.db.save_game_state(snapshot_to_dict(room.engine))
                        except Exception as exc:
                            logger.warning("Failed to save game state on disconnect: %s", exc)
            await self.room_manager.leave_room(seat.username)
            if room is not None:
                room.event_bus.publish(MESSAGE_PLAYER_LEFT, {
                    "username": seat.username,
                    "role": seat.role,
                    "color": seat.color,
                })
        else:
            released = self.lobby.release(seat.username)
            if released is None:
                return
            if released.color is not None:
                self.engine.players[released.color].name = None
            if released.role != ROLE_OBSERVER:
                self._game_started = False
                if self.db is not None and not self.engine.game_over:
                    try:
                        await self.db.save_game_state(snapshot_to_dict(self.engine))
                    except Exception as exc:
                        logger.warning("Failed to save game state on disconnect: %s", exc)
                if self.engine.game_over and not self.lobby.players():
                    self.engine = GameEngine(
                        standard_starting_board(), event_bus=self.event_bus
                    )
            self.event_bus.publish(MESSAGE_PLAYER_LEFT, {
                "username": released.username,
                "role": released.role,
                "color": released.color,
            })


async def create_local_server(
    host: str = NETWORK_HOST,
    port: int = NETWORK_PORT,
    nats_url: Optional[str] = NATS_URL,
) -> LocalWebSocketGameServer:
    event_bus = InMemoryEventBus()
    db = UserDB(PG_DSN)
    await db.initialize()

    saved = await db.load_game_state()
    if saved is not None:
        logger.info("Restoring interrupted game state...")
        engine = engine_from_snapshot(saved, event_bus=event_bus)
    else:
        engine = GameEngine(standard_starting_board(), event_bus=event_bus)
    lobby = ShellLoginLobby(db=db)
    return LocalWebSocketGameServer(
        engine=engine,
        event_bus=event_bus,
        lobby=lobby,
        db=db,
        host=host,
        port=port,
        nats_url=nats_url,
    )
