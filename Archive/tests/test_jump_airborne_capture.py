import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'files'))

from board import Board
from piece import Piece
from game import Game


def test_airborne_piece_captures_arriving_attacker_and_king_ends_game():
    # Setup: black knight will jump and be airborne at (1,1).
    # Then white king will attempt to move into (1,1) and be captured in-air -> game over.
    grid = [
        [None, None, None],
        [None, Piece.from_token('bN'), None],
        [None, Piece.from_token('wK'), None],
    ]
    b = Board(grid)
    g = Game(b)

    # black knight jump from (1,1)
    g.jump(100, 100)  # row=1,col=1
    # white king moves from (2,1) to (1,1)
    g.click(100, 200)  # select wK at row=2,col=1
    g.click(100, 100)  # target row=1,col=1
    # advance time so pending moves arrive and jump resolves
    g.wait(1000)

    # attacker (wK) should have been captured in-air and game_over True
    assert b.game_over is True
