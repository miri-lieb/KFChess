from model.board import Board
from model.piece import Piece, KING, WHITE, BLACK
from model.position import Position
from rules.win_conditions import StandardWinChecker


def test_win_condition_when_white_king_missing():
    board = Board(8, 8)
    board.add_piece(Position(0, 4), Piece(id="k1", color=BLACK, kind=KING, cell=Position(0, 4)))
    checker = StandardWinChecker()
    res = checker.check(board)
    assert res is not None
    assert res.winner_color == BLACK


def test_no_win_when_both_kings_present():
    board = Board(8, 8)
    board.add_piece(Position(0, 4), Piece(id="k1", color=BLACK, kind=KING, cell=Position(0, 4)))
    board.add_piece(Position(7, 4), Piece(id="k2", color=WHITE, kind=KING, cell=Position(7, 4)))
    checker = StandardWinChecker()
    res = checker.check(board)
    assert res is None
