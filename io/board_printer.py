from typing import Dict

from model.board import Board
from model.piece import Piece, WHITE, BLACK, KING, QUEEN, ROOK, BISHOP, KNIGHT, PAWN
from model.position import Position

LETTER_BY_COLOR: Dict[str, str] = {WHITE: "w", BLACK: "b"}
LETTER_BY_KIND: Dict[str, str] = {
    KING: "K",
    QUEEN: "Q",
    ROOK: "R",
    BISHOP: "B",
    KNIGHT: "N",
    PAWN: "P",
}


def token_for_piece(piece: Piece) -> str:
    return f"{LETTER_BY_COLOR[piece.color]}{LETTER_BY_KIND[piece.kind]}"


def print_board(board: Board) -> None:
    for row in range(board.height):
        tokens = []
        for col in range(board.width):
            position = Position(row, col)
            piece = board.get_piece(position)
            tokens.append(token_for_piece(piece) if piece is not None else ".")
        print(" ".join(tokens))
