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
