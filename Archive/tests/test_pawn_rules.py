import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'files'))

from board import Board
from piece import Piece
from pawn_rules import is_valid_pawn_move, promote_if_needed
from move_context import MoveContext


def make_board(grid_tokens):
    grid = []
    for row in grid_tokens:
        r = []
        for tok in row:
            r.append(Piece.from_token(tok))
        grid.append(r)
    return Board(grid)


def test_pawn_single_step_and_double_step_and_promotion():
    # white pawn at row 2 (bottom), can move up (direction -1)
    b = make_board([
        ['.', '.', '.'],
        ['.', '.', '.'],
        ['.', 'wP', '.'],
    ])
    ctx = MoveContext(board=b, from_row=2, from_col=1, to_row=1, to_col=1)
    assert is_valid_pawn_move(ctx)

    # double step from start row (for white start_row is height -1 == 2)
    ctx2 = MoveContext(board=b, from_row=2, from_col=1, to_row=0, to_col=1)
    assert is_valid_pawn_move(ctx2)

    # promotion when reaching last row
    p = Piece('w', 'P')
    promoted = promote_if_needed(p, 0, b)
    assert promoted.type == 'Q'
