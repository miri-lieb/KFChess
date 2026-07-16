from model.position import Position
from model.board import Board
from model.piece import Piece, WHITE, PAWN
from input.controller import Controller


def make_board_with_pawn():
    board = Board(8, 8)
    pawn = Piece(id="p1", color=WHITE, kind=PAWN, cell=Position(6, 0))
    board.add_piece(Position(6, 0), pawn)
    return board


def test_click_select_and_move():
    board = make_board_with_pawn()
    controller = Controller(type('E', (), {'board': board, 'request_move': lambda self, s, d: type('R', (), {'is_accepted': True, 'reason': 'ok'})})())
    # First click selects
    controller.click(Position(6, 0))
    assert controller.selected == Position(6, 0)
    # Second click on destination attempts move and clears selection
    controller.click(Position(5, 0))
    assert controller.selected is None
