from model.piece import PAWN
from model.position import Position
from config import (
    BOARD_FILE_NAMES,
    DEFAULT_BOARD_HEIGHT,
    NOTATION_CAPTURE_SYMBOL,
    PIECE_NOTATION_PREFIXES,
)


def position_to_algebraic(position: Position) -> str:
    rank = DEFAULT_BOARD_HEIGHT - position.row
    return f"{BOARD_FILE_NAMES[position.col]}{rank}"


def format_elapsed(seconds: float) -> str:
    minutes = int(seconds // 60)
    seconds_rem = seconds - minutes * 60
    return f"{minutes:02d}:{seconds_rem:05.2f}"


def move_notation(piece, source: Position, destination: Position, target) -> str:
    dest_notation = position_to_algebraic(destination)
    if piece.kind == PAWN:
        prefix = "" if target is None else position_to_algebraic(source)[0] + NOTATION_CAPTURE_SYMBOL
    else:
        prefix = PIECE_NOTATION_PREFIXES.get(piece.kind, "")
        if target is not None:
            prefix += NOTATION_CAPTURE_SYMBOL
    return f"{prefix}{dest_notation}"
