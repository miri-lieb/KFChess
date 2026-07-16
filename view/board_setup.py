import os

from model.board import Board
from model.piece import Piece, WHITE, BLACK, ROOK, KNIGHT, BISHOP, QUEEN, KING, PAWN, IDLE
from model.position import Position

START_PIECES = [
    ["RB", "NB", "BB", "QB", "KB", "BB", "NB", "RB"],
    ["PB"] * 8,
    [None] * 8,
    [None] * 8,
    [None] * 8,
    [None] * 8,
    ["PW"] * 8,
    ["RW", "NW", "BW", "QW", "KW", "BW", "NW", "RW"],
]


def make_piece(code: str, row: int, col: int) -> Piece:
    kind_map = {"R": ROOK, "N": KNIGHT, "B": BISHOP, "Q": QUEEN, "K": KING, "P": PAWN}
    color = WHITE if code[1] == "W" else BLACK
    kind = kind_map[code[0]]
    return Piece(id=f"{code}-{row}-{col}", color=color, kind=kind, cell=Position(row, col), state=IDLE)


def create_initial_board() -> Board:
    board = Board(8, 8)
    for row in range(8):
        for col in range(8):
            code = START_PIECES[row][col]
            if code is None:
                continue
            board.add_piece(Position(row, col), make_piece(code, row, col))
    return board
