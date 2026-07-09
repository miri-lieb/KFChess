import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'files'))

from board import Board
from piece import Piece
from game import Game


def test_capture_king_sets_game_over():
    # board with white rook at (1,0) and black king at (1,2)
    grid = [
        [None, None, None],
        [Piece('w', 'R'), None, Piece.from_token('bK')],
        [None, None, None],
    ]
    b = Board(grid)
    g = Game(b)
    # select rook
    g.click(0, 100)  # x=0,y=100 -> row=1,col=0
    # click destination on king
    g.click(200, 100)  # x=200,y=100 -> row=1,col=2
    # advance time so move settles
    g.wait(1000)
    assert b.game_over is True
