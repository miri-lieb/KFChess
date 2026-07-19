from model.board import Board
from model.piece import Piece, ROOK, KNIGHT, BISHOP, QUEEN, KING, PAWN, WHITE, BLACK
from model.position import Position
from rules.piece_rules import StandardMoveGenerator


def test_rook_moves_empty_board():
    board = Board(8, 8)
    rook = Piece(id="r1", color=WHITE, kind=ROOK, cell=Position(4, 4))
    board.add_piece(Position(4, 4), rook)
    generator = StandardMoveGenerator()
    dests = generator.legal_destinations(board, rook)
    assert Position(4, 0) in dests
    assert Position(4, 7) in dests
    assert Position(0, 4) in dests
    assert Position(7, 4) in dests


def test_knight_moves():
    board = Board(8, 8)
    knight = Piece(id="n1", color=WHITE, kind=KNIGHT, cell=Position(4, 4))
    board.add_piece(Position(4, 4), knight)
    generator = StandardMoveGenerator()
    dests = generator.legal_destinations(board, knight)
    assert Position(6, 5) in dests
    assert Position(2, 3) in dests


def test_pawn_forward_and_capture():
    board = Board(8, 8)
    white_pawn = Piece(id="p1", color=WHITE, kind=PAWN, cell=Position(6, 3))
    black_pawn = Piece(id="p2", color=BLACK, kind=PAWN, cell=Position(5, 4))
    board.add_piece(Position(6, 3), white_pawn)
    board.add_piece(Position(5, 4), black_pawn)
    generator = StandardMoveGenerator()
    dests = generator.legal_destinations(board, white_pawn)
    assert Position(5, 3) in dests
    assert Position(5, 4) in dests
