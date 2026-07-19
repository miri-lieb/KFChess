from realtime.real_time_arbiter import RealTimeArbiter
from model.board import Board
from model.piece import Piece, ROOK, WHITE
from model.position import Position


def test_arbiter_ordering_and_arrival():
    arb = RealTimeArbiter()
    p1 = Piece(id="r1", color=WHITE, kind=ROOK, cell=Position(0,0))
    p2 = Piece(id="r2", color=WHITE, kind=ROOK, cell=Position(0,1))
    # start two motions with different durations
    arb.start_motion(p1, Position(0,0), Position(0,3), 1000)
    arb.start_motion(p2, Position(0,1), Position(0,4), 2000)
    arrived = arb.advance_time(1500)
    # first motion arrived, second not yet
    assert len(arrived) == 1
    arrived2 = arb.advance_time(1000)
    assert len(arrived2) == 1
