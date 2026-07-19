import asyncio
import contextlib
import json
from typing import Optional

import websockets

from config import TICK_DURATION_MS
from engine.game_engine import GameEngine
from model.setup import standard_starting_board
from network.event_bus import GameEvent, InMemoryEventBus
from network.lobby import LobbyError, PlayerSeat, ShellLoginLobby, OBSERVER
from network.serialization import position_from_dict, snapshot_to_dict


class LocalWebSocketGameServer:
    def __init__(
        self,
        engine: GameEngine,
        event_bus: InMemoryEventBus,
        lobby: Optional[ShellLoginLobby] = None,
        host: str = "127.0.0.1",
        port: int = 8765,
        tick_duration_ms: int = TICK_DURATION_MS,
    ):
        self.engine = engine
        self.event_bus = event_bus
        self.lobby = lobby or ShellLoginLobby()
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
            await websocket.send(json.dumps({"type": "error", "reason": "invalid_json"}))
            return

        message_type = message.get("type")
        seat = self._sessions.get(websocket)
        if seat is None:
            if message_type != "login":
                await websocket.send(json.dumps({"type": "error", "reason": "login_required"}))
                return
            await self._handle_login(websocket, message)
            return

        if message_type == "move":
            await self._handle_move(websocket, seat, message)
            return
        if message_type == "snapshot":
            await websocket.send(json.dumps({"type": "snapshot", "payload": snapshot_to_dict(self.engine)}))
            return
        await websocket.send(json.dumps({"type": "error", "reason": "unknown_message_type"}))

    async def _handle_login(self, websocket, message: dict):
        username = str(message.get("username", ""))
        try:
            seat = self.lobby.login(username)
        except LobbyError as exc:
            await websocket.send(json.dumps({"type": "error", "reason": str(exc)}))
            await websocket.close()
            return
        self._sessions[websocket] = seat
        if seat.color is not None:
            self.engine.players[seat.color].name = seat.username
        await websocket.send(json.dumps({
            "type": "login_ack",
            "payload": {
                "username": seat.username,
                "role": seat.role,
                "color": seat.color,
                "snapshot": snapshot_to_dict(self.engine),
            },
        }))
        self.event_bus.publish("player_joined", {"username": seat.username, "role": seat.role, "color": seat.color})
        if self.lobby.is_ready() and not self._game_started:
            self._game_started = True
            self.event_bus.publish("game_started", {
                "players": [
                    {"username": player.username, "role": player.role, "color": player.color}
                    for player in self.lobby.players()
                ],
                "snapshot": snapshot_to_dict(self.engine),
            })

    async def _handle_move(self, websocket, seat: PlayerSeat, message: dict):
        try:
            source = position_from_dict(message["source"])
            destination = position_from_dict(message["destination"])
        except (KeyError, TypeError, ValueError):
            await websocket.send(json.dumps({"type": "error", "reason": "invalid_move_payload"}))
            return

        if seat.role == OBSERVER:
            await websocket.send(json.dumps({"type": "move_ack", "payload": {"accepted": False, "reason": "observer_read_only"}}))
            return
        piece = self.engine.board.get_piece(source)
        if piece is None:
            await websocket.send(json.dumps({"type": "move_ack", "payload": {"accepted": False, "reason": "empty_source"}}))
            return
        if piece.color != seat.color:
            await websocket.send(json.dumps({"type": "move_ack", "payload": {"accepted": False, "reason": "wrong_player_color"}}))
            return

        result = self.engine.request_move(source, destination)
        await websocket.send(json.dumps({
            "type": "move_ack",
            "payload": {
                "accepted": result.is_accepted,
                "reason": result.reason,
            },
        }))

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
        if released.role != OBSERVER:
            self._game_started = False
        self.event_bus.publish("player_left", {
            "username": released.username,
            "role": released.role,
            "color": released.color,
        })


def create_local_server(host: str = "127.0.0.1", port: int = 8765) -> LocalWebSocketGameServer:
    event_bus = InMemoryEventBus()
    engine = GameEngine(standard_starting_board(), event_bus=event_bus)
    return LocalWebSocketGameServer(engine=engine, event_bus=event_bus, host=host, port=port)
