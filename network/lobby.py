import unicodedata
from dataclasses import dataclass
from typing import Callable, Optional

from model.piece import BLACK, WHITE

OBSERVER = "observer"

class LobbyError(ValueError):
    pass


@dataclass(frozen=True)
class PlayerSeat:
    username: str
    role: str
    color: Optional[str]


class ShellLoginLobby:
    def __init__(self):
        self._seats_by_username: dict[str, PlayerSeat] = {}
        self._player_seats: list[PlayerSeat] = []
        self._observer_seats: list[PlayerSeat] = []

    def login(self, username: str) -> PlayerSeat:
        normalized = self._normalize_username(username)
        if not normalized:
            raise LobbyError("username_required")
        existing = self._seats_by_username.get(normalized)
        if existing is not None:
            return existing
        if len(self._player_seats) < 2:
            color = WHITE if not self._player_seats else BLACK
            seat = PlayerSeat(username=normalized, role=color, color=color)
            self._player_seats.append(seat)
        else:
            seat = PlayerSeat(username=normalized, role=OBSERVER, color=None)
            self._observer_seats.append(seat)
        self._seats_by_username[normalized] = seat
        return seat

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

    def prompt_for_login(
        self,
        input_fn: Callable[[str], str] = input,
        output_fn: Callable[[str], None] = print,
    ) -> PlayerSeat:
        while True:
            username = input_fn("Username: ")
            try:
                seat = self.login(username)
            except LobbyError as exc:
                message = "Username is required." if str(exc) == "username_required" else "Login failed."
                output_fn(message)
                continue
            output_fn(f"{seat.username} joined as {seat.role}.")
            return seat

    def _normalize_username(self, username: str) -> str:
        cleaned = username.encode("utf-8", errors="ignore").decode("utf-8")
        cleaned = "".join(ch for ch in cleaned if ch.isprintable())
        return unicodedata.normalize("NFKC", cleaned).strip()
