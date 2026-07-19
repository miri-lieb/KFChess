from dataclasses import dataclass

from model.position import Position

WHITE = "white"
BLACK = "black"

KING = "king"
QUEEN = "queen"
ROOK = "rook"
BISHOP = "bishop"
KNIGHT = "knight"
PAWN = "pawn"


@dataclass
class Piece:
    id: str
    color: str
    kind: str
    cell: Position

COLOR_BY_LETTER = {"w": WHITE, "b": BLACK}
KIND_BY_LETTER = {"K": KING, "Q": QUEEN, "R": ROOK, "B": BISHOP, "N": KNIGHT, "P": PAWN}

    
