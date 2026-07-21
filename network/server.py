import asyncio
import contextlib
import json
from typing import Optional

import websockets

from config import (
    DB_PATH,
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
    NETWORK_HOST,
    NETWORK_PORT,
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
from network.event_bus import GameEvent, InMemoryEventBus
from network.lobby import LobbyError, PlayerSeat, ShellLoginLobby, RoomManager
from network.serialization import engine_from_snapshot, position_from_dict, snapshot_to_dict

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
    ):
        self.engine = engine
        self.event_bus = event_bus
        self.lobby = lobby or ShellLoginLobby()
        self.db = db
        self.room_manager = RoomManager(db)
        self.host = host
        self.port = port
        self.tick_duration_ms = tick_duration_ms
        self._server = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._tick_task: Optional[asyncio.Task] = None
        self._connections = set()
        self._sessions: dict[object, PlayerSeat] = {}
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
        self._sessions.clear()

    def _schedule_broadcast(self, event: GameEvent) -> None:
        if self._loop is None:
            return
        self._loop.call_soon_threadsafe(
            lambda: asyncio.create_task(self._broadcast({
                "type": event.type,
                "payload": event.payload,
            }))
        )

    def _on_game_over(self, event: GameEvent) -> None:
        """Update ELO ratings when the game ends and save completed state."""
        if self.db is not None:
            self.db.save_game_state(snapshot_to_dict(self.engine))
        if self.db is None:
            return
        winner_color = event.payload.get("winner_color")
        if winner_color is None:
            return
        players = self.lobby.players()
        if len(players) != 2:
            return
        winner = next((p for p in players if p.color == winner_color), None)
        loser = next((p for p in players if p.color != winner_color), None)
        if winner is None or loser is None:
            return
        new_winner_elo, new_loser_elo = compute_elo(winner.elo, loser.elo)
        self.db.update_elos(winner.username, new_winner_elo, loser.username, new_loser_elo)

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
            self._disconnect_session(connection)

    async def _tick_loop(self):
        while True:
            await asyncio.sleep(self.tick_duration_ms / 1000)
            self.engine.wait(self.tick_duration_ms)

    async def _handle_connection(self, websocket):
        self._connections.add(websocket)
        try:
            async for raw_message in websocket:
                await self._handle_message(websocket, raw_message)
        finally:
            self._disconnect_session(websocket)

    async def _handle_message(self, websocket, raw_message: str):
        try:
            message = json.loads(raw_message)
        except json.JSONDecodeError:
            await websocket.send(json.dumps({"type": MESSAGE_ERROR, "reason": REASON_INVALID_JSON}))
            return

        message_type = str(message.get("type", "")).strip().lower()
        seat = self._sessions.get(websocket)
        
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
            await websocket.send(json.dumps({"type": MESSAGE_ERROR, "reason": REASON_LOGIN_REQUIRED}))
            return

        if message_type == MESSAGE_MOVE:
            await self._handle_move(websocket, seat, message)
            return
        if message_type == MESSAGE_SNAPSHOT:
            await websocket.send(json.dumps({"type": MESSAGE_SNAPSHOT, "payload": snapshot_to_dict(self.engine)}))
            return
        await websocket.send(json.dumps({"type": MESSAGE_ERROR, "reason": REASON_UNKNOWN_MESSAGE_TYPE}))

    async def _handle_login(self, websocket, message: dict):
        username = str(message.get("username", ""))
        password = str(message.get("password", ""))
        register = bool(message.get("register", False))
        try:
            if register:
                seat = self.lobby.register(username, password)
            else:
                seat = self.lobby.login(username, password)
        except LobbyError as exc:
            await websocket.send(json.dumps({"type": MESSAGE_ERROR, "reason": str(exc)}))
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
        self.event_bus.publish(MESSAGE_PLAYER_JOINED, {"username": seat.username, "role": seat.role, "color": seat.color})
        if self.lobby.is_ready() and not self._game_started:
            self._game_started = True
            self.event_bus.publish(MESSAGE_GAME_STARTED, {
                "players": [
                    {"username": player.username, "role": player.role, "color": player.color, "elo": player.elo}
                    for player in self.lobby.players()
                ],
                "snapshot": snapshot_to_dict(self.engine),
            })

    async def _handle_move(self, websocket, seat: PlayerSeat, message: dict):
        try:
            source = position_from_dict(message["source"])
            destination = position_from_dict(message["destination"])
        except (KeyError, TypeError, ValueError):
            await websocket.send(json.dumps({"type": MESSAGE_ERROR, "reason": REASON_INVALID_MOVE_PAYLOAD}))
            return

        if seat.role == ROLE_OBSERVER:
            await websocket.send(json.dumps({"type": MESSAGE_MOVE_ACK, "payload": {"accepted": False, "reason": REASON_OBSERVER_READ_ONLY}}))
            return
        piece = self.engine.board.get_piece(source)
        if piece is None:
            await websocket.send(json.dumps({"type": MESSAGE_MOVE_ACK, "payload": {"accepted": False, "reason": REASON_EMPTY_SOURCE}}))
            return
        if piece.color != seat.color:
            await websocket.send(json.dumps({"type": MESSAGE_MOVE_ACK, "payload": {"accepted": False, "reason": REASON_WRONG_PLAYER_COLOR}}))
            return

        result = self.engine.request_move(source, destination)
        await websocket.send(json.dumps({
            "type": MESSAGE_MOVE_ACK,
            "payload": {
                "accepted": result.is_accepted,
                "reason": result.reason,
            },
        }))

    async def _handle_create_room(self, websocket, message: dict):
        """Handle room creation request."""
        username = str(message.get("username", "")).strip()
        room_name = str(message.get("room_name", "")).strip()
        
        if not username:
            await websocket.send(json.dumps({"type": MESSAGE_ERROR, "reason": REASON_LOGIN_REQUIRED}))
            return
        
        if not room_name or len(room_name) > 100:
            await websocket.send(json.dumps({"type": MESSAGE_ERROR, "reason": REASON_INVALID_ROOM_NAME}))
            return
        
        try:
            room_id = self.room_manager.create_room(room_name, username)
            await websocket.send(json.dumps({
                "type": MESSAGE_ROOM_CREATED,
                "payload": {
                    "room_id": room_id,
                    "room_name": room_name,
                }
            }))
        except Exception as exc:
            await websocket.send(json.dumps({"type": MESSAGE_ERROR, "reason": str(exc)}))

    async def _handle_join_room(self, websocket, message: dict):
        """Handle room join request."""
        username = str(message.get("username", "")).strip()
        password = str(message.get("password", ""))
        room_id = str(message.get("room_id", "")).strip().upper()
        
        if not username:
            await websocket.send(json.dumps({"type": MESSAGE_ERROR, "reason": REASON_LOGIN_REQUIRED}))
            return
        
        if not room_id:
            await websocket.send(json.dumps({"type": MESSAGE_ERROR, "reason": REASON_ROOM_NOT_FOUND}))
            return
        
        try:
            role, seat = self.room_manager.join_room(room_id, username, password)
            self._sessions[websocket] = seat
            if seat.color is not None:
                self.engine.players[seat.color].name = seat.username
            await websocket.send(json.dumps({
                "type": MESSAGE_ROOM_JOINED,
                "payload": {
                    "room_id": room_id,
                    "username": seat.username,
                    "role": seat.role,
                    "color": seat.color,
                    "elo": seat.elo,
                    "snapshot": snapshot_to_dict(self.engine),
                }
            }))
            self.event_bus.publish(MESSAGE_PLAYER_JOINED, {
                "username": seat.username,
                "role": seat.role,
                "color": seat.color,
            })
        except Exception as exc:
            await websocket.send(json.dumps({"type": MESSAGE_ERROR, "reason": str(exc)}))

    async def _handle_list_rooms(self, websocket, message: dict):
        """List available rooms."""
        try:
            rooms = self.room_manager.list_rooms()
            await websocket.send(json.dumps({
                "type": MESSAGE_ROOMS_LIST,
                "payload": {
                    "rooms": rooms,
                }
            }))
        except Exception as exc:
            await websocket.send(json.dumps({"type": MESSAGE_ERROR, "reason": str(exc)}))

    def _disconnect_session(self, websocket) -> None:
        self._connections.discard(websocket)
        seat = self._sessions.pop(websocket, None)
        if seat is None:
            return
        released = self.lobby.release(seat.username)
        if released is None:
            return
        if released.color is not None:
            self.engine.players[released.color].name = None
        if released.role != ROLE_OBSERVER:
            self._game_started = False
            if self.db is not None and not self.engine.game_over:
                self.db.save_game_state(snapshot_to_dict(self.engine))
            # Reset engine once both players have left after a completed game
            if self.engine.game_over and not self.lobby.players():
                self.engine = GameEngine(standard_starting_board(), event_bus=self.event_bus)
        self.event_bus.publish(MESSAGE_PLAYER_LEFT, {
            "username": released.username,
            "role": released.role,
            "color": released.color,
        })


def create_local_server(host: str = NETWORK_HOST, port: int = NETWORK_PORT) -> LocalWebSocketGameServer:
    event_bus = InMemoryEventBus()
    db = UserDB(DB_PATH)
    saved = db.load_game_state()
    if saved is not None:
        print("Restoring interrupted game state...")
        engine = engine_from_snapshot(saved, event_bus=event_bus)
    else:
        engine = GameEngine(standard_starting_board(), event_bus=event_bus)
    lobby = ShellLoginLobby(db=db)
    return LocalWebSocketGameServer(engine=engine, event_bus=event_bus, lobby=lobby, db=db, host=host, port=port)

