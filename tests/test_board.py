import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'files'))

from board import Board
from piece import Piece


def test_from_lines_and_print():
    lines = ['. wK .', '. . .']
    b = Board.from_lines(lines)
    assert b is not None
    assert b.height == 2
    assert b.width == 3
    assert b.get(0, 1).token == 'wK'


def test_is_path_clear():
    # create a 3x3 empty board
    grid = [[None for _ in range(3)] for _ in range(3)]
    b = Board(grid)
    assert b.is_path_clear(0, 0, 0, 2)
    # block middle
    b.set(0, 1, Piece('w', 'P'))
    assert not b.is_path_clear(0, 0, 0, 2)
