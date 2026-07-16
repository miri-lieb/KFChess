from model.board import Board
from model.piece import Piece, ROOK, WHITE
from model.position import Position
from rules.rule_engine import validate_move


def test_validate_move_out_of_bounds():
    board = Board(8, 8)
    assert not validate_move(board, Position(0,0), Position(8,8)).is_valid


def test_validate_move_empty_source():
    board = Board(8, 8)
    assert not validate_move(board, Position(1,1), Position(2,2)).is_valid


def test_validate_move_friendly_fire():
    board = Board(8, 8)
    r1 = Piece(id="r1", color=WHITE, kind=ROOK, cell=Position(0,0))
    r2 = Piece(id="r2", color=WHITE, kind=ROOK, cell=Position(0,1))
    board.add_piece(Position(0,0), r1)
    board.add_piece(Position(0,1), r2)
    res = validate_move(board, Position(0,0), Position(0,1))
    assert not res.is_valid and res.reason == "friendly_destination"
