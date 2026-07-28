import asyncio
import contextlib
import functools
import json
import logging

import websockets

from config import (
    MESSAGE_CREATE_ROOM,
    MESSAGE_ERROR,
    MESSAGE_GAME_OVER,
    MESSAGE_JOIN_ROOM,
    MESSAGE_LIST_ROOMS,
    MESSAGE_LOGIN,
    MESSAGE_MOVE,
    MESSAGE_SNAPSHOT,
    NATS_URL,
    NETWORK_HOST,
    NETWORK_PORT,
    PG_DSN,
    REASON_INVALID_JSON,
    REASON_LOGIN_REQUIRED,
    REASON_UNKNOWN_MESSAGE_TYPE,
    TICK_DURATION_MS,
)
from engine.game_engine import GameEngine
from model.setup import standard_starting_board
from network.db import UserDB
from network.event_bus import InMemoryEventBus
from network.events import (
    on_game_over,
    schedule_broadcast,
)
from network.handlers import (
    handle_create_room,
    handle_join_room,
    handle_list_rooms,
    handle_login,
    handle_move,
    handle_relogin,
    handle_snapshot,
)
from network.lobby import LobbyError, ShellLoginLobby
from network.serialization import engine_from_snapshot, snapshot_to_dict

logger = logging.getLogger(__name__)

class LocalWebSocketGameServer:
    def __init__(
        self,
        engine: GameEngine,
        event_bus: InMemoryEventBus,
        lobby=None,
        db=None,
        host: str = NETWORK_HOST,
        port: int = NETWORK_PORT,
        tick_duration_ms: int = TICK_DURATION_MS,
        nats_url=None,
    ):
        self.engine = engine
        self.event_bus = event_bus
        self.lobby = lobby or ShellLoginLobby()
        self.db = db
        self.nats_url = nats_url
        from network.lobby import RoomManager
        self.room_manager = RoomManager(
            db,
            engine_factory=lambda bus: GameEngine(standard_starting_board(), event_bus=bus),
        )
        self.host = host
        self.port = port
        self.tick_duration_ms = tick_duration_ms
        self._server = None
        self._loop = None
        self._tick_task = None
        self._connections = set()
        self._room_connections = {}
        self._subscribed_rooms = set()
        self._room_nats = {}
        self._sessions = {}
        self._game_started = False
        self.event_bus.subscribe(self._on_game_over_sync, MESSAGE_GAME_OVER)

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.stop()

    async def start(self):
        self._loop = asyncio.get_running_loop()
        self._server = await websockets.serve(self._handle_connection, self.host, self.port)
        self.event_bus.subscribe(functools.partial(schedule_broadcast, self))
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

    def _on_game_over_sync(self, event):
        if self._loop is None:
            return
        self._loop.call_soon_threadsafe(
            lambda: asyncio.create_task(on_game_over(self, event))
        )

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

    async def _handle_message(self, websocket, raw_message):
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

        if message_type == MESSAGE_LOGIN:
            if seat is None:
                await handle_login(self, websocket, message)
            else:
                await handle_relogin(self, websocket, seat)
            return

        if message_type == MESSAGE_CREATE_ROOM:
            if seat is not None:
                self.lobby.release(seat.username)
            await handle_create_room(self, websocket, message)
            return

        if message_type == MESSAGE_JOIN_ROOM:
            if seat is not None:
                self.lobby.release(seat.username)
            await handle_join_room(self, websocket, message)
            return

        if message_type == MESSAGE_LIST_ROOMS:
            await handle_list_rooms(self, websocket, message)
            return

        if seat is None:
            await websocket.send(
                json.dumps({"type": MESSAGE_ERROR, "reason": REASON_LOGIN_REQUIRED})
            )
            return

        if message_type == MESSAGE_MOVE:
            await handle_move(self, websocket, seat, message, room_id)
            return

        if message_type == MESSAGE_SNAPSHOT:
            await handle_snapshot(self, websocket, message, room_id)
            return

        await websocket.send(
            json.dumps({"type": MESSAGE_ERROR, "reason": REASON_UNKNOWN_MESSAGE_TYPE})
        )

    async def _disconnect_session(self, websocket):
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

        from config import (
            MESSAGE_PLAYER_LEFT,
            ROLE_OBSERVER,
        )
        from network.events import save_game_over

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
            from network.lobby import PlayerSeat
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
    nats_url = NATS_URL,
):
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