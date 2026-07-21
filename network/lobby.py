import unicodedata
import uuid
from dataclasses import dataclass
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

OBSERVER = ROLE_OBSERVER

class LobbyError(ValueError):
    pass

@dataclass(frozen=True)
class PlayerSeat:
    username: str
    role: str
    color: Optional[str]
    elo: int = 1200

@dataclass(frozen=True)
class Room:
    room_id: str
    name: str
    creator: str
    player_seats: list
    observer_seats: list

class ShellLoginLobby:
    def __init__(self, db: Optional[UserDB] = None):
        self._db = db
        self._seats_by_username: dict[str, PlayerSeat] = {}
        self._player_seats: list[PlayerSeat] = []
        self._observer_seats: list[PlayerSeat] = []

    def login(self, username: str, password: str = "") -> PlayerSeat:
        normalized = self._normalize_username(username)
        if not normalized:
            raise LobbyError(REASON_USERNAME_REQUIRED)
        existing = self._seats_by_username.get(normalized)
        if existing is not None:
            return existing
        elo = 1200
        if self._db is not None:
            try:
                elo = self._db.authenticate(normalized, password)
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

    def register(self, username: str, password: str) -> PlayerSeat:
        """Register a new user and log them in."""
        normalized = self._normalize_username(username)
        if not normalized:
            raise LobbyError(REASON_USERNAME_REQUIRED)
        if self._db is None:
            raise LobbyError("Registration requires a database.")
        try:
            self._db.create_user(normalized, password)
        except UserDBError as exc:
            raise LobbyError(str(exc))
        return self.login(normalized, password)

    def seat_for(self, username: str) -> Optional[PlayerSeat]:
        return self._seats_by_username.get(self._normalize_username(username))

    def release(self, username: str) -> Optional[PlayerSeat]:
        normalized = self._normalize_username(username)
        seat = self._seats_by_username.pop(normalized, None)
        if seat is None:
            return None
        if seat.role == OBSERVER:
            self._observer_seats = [existing for existing in self._observer_seats if existing.username != seat.username]
        else:
            self._player_seats = [existing for existing in self._player_seats if existing.username != seat.username]
        return seat

    def is_ready(self) -> bool:
        return len(self._player_seats) == 2

    def players(self) -> list[PlayerSeat]:
        return list(self._player_seats)

    def observers(self) -> list[PlayerSeat]:
        return list(self._observer_seats)

    def _normalize_username(self, username: str) -> str:
        cleaned = username.encode("utf-8", errors="ignore").decode("utf-8")
        cleaned = "".join(ch for ch in cleaned if ch.isprintable())
        return unicodedata.normalize("NFKC", cleaned).strip()

class RoomManager:
    """Manages multiple rooms, each with their own player/observer seats."""

    def __init__(self, db: Optional[UserDB] = None):
        self._db = db
        self._rooms: dict[str, Room] = {}
        self._user_to_room: dict[str, str] = {}  # username -> room_id mapping

    def create_room(self, name: str, creator: str) -> str:
        """Create a new room and return its ID."""
        from config import REASON_INVALID_ROOM_NAME
        
        normalized_name = name.strip()
        if not normalized_name or len(normalized_name) > 100:
            raise LobbyError(REASON_INVALID_ROOM_NAME)
        
        room_id = self._generate_room_id()
        room = Room(
            room_id=room_id,
            name=normalized_name,
            creator=creator,
            player_seats=[],
            observer_seats=[]
        )
        self._rooms[room_id] = room
        
        if self._db:
            self._db.create_room(room_id, normalized_name, creator)
        
        return room_id

    def join_room(self, room_id: str, username: str, password: str = "") -> tuple[str, Optional[PlayerSeat]]:
        """Join a room. Returns (role, seat). Raises LobbyError if room not found or full."""
        from config import ROLE_BLACK, ROLE_WHITE, ROLE_OBSERVER, REASON_ROOM_NOT_FOUND, REASON_ROOM_FULL
        
        if room_id not in self._rooms:
            if self._db:
                room_data = self._db.get_room(room_id)
                if not room_data:
                    raise LobbyError(REASON_ROOM_NOT_FOUND)
                # Load room from DB if it exists but not in memory
                room = Room(
                    room_id=room_data["id"],
                    name=room_data["name"],
                    creator=room_data["creator"],
                    player_seats=[],
                    observer_seats=[]
                )
                self._rooms[room_id] = room
            else:
                raise LobbyError(REASON_ROOM_NOT_FOUND)
        
        room = self._rooms[room_id]
        
        # Get user ELO if DB available and password provided
        elo = 1200
        if self._db and password:
            try:
                elo = self._db.authenticate(username, password)
            except UserDBError:
                # Allow joining without auth if password not provided
                pass
        
        # Assign role based on seats
        if len(room.player_seats) < 2:
            color = WHITE if not room.player_seats else BLACK
            role = ROLE_WHITE if not room.player_seats else ROLE_BLACK
            seat = PlayerSeat(username=username, role=role, color=color, elo=elo)
            room.player_seats.append(seat)
        elif len(room.observer_seats) < 10:  # Max 10 observers per room
            seat = PlayerSeat(username=username, role=ROLE_OBSERVER, color=None, elo=elo)
            room.observer_seats.append(seat)
        else:
            raise LobbyError(REASON_ROOM_FULL)
        
        self._user_to_room[username] = room_id
        return (seat.role, seat)

    def get_room(self, room_id: str) -> Optional[Room]:
        """Get a room by ID."""
        return self._rooms.get(room_id)

    def get_room_for_user(self, username: str) -> Optional[Room]:
        """Get the room a user is currently in."""
        room_id = self._user_to_room.get(username)
        if room_id:
            return self._rooms.get(room_id)
        return None

    def list_rooms(self) -> list[dict]:
        """List all active rooms."""
        if self._db:
            return self._db.list_available_rooms()
        
        rooms_list = []
        for room in self._rooms.values():
            rooms_list.append({
                "id": room.room_id,
                "name": room.name,
                "creator": room.creator,
                "players": len(room.player_seats),
                "observers": len(room.observer_seats)
            })
        return rooms_list

    def leave_room(self, username: str) -> Optional[Room]:
        """Remove user from their current room."""
        room_id = self._user_to_room.pop(username, None)
        if not room_id:
            return None
        
        room = self._rooms.get(room_id)
        if room:
            # Remove from player or observer list
            room.player_seats = [s for s in room.player_seats if s.username != username]
            room.observer_seats = [s for s in room.observer_seats if s.username != username]
            
            # Delete room if empty
            if not room.player_seats and not room.observer_seats:
                del self._rooms[room_id]
                if self._db:
                    self._db.update_room_status(room_id, "deleted")
        
        return room

    def _generate_room_id(self) -> str:
        """Generate a unique 6-character room ID."""
        while True:
            room_id = uuid.uuid4().hex[:6].upper()
            if room_id not in self._rooms:
                return room_id
