# Centralized configuration constants for the game

# Motion & Timing
MOTION_SPEED_MS_PER_CELL = 1000  # ms per cell distance
TICK_DURATION_MS = 20  # Game loop tick duration in ms
ARBITER_INITIAL_ELAPSED_TIME_MS = 0
ARBITER_INITIAL_ORDER_COUNTER = 0

# Rest / Cooldown timers (in ticks)
REST_TICKS = 100
SHORT_REST_TICKS = 30
JUMP_TICKS = 20

# Piece values for scoring
PIECE_VALUES = {
    "pawn": 1,
    "knight": 3,
    "bishop": 3,
    "rook": 5,
    "queen": 9,
    "king": 0,
}

# Board
DEFAULT_BOARD_WIDTH = 8
DEFAULT_BOARD_HEIGHT = 8
BOARD_FILE_NAMES = "abcdefgh"
BLACK_START_ROWS = 2

# Animation
ANIMATION_DELAY = 5
ANIMATION_FRAMES = 5

# Sprite
PIECE_SPRITE_SIZE = (80, 80)
BOARD_SPRITE_SIZE = (800, 800)

# View
PANEL_WIDTH = 260
TOP_MARGIN = 60
BOTTOM_MARGIN = 40
WINDOW_TITLE = "Chess Board"

# Network
NETWORK_HOST = "127.0.0.1"
NETWORK_PORT = 8765

# Database
import os as _os
DB_PATH = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "kfchess.db")

# ELO
ELO_DEFAULT = 1200
ELO_K_FACTOR = 32

# Roles
ROLE_WHITE = "white"
ROLE_BLACK = "black"
ROLE_OBSERVER = "observer"

# Piece states
STATE_IDLE = "idle"
STATE_MOVE = "move"
STATE_JUMP = "jump"
STATE_SHORT_REST = "short_rest"
STATE_LONG_REST = "long_rest"

# Notation
PIECE_NOTATION_PREFIXES = {
    "king": "K",
    "queen": "Q",
    "rook": "R",
    "bishop": "B",
    "knight": "N",
}
NOTATION_CAPTURE_SYMBOL = "x"

# Protocol / message types
MESSAGE_LOGIN = "login"
MESSAGE_LOGIN_ACK = "login_ack"
MESSAGE_MOVE = "move"
MESSAGE_MOVE_ACK = "move_ack"
MESSAGE_SNAPSHOT = "snapshot"
MESSAGE_ERROR = "error"
MESSAGE_PLAYER_JOINED = "player_joined"
MESSAGE_PLAYER_LEFT = "player_left"
MESSAGE_GAME_STARTED = "game_started"
MESSAGE_MOVE_REQUESTED = "move_requested"
MESSAGE_MOVE_RESOLVED = "move_resolved"
MESSAGE_GAME_OVER = "game_over"
MESSAGE_CREATE_ROOM = "create_room"
MESSAGE_JOIN_ROOM = "join_room"
MESSAGE_LIST_ROOMS = "list_rooms"
MESSAGE_ROOM_CREATED = "room_created"
MESSAGE_ROOM_JOINED = "room_joined"
MESSAGE_ROOMS_LIST = "rooms_list"

# Protocol / reasons
REASON_USERNAME_REQUIRED = "username_required"
REASON_LOGIN_REQUIRED = "login_required"
REASON_INVALID_JSON = "invalid_json"
REASON_UNKNOWN_MESSAGE_TYPE = "unknown_message_type"
REASON_INVALID_MOVE_PAYLOAD = "invalid_move_payload"
REASON_OBSERVER_READ_ONLY = "observer_read_only"
REASON_EMPTY_SOURCE = "empty_source"
REASON_WRONG_PLAYER_COLOR = "wrong_player_color"
REASON_PIECE_IN_FLIGHT = "piece_in_flight"
REASON_GAME_OVER = "game_over"
REASON_OK = "ok"
REASON_WIN_CONDITION = "win_condition"
REASON_KING_CAPTURED = "king_captured"
REASON_INVALID_CREDENTIALS = "invalid_credentials"
REASON_USER_EXISTS = "user_already_exists"
REASON_ROOM_NOT_FOUND = "room_not_found"
REASON_ROOM_FULL = "room_full"
REASON_INVALID_ROOM_NAME = "invalid_room_name"

# UI strings
USERNAME_PROMPT = "Username: "
PASSWORD_PROMPT = "Password: "
SHELL_PROMPT = "kfchess> "
SHELL_COMMAND_HINT = "Commands: move <src_row> <src_col> <dst_row> <dst_col> | snapshot | quit"
SHELL_COMMAND_MOVE = "move"
SHELL_COMMAND_SNAPSHOT = "snapshot"
SHELL_COMMAND_QUIT = "quit"
CONNECTED_AS_TEMPLATE = "Connected as {}."
MOVE_REJECTED_PREFIX = "Move rejected: "
SERVER_ERROR_PREFIX = "Server error: "
PANEL_TITLE_BLACK = "Black"
PANEL_TITLE_WHITE = "White"
PANEL_HEADER_TIME = "Time"
PANEL_HEADER_MOVE = "Move"
GAME_OVER_TEXT = "GAME OVER"
ROOM_NAME_PROMPT = "Enter room name (or 'exit' to go back): "
ROOM_ID_PROMPT = "Enter room ID (or 'exit' to go back): "