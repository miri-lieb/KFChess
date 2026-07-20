from dataclasses import dataclass

from config import ROLE_BLACK as BLACK, ROLE_WHITE as WHITE, STATE_IDLE as IDLE
from model.position import Position

KING = "king"
QUEEN = "queen"
ROOK = "rook"
BISHOP = "bishop"
KNIGHT = "knight"
PAWN = "pawn"

COLOR_BY_LETTER = {"w": WHITE, "b": BLACK}
KIND_BY_LETTER = {"K": KING, "Q": QUEEN, "R": ROOK, "B": BISHOP, "N": KNIGHT, "P": PAWN}

@dataclass
class Piece:
    id: str
    color: str
    kind: str
    cell: Position
    state: str = IDLE
