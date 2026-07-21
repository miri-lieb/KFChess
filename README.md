# KFChess — small textual chess simulator

Files are under `files//` and the entrypoint is `files/main.py` which reads a textual board and a list of commands from stdin and simulates them.

Quick facts
- Entry point: `files/main.py`
- Board/token parser: `files/board.py`, `files/piece.py`
- Move validation: `files/movement_rules.py` (used by the game)
- Config: `files/config.py` (CELL_SIZE, MOVE_DURATION_MS, etc.)
- Tests: `tests/` (pytest)

Input format
- Two sections separated by headers (exact text):
  - `Board:` — then one or more rows, tokens separated by spaces. Valid tokens: `.` (empty), `wK,wQ,wR,wB,wN,wP,bK,bQ,bR,bB,bN,bP`.
  - `Commands:` — then one command per line.

Commands
- `click X Y` — simulate a click at pixel coordinates `(X, Y)`. The code maps to board cell as `row = Y // CELL_SIZE`, `col = X // CELL_SIZE`.
- `jump X Y` — make the piece at the clicked cell "jump" (becomes airborne) until jump arrival; when airborne, incoming attackers can be captured mid-air.
- `wait MS` — advance simulation time by `MS` milliseconds (pending moves / jumps may resolve after the configured durations).
- `print board` — print the current textual board (one row per line, tokens separated by a space).

Timing & geometry (defaults in `files/config.py`)
- `CELL_SIZE = 100` — pixel size of a board cell. Clicks are in pixel coordinates and integer-divided by CELL_SIZE.
- `MOVE_DURATION_MS = 1000` — how many ms until a normal move arrives (used for pending moves and jumps in the current implementation).
- `JUMP_DURATION_MS = 1000` — jump duration (present in config; Game currently uses `MOVE_DURATION_MS` for arrival times).

Examples
- Minimal board + commands (save as `example.txt`):

```
Board:
. . .
. . .
. wP .
Commands:
click 100 200
click 100 100
wait 1000
print board
```

- Run: `python3 files/main.py < example.txt` — output shows the board after commands are applied.

Tests
- Install pytest: `python3 -m pip install pytest --user` (or use your environment's package manager).
- Run tests: `python3 -m pytest -q`

Notes
- There was a consolidation to use `files/movement_rules.py` as the single move-validation layer; duplicate modules `files/move_rules.py`, `files/command_parser.py` and `files/move_scheduler.py` were removed (kept in git history if needed).
- The code models time and "pending" moves: calling `wait` is required to advance time so moves finish and board state updates.

If you want, I can:
1. Add CI (GitHub Actions) to run the tests on push/PR.
2. Expand tests for all piece movement/capture cases.
3. Add examples or a simple runner wrapper to convert human-friendly cell coordinates to pixel clicks.

## Local multiplayer milestone

- One-time setup from the repo root: `python3 -m pip install -e .`
- Start the local WebSocket server: `python3 -m network.server_main`
- Start one shell client per player: `python3 -m network.shell_client`
- Start the graphical network client: `python3 -m network.opencv_client`
- After the editable install, those commands work even if your current directory is `view/` or another subdirectory.
- Optional shortcuts after install:
  - `kfchess-server`
  - `kfchess-shell`
  - `kfchess-gui`
- Graphical roles:
  - first login gets **white**
  - second login gets **black**
  - later logins become **observer**
- Login is username-based only:
  - exactly two active player seats
  - additional clients join as observers
- Shell client commands:
  - `move <src_row> <src_col> <dst_row> <dst_col>`
  - `snapshot`
  - `quit`

The server publishes JSON events for `player_joined`, `game_started`, `move_requested`, `move_resolved`, and `game_over`.

## Room System (NEW)

The game now supports a room-based multiplayer system where players can create and join separate game rooms.

### How to use:

1. **Start the server**: `python3 -m network.server_main`
2. **Connect with shell client**: `python3 -m network.shell_client`
3. **Choose room mode** when prompted:
   - Option 1: Use Room system (new)
   - Option 2: Direct login (classic mode with single shared game)

### Room Features:

- **Create Room**: 
  - Player enters a room name
  - Server generates a unique 6-character room ID (e.g., `ABC123`)
  - Room creator receives the ID to share with others

- **Join Room**:
  - Player enters the room ID they received
  - Player joins the room as white (if available), black (if white is taken), or observer (if room is full)

- **List Rooms**:
  - View all available rooms
  - See room name, creator, and player count
  - Copy a room ID to join

### Room Roles:

Each room can have:
- **Player 1 (White)**: First player to join
- **Player 2 (Black)**: Second player to join
- **Observers**: Up to 10 additional viewers (can watch but not play)

### Example Workflow:

```
Player A (Alice):
1. Starts shell client
2. Selects "Create new room"
3. Enters room name: "Championship Match"
4. Gets room ID: "X3K7M9"
5. Shares ID with Player B

Player B (Bob):
1. Starts shell client
2. Selects "Join existing room"
3. Enters room ID: "X3K7M9"
4. Joins as Black player
5. Game starts when both players are present
```

### Protocol (for API integration):

Messages for room operations:

```json
// Create room
{"type": "create_room", "username": "alice", "room_name": "Battle"}
// Response: {"type": "room_created", "payload": {"room_id": "ABC123", "room_name": "Battle"}}

// Join room
{"type": "join_room", "username": "bob", "password": "", "room_id": "ABC123"}
// Response: {"type": "room_joined", "payload": {"room_id": "ABC123", "role": "white", "color": "white"}}

// List rooms
{"type": "list_rooms"}
// Response: {"type": "rooms_list", "payload": {"rooms": [...]}}
```
