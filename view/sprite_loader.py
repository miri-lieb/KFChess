import os

from model.piece import WHITE, BLACK, ROOK, KNIGHT, BISHOP, QUEEN, KING, PAWN
from model.position import Position
from .img import Img
from config import (
    PIECE_SPRITE_SIZE,
    BOARD_SPRITE_SIZE,
    ANIMATION_DELAY,
    ANIMATION_FRAMES,
    REST_TICKS,
    SHORT_REST_TICKS,
    JUMP_TICKS,
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(SCRIPT_DIR, "assets")
BOARD_PATH = os.path.join(ASSETS_DIR, "board.png")
PIECE_SIZE = PIECE_SPRITE_SIZE
BOARD_SIZE = BOARD_SPRITE_SIZE
SHORT_REST_STATE = "short_rest"
LONG_REST_STATE = "long_rest"

SPRITE_CODES = ["PW", "PB", "RW", "RB", "NW", "NB", "BW", "BB", "QW", "QB", "KW", "KB"]
SPRITE_PATHS = {
    code: os.path.join(ASSETS_DIR, "pieces_mine", f"{code[1]}{code[0]}", "states")
    for code in SPRITE_CODES
}

KIND_TO_SYMBOL = {
    "king": "K",
    "queen": "Q",
    "rook": "R",
    "bishop": "B",
    "knight": "N",
    "pawn": "P",
}

STATE_ORDER = ["idle", "move", "jump", SHORT_REST_STATE, LONG_REST_STATE]

def load_sprite_frames(state_dir: str):
    frames = []
    for frame_index in range(1, ANIMATION_FRAMES + 1):
        frame_path = os.path.join(state_dir, f"{frame_index}.png")
        frames.append(Img().read(frame_path, size=PIECE_SIZE, keep_aspect=True))
    return frames

def load_sprites():
    sprites = {}
    for code, state_dir in SPRITE_PATHS.items():
        sprites[code] = {
            state: load_sprite_frames(os.path.join(state_dir, state, "sprites"))
            for state in STATE_ORDER
        }
    return sprites

def piece_state(position: Position, jump_timers, short_rest_timers, long_rest_timers) -> str:
    if position in jump_timers:
        return "jump"
    if position in short_rest_timers:
        return SHORT_REST_STATE
    if position in long_rest_timers:
        return LONG_REST_STATE
    return "idle"

def piece_sprite(sprites, piece, state: str, animation_tick: int):
    kind_code = KIND_TO_SYMBOL[piece.kind]
    code = f"{kind_code}{piece.color[0].upper()}"
    state_frames = sprites[code][state]
    frame_index = (animation_tick // ANIMATION_DELAY) % len(state_frames)
    return state_frames[frame_index]