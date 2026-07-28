import logging
import unicodedata
import uuid
from dataclasses import dataclass, field
from typing import Callable, Optional

from config import (
    ROLE_BLACK,
    ROLE_OBSERVER,
    ROLE_WHITE,
    REASON_USERNAME_REQUIRED,
    USERNAME_PROMPT,
)
from model.piece import BLACK, WHITE
from network.db import UserDB, UserDBError
from network.event_bus import InMemoryEventBus

logger = logging.getLogger(__name__)

OBSERVER = ROLE_OBSERVER

class LobbyError(ValueError):
    pass

@dataclass(frozen=True)
class PlayerSeat:
    username: str
    role: str
    color: Optional[str]
    elo: int = 1200

@dataclass
class Room:
    room_id: str
    name: str
    creator: str
    player_seats: list
    observer_seats: list
    engine: any = None
    event_bus: InMemoryEventBus = field(default_factory=InMemoryEventBus)


class ShellLoginLobby:
    def __init__(self, db: Optional[UserDB] = None):
        self._db = db
        self._seats_by_username: dict[str, PlayerSeat] = {}
        self._player_seats: list[PlayerSeat] = []
        self._observer_seats: list[PlayerSeat] = []

    async def login(self, username: str, password: str = "") -> PlayerSeat:
        normalized = self._normalize_username(username)
        if not normalized:
            raise LobbyError(REASON_USERNAME_REQUIRED)
        existing = self._seats_by_username.get(normalized)
        if existing is not None:
            return existing
        elo = 1200
        if self._db is not None:
            try:
                elo = await self._db.authenticate(normalized, password)
            except UserDBError as exc:
                raise LobbyError(str(exc))
        if len(self._player_seats) < 2:
            color = WHITE if not self._player_seats else BLACK
            role = ROLE_WHITE if not self._player_seats else ROLE_BLACK
            seat = PlayerSeat(username=normalized, role=role, color=color, elo=elo)
            self._player_seats.append(seat)
        else:
            seat = PlayerSeat(username=normalized, role=ROLE_OBSERVER, color=None, elo=elo)
            self._observer_seats.append(seat)
        self._seats_by_username[normalized] = seat
        return seat

    async def register(self, username: str, password: str) -> PlayerSeat:
        normalized = self._normalize_username(username)
        if not normalized:
            raise LobbyError(REASON_USERNAME_REQUIRED)
        if self._db is None:
            raise LobbyError("Registration requires a database.")
        try:
            await self._db.create_user(normalized, password)
        except UserDBError as exc:
            raise LobbyError(str(exc))
        return await self.login(normalized, password)

    def seat_for(self, username: str) -> Optional[PlayerSeat]:
        return self._seats_by_username.get(self._normalize_username(username))

    def release(self, username: str) -> Optional[PlayerSeat]:
        normalized = self._normalize_username(username)
        seat = self._seats_by_username.pop(normalized, None)
        if seat is None:
            return None
        if seat.role == OBSERVER:
            self._observer_seats = [
                existing for existing in self._observer_seats if existing.username != seat.username
            ]
        else:
            self._player_seats = [
                existing for existing in self._player_seats if existing.username != seat.username
            ]
        return seat

    def is_ready(self) -> bool:
        return len(self._player_seats) == 2

    def players(self) -> list[PlayerSeat]:
        return list(self._player_seats)

    def observers(self) -> list[PlayerSeat]:
        return list(self._observer_seats)

    def _normalize_username(self, username: str) -> str:
        cleaned = username.encode("utf-8", errors="surrogateescape").decode("utf-8", errors="ignore")
        cleaned = "".join(ch for ch in cleaned if ch.isprintable() and not ("\ud800" <= ch <= "\udfff"))
        return unicodedata.normalize("NFKC", cleaned).strip()


