# Centralized configuration constants for the game

# Motion & Timing
MOTION_SPEED_MS_PER_CELL = 1000  # ms per cell distance
TICK_DURATION_MS = 20  # Game loop tick duration in ms

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