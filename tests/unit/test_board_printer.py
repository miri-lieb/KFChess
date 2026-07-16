from game_io.board_printer import token_for_piece
from model.board import Board
from model.piece import Piece, WHITE, PAWN
from model.position import Position


def test_token_for_piece_and_print():
    board = Board(8, 8)
    p = Piece(id="p1", color=WHITE, kind=PAWN, cell=Position(6, 0))
    board.add_piece(Position(6, 0), p)
    token = token_for_piece(p)
    assert token == "wP"
