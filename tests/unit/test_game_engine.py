from model.setup import standard_starting_board
from model.position import Position
from engine.game_engine import GameEngine


def test_game_engine_pawn_move_and_capture_king():
    board = standard_starting_board()
    engine = GameEngine(board)
    # Move white pawn at (6,0) to (5,0)
    res = engine.request_move(Position(6,0), Position(5,0))
    assert res.is_accepted
    engine.wait(1000)
    # place a black king diagonally in front of pawn so pawn can capture
    from model.piece import Piece, KING, BLACK
    board.add_piece(Position(4,1), Piece(id='bk', color=BLACK, kind=KING, cell=Position(4,1)))
    res2 = engine.request_move(Position(5,0), Position(4,1))
    assert res2.is_accepted
    engine.wait(1000)
    assert engine.game_over
