CREATE_GAME_STATE = """
                CREATE TABLE IF NOT EXISTS game_state (
                    id        INTEGER PRIMARY KEY CHECK (id = 1),
                    snapshot  TEXT NOT NULL,
                    game_over INTEGER NOT NULL DEFAULT 0
                )
                """
INSERT_USER = "INSERT INTO users (username, password_hash, salt, elo) VALUES (?, ?, ?, ?)"
CREATE_USERS = f"""
                CREATE TABLE IF NOT EXISTS users (
                    username     TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    salt         TEXT NOT NULL,
                    elo          INTEGER NOT NULL DEFAULT 1200
                )
      
          """
GET_USER = "SELECT password_hash, salt, elo FROM users WHERE username = ?"
UPDATE_USER = "UPDATE users SET elo = ? WHERE username = ?"
INSERT_GAME_STATE = """INSERT INTO game_state (id, snapshot, game_over) VALUES (1, ?, ?)
        ON CONFLICT(id) DO UPDATE SET snapshot = excluded.snapshot, game_over = excluded.game_over """
GET_GAME_STATE = "SELECT snapshot, game_over FROM game_state WHERE id = 1"
GET_ELO = "SELECT elo FROM users WHERE username = ?"

# Room queries
CREATE_ROOMS = """
                CREATE TABLE IF NOT EXISTS rooms (
                    id          TEXT PRIMARY KEY,
                    name        TEXT NOT NULL,
                    creator     TEXT NOT NULL,
                    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    status      TEXT NOT NULL DEFAULT 'waiting',
                    FOREIGN KEY(creator) REFERENCES users(username)
                )
                """
INSERT_ROOM = "INSERT INTO rooms (id, name, creator, status) VALUES (?, ?, ?, ?)"
GET_ROOM = "SELECT id, name, creator, created_at, status FROM rooms WHERE id = ?"
LIST_ROOMS = "SELECT id, name, creator, created_at, status FROM rooms WHERE status = 'waiting' LIMIT 50"
UPDATE_ROOM_STATUS = "UPDATE rooms SET status = ? WHERE id = ?"