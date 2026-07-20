import unicodedata
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

