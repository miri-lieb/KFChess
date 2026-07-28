CREATE_GAME_STATE = """
    CREATE TABLE IF NOT EXISTS game_state (
        id        INTEGER PRIMARY KEY DEFAULT 1,
        snapshot  TEXT NOT NULL,
        game_over INTEGER NOT NULL DEFAULT 0
    )
"""
CREATE_USERS = """
    CREATE TABLE IF NOT EXISTS users (
        username      TEXT PRIMARY KEY,
        password_hash TEXT NOT NULL,
        salt          TEXT NOT NULL,
        elo           INTEGER NOT NULL DEFAULT 1200
    )
"""
CREATE_ROOMS = """
    CREATE TABLE IF NOT EXISTS rooms (
        id         TEXT PRIMARY KEY,
        name       TEXT NOT NULL,
        creator    TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        status     TEXT NOT NULL DEFAULT 'waiting'
    )
"""

INSERT_USER = "INSERT INTO users (username, password_hash, salt, elo) VALUES ($1, $2, $3, $4)"
GET_USER = "SELECT password_hash, salt, elo FROM users WHERE username = $1"
UPDATE_USER = "UPDATE users SET elo = $1 WHERE username = $2"
GET_ELO = "SELECT elo FROM users WHERE username = $1"

INSERT_GAME_STATE = """
    INSERT INTO game_state (id, snapshot, game_over)
    VALUES (1, $1, $2)
    ON CONFLICT (id) DO UPDATE SET snapshot = EXCLUDED.snapshot, game_over = EXCLUDED.game_over
"""
GET_GAME_STATE = "SELECT snapshot, game_over FROM game_state WHERE id = 1"

INSERT_ROOM = "INSERT INTO rooms (id, name, creator, status) VALUES ($1, $2, $3, $4)"
GET_ROOM = "SELECT id, name, creator, created_at, status FROM rooms WHERE id = $1"
LIST_ROOMS = "SELECT id, name, creator, created_at, status FROM rooms WHERE status = 'waiting' LIMIT 50"
UPDATE_ROOM_STATUS = "UPDATE rooms SET status = $1 WHERE id = $2"
