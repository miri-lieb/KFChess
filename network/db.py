import hashlib
import logging
import os
from typing import Optional

import asyncpg

from config import ELO_DEFAULT, PG_DSN
from network.sql_query import (
    CREATE_GAME_STATE,
    CREATE_ROOMS,
    CREATE_USERS,
    GET_ELO,
    GET_GAME_STATE,
    GET_USER,
    INSERT_GAME_STATE,
    INSERT_ROOM,
    INSERT_USER,
    LIST_ROOMS,
    UPDATE_ROOM_STATUS,
    UPDATE_USER,
)

logger = logging.getLogger(__name__)


class UserDBError(ValueError):
    pass


class UserDB:
    def __init__(self, dsn: str = PG_DSN):
        self._dsn = dsn
        self._pool: Optional[asyncpg.Pool] = None

    async def initialize(self) -> None:
        try:
            self._pool = await asyncpg.create_pool(self._dsn, min_size=2, max_size=10)
            async with self._pool.acquire() as conn:
                await conn.execute(CREATE_USERS)
                await conn.execute(CREATE_GAME_STATE)
                await conn.execute(CREATE_ROOMS)
            logger.info("PostgreSQL connected: %s", self._dsn.split("@")[-1])
        except Exception as exc:
            logger.warning("PostgreSQL unavailable, running without persistence: %s", exc)
            self._pool = None

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    @staticmethod
    def _hash_password(password: str, salt: bytes) -> str:
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 260_000)
        return dk.hex()

    async def create_user(self, username: str, password: str) -> int:
        from config import REASON_USER_EXISTS, ELO_DEFAULT

        if self._pool is None:
            return ELO_DEFAULT
        salt = os.urandom(32)
        pw_hash = self._hash_password(password, salt)
        try:
            async with self._pool.acquire() as conn:
                await conn.execute(INSERT_USER, username, pw_hash, salt.hex(), ELO_DEFAULT)
        except asyncpg.UniqueViolationError:
            raise UserDBError(REASON_USER_EXISTS)
        return ELO_DEFAULT

    async def authenticate(self, username: str, password: str) -> int:
        from config import ELO_DEFAULT, REASON_INVALID_CREDENTIALS

        if self._pool is None:
            return ELO_DEFAULT
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(GET_USER, username)
        if row is None:
            raise UserDBError(REASON_INVALID_CREDENTIALS)
        salt = bytes.fromhex(row["salt"])
        if self._hash_password(password, salt) != row["password_hash"]:
            raise UserDBError(REASON_INVALID_CREDENTIALS)
        return row["elo"]

    async def get_elo(self, username: str) -> Optional[int]:
        if self._pool is None:
            return None
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(GET_ELO, username)
        return row["elo"] if row else None

    async def update_elos(
        self,
        winner_username: str,
        new_winner_elo: int,
        loser_username: str,
        new_loser_elo: int,
    ) -> None:
        if self._pool is None:
            return
        async with self._pool.acquire() as conn:
            await conn.execute(UPDATE_USER, new_winner_elo, winner_username)
            await conn.execute(UPDATE_USER, new_loser_elo, loser_username)

    async def save_game_state(self, snapshot: dict) -> None:
        import json

        if self._pool is None:
            return
        game_over = int(snapshot.get("game_over", False))
        async with self._pool.acquire() as conn:
            await conn.execute(INSERT_GAME_STATE, json.dumps(snapshot), game_over)

    async def load_game_state(self) -> Optional[dict]:
        import json

        if self._pool is None:
            return None
        async with self._pool.acquire() as conn:
            try:
                row = await conn.fetchrow(GET_GAME_STATE)
            except Exception:
                return None
        if row is None or row["game_over"]:
            return None
        return json.loads(row["snapshot"])

    async def create_room(self, room_id: str, room_name: str, creator: str) -> None:
        if self._pool is None:
            return
        try:
            async with self._pool.acquire() as conn:
                await conn.execute(INSERT_ROOM, room_id, room_name, creator, "waiting")
        except asyncpg.UniqueViolationError:
            raise UserDBError("Room ID already exists")

    async def get_room(self, room_id: str) -> Optional[dict]:
        if self._pool is None:
            return None
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(GET_ROOM, room_id)
        if row is None:
            return None
        return dict(row)

    async def list_available_rooms(self) -> list:
        if self._pool is None:
            return []
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(LIST_ROOMS)
        return [dict(row) for row in rows]

    async def update_room_status(self, room_id: str, status: str) -> None:
        if self._pool is None:
            return
        async with self._pool.acquire() as conn:
            await conn.execute(UPDATE_ROOM_STATUS, status, room_id)
