from model.board import Board
from model.piece import Piece, WHITE, BLACK, ROOK, KNIGHT, BISHOP, QUEEN, KING, PAWN
from model.position import Position
from model.piece_factory import PieceFactory
from typing import List

START_PIECES = [
    ["R","N","B","Q","K","B","N","R"],
    ["P"] * 8,
    [None] * 8,
    [None] * 8,
    [None] * 8,
    [None] * 8,
    ["P"] * 8,
    ["R","N","B","Q","K","B","N","R"],
]

def standard_starting_board() -> Board:
    board = Board(8, 8)
    # Top (row 0) is black, bottom (row 7) is white
    for row in range(8):
        for col in range(8):
            code = START_PIECES[row][col]
            if code is None:
                continue
            if row <= 1:
                color = BLACK
            else:
                color = WHITE
            kind_map = {"R": ROOK, "N": KNIGHT, "B": BISHOP, "Q": QUEEN, "K": KING, "P": PAWN}
            kind = kind_map[code]
            piece = PieceFactory.create(kind, color, Position(row, col))
            board.add_piece(Position(row, col), piece)
    return board

def standard_starting_board_lines() -> List[str]:
    # returns the textual token lines matching game_io.parser token format: color letter then kind letter
    lines: List[str] = []
    for row in range(8):
        tokens: List[str] = []
        for col in range(8):
            piece = START_PIECES[row][col]
            if piece is None:
                tokens.append(".")
            else:
                color = "b" if row <= 1 else "w"
                tokens.append(f"{color}{piece}")
        lines.append(" ".join(tokens))
    return lines