class RoomManager:
    def __init__(self, db: Optional[UserDB] = None, engine_factory=None):
        self._db = db
        self._rooms: dict[str, Room] = {}
        self._user_to_room: dict[str, str] = {}
        self._engine_factory = engine_factory

    async def create_room(self, name: str, creator: str) -> str:
        from config import REASON_INVALID_ROOM_NAME

        normalized_name = name.strip()
        if not normalized_name or len(normalized_name) > 100:
            raise LobbyError(REASON_INVALID_ROOM_NAME)

        room_id = self._generate_room_id()

        room_bus = InMemoryEventBus()
        engine = self._engine_factory(room_bus) if self._engine_factory else None

        room = Room(
            room_id=room_id,
            name=normalized_name,
            creator=creator,
            player_seats=[],
            observer_seats=[],
            engine=engine,
            event_bus=room_bus,
        )
        self._rooms[room_id] = room

        if self._db is not None:
            try:
                await self._db.create_room(room_id, normalized_name, creator)
            except Exception as exc:
                logger.warning("Failed to persist room %s: %s", room_id, exc)

        return room_id

    async def join_room(self, room_id: str, username: str, password: str = "") -> tuple[str, Optional[PlayerSeat]]:
        from config import ROLE_BLACK, ROLE_WHITE, ROLE_OBSERVER, REASON_ROOM_NOT_FOUND, REASON_ROOM_FULL

        if room_id not in self._rooms:
            if self._db is not None:
                try:
                    room_data = await self._db.get_room(room_id)
                except Exception as exc:
                    logger.warning("Failed to fetch room %s from DB: %s", room_id, exc)
                    room_data = None
                if not room_data:
                    raise LobbyError(REASON_ROOM_NOT_FOUND)
                room_bus = InMemoryEventBus()
                engine = self._engine_factory(room_bus) if self._engine_factory else None
                room = Room(
                    room_id=room_data["id"],
                    name=room_data["name"],
                    creator=room_data["creator"],
                    player_seats=[],
                    observer_seats=[],
                    engine=engine,
                    event_bus=room_bus,
                )
                self._rooms[room_id] = room
            else:
                raise LobbyError(REASON_ROOM_NOT_FOUND)

        room = self._rooms[room_id]

        elo = 1200
        if self._db is not None and password:
            try:
                elo = await self._db.authenticate(username, password)
            except UserDBError:
                pass

        if len(room.player_seats) < 2:
            color = WHITE if not room.player_seats else BLACK
            role = ROLE_WHITE if not room.player_seats else ROLE_BLACK
            seat = PlayerSeat(username=username, role=role, color=color, elo=elo)
            room.player_seats.append(seat)
        elif len(room.observer_seats) < 10:
            seat = PlayerSeat(username=username, role=ROLE_OBSERVER, color=None, elo=elo)
            room.observer_seats.append(seat)
        else:
            raise LobbyError(REASON_ROOM_FULL)

        self._user_to_room[username] = room_id
        return (seat.role, seat)

    def get_room(self, room_id: str) -> Optional[Room]:
        return self._rooms.get(room_id)

    def get_room_for_user(self, username: str) -> Optional[Room]:
        room_id = self._user_to_room.get(username)
        if room_id:
            return self._rooms.get(room_id)
        return None

    async def list_rooms(self) -> list[dict]:
        if self._db is not None:
            try:
                return await self._db.list_available_rooms()
            except Exception as exc:
                logger.warning("Failed to list rooms from DB: %s", exc)

        rooms_list = []
        for room in self._rooms.values():
            rooms_list.append({
                "id": room.room_id,
                "name": room.name,
                "creator": room.creator,
                "players": len(room.player_seats),
                "observers": len(room.observer_seats),
            })
        return rooms_list

    async def leave_room(self, username: str) -> Optional[Room]:
        room_id = self._user_to_room.pop(username, None)
        if not room_id:
            return None

        room = self._rooms.get(room_id)
        if room:
            room.player_seats = [s for s in room.player_seats if s.username != username]
            room.observer_seats = [s for s in room.observer_seats if s.username != username]

            if not room.player_seats and not room.observer_seats:
                del self._rooms[room_id]
                if self._db is not None:
                    try:
                        await self._db.update_room_status(room_id, "deleted")
                    except Exception as exc:
                        logger.warning("Failed to update room %s status: %s", room_id, exc)
        return room

    def _generate_room_id(self) -> str:
        while True:
            room_id = uuid.uuid4().hex[:6].upper()
            if room_id not in self._rooms:
                return room_id