import hashlib
import os
import sqlite3
from contextlib import contextmanager
from typing import Optional

from config import DB_PATH, ELO_DEFAULT
from network.sql_query import UPDATE_USER, INSERT_GAME_STATE, GET_GAME_STATE, GET_ELO, GET_USER, INSERT_USER, \
    CREATE_GAME_STATE, CREATE_USERS, CREATE_ROOMS, INSERT_ROOM, GET_ROOM, LIST_ROOMS, UPDATE_ROOM_STATUS


class UserDBError(ValueError):
    pass

class UserDB:
    def __init__(self, db_path: str = DB_PATH):
        self._db_path = db_path
        self._init_schema()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.execute(CREATE_USERS)
            conn.execute(CREATE_GAME_STATE)
            conn.execute(CREATE_ROOMS)

    @staticmethod
    def _hash_password(password: str, salt: bytes) -> str:
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 260_000)
        return dk.hex()

    def create_user(self, username: str, password: str) -> int:
        """Register a new user. Returns their starting ELO. Raises UserDBError if taken."""
        from config import REASON_USER_EXISTS
        salt = os.urandom(32)
        pw_hash = self._hash_password(password, salt)
        try:
            with self._conn() as conn:
                conn.execute(INSERT_USER,(username, pw_hash, salt.hex(), ELO_DEFAULT),)
        except sqlite3.IntegrityError:
            raise UserDBError(REASON_USER_EXISTS)
        return ELO_DEFAULT

    def authenticate(self, username: str, password: str) -> int:
        """Verify credentials. Returns the user's current ELO. Raises UserDBError on failure."""
        from config import REASON_INVALID_CREDENTIALS
        with self._conn() as conn:
            row = conn.execute(GET_USER,(username,),).fetchone()
        if row is None:
            raise UserDBError(REASON_INVALID_CREDENTIALS)
        salt = bytes.fromhex(row["salt"])
        if self._hash_password(password, salt) != row["password_hash"]:
            raise UserDBError(REASON_INVALID_CREDENTIALS)
        return row["elo"]

    def get_elo(self, username: str) -> Optional[int]:
        with self._conn() as conn:
            row = conn.execute(GET_ELO, (username,)).fetchone()
        return row["elo"] if row else None

    def update_elos(
        self, winner_username: str, new_winner_elo: int, loser_username: str, new_loser_elo: int
    ) -> None:
        with self._conn() as conn:
            conn.execute(UPDATE_USER,(new_winner_elo, winner_username),)
            conn.execute(UPDATE_USER,(new_loser_elo, loser_username),)

    def save_game_state(self, snapshot: dict) -> None:
        import json
        game_over = int(snapshot.get("game_over", False))
        with self._conn() as conn:
            conn.execute(INSERT_GAME_STATE,(json.dumps(snapshot), game_over),)

    def load_game_state(self) -> "dict | None":
        """Returns the saved snapshot if the last game was not completed, else None."""
        import json
        with self._conn() as conn:
            try:
                row = conn.execute(GET_GAME_STATE).fetchone()
            except sqlite3.OperationalError:
                return None
        if row is None or row["game_over"]:
            return None
        return json.loads(row["snapshot"])

    def create_room(self, room_id: str, room_name: str, creator: str) -> None:
        """Create a new room. Raises UserDBError if room ID already exists."""
        try:
            with self._conn() as conn:
                conn.execute(INSERT_ROOM, (room_id, room_name, creator, "waiting"))
        except sqlite3.IntegrityError:
            raise UserDBError("Room ID already exists")

    def get_room(self, room_id: str) -> "dict | None":
        """Get room details by ID."""
        with self._conn() as conn:
            row = conn.execute(GET_ROOM, (room_id,)).fetchone()
        if row is None:
            return None
        return dict(row)

    def list_available_rooms(self) -> list:
        """Get all waiting rooms."""
        with self._conn() as conn:
            rows = conn.execute(LIST_ROOMS).fetchall()
        return [dict(row) for row in rows]

    def update_room_status(self, room_id: str, status: str) -> None:
        """Update room status (e.g., 'waiting' -> 'started' -> 'completed')."""
        with self._conn() as conn:
            conn.execute(UPDATE_ROOM_STATUS, (status, room_id))
