from typing import List

from model.board import Board
from model.piece import Piece, COLOR_BY_LETTER, KIND_BY_LETTER
from model.position import Position


def parse_board_lines(lines: List[str]) -> Board:
    board_lines = [line.strip() for line in lines if line.strip()]
    if not board_lines:
        raise ValueError("אין שורות לוח")

    width = len(board_lines[0].split())
    board = Board(width, len(board_lines))

    for row, line in enumerate(board_lines):
        tokens = line.split()
        if len(tokens) != width:
            raise ValueError("רוחב שורה לא אחיד")
        for col, token in enumerate(tokens):
            if token == ".":
                continue
            if len(token) != 2 or token[0] not in COLOR_BY_LETTER or token[1] not in KIND_BY_LETTER:
                raise ValueError(f"טוקן לא חוקי: {token}")
            color = COLOR_BY_LETTER[token[0]]
            kind = KIND_BY_LETTER[token[1]]
            piece = Piece(id=f"{row}-{col}", color=color, kind=kind, cell=Position(row, col))
            board.add_piece(Position(row, col), piece)

    return board
