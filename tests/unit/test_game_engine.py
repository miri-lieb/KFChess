from model.setup import standard_starting_board
from model.position import Position
from engine.game_engine import GameEngine
from network.event_bus import InMemoryEventBus


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


def test_game_engine_publishes_move_events():
    board = standard_starting_board()
    bus = InMemoryEventBus()
    seen = []
    bus.subscribe(lambda event: seen.append(event))
    engine = GameEngine(board, event_bus=bus)

    res = engine.request_move(Position(6, 0), Position(5, 0))

    assert res.is_accepted
    engine.wait(1000)

    event_types = [event.type for event in seen]
    assert "move_requested" in event_types
    assert "move_resolved" in event_types
    requested = next(event for event in seen if event.type == "move_requested")
    resolved = next(event for event in seen if event.type == "move_resolved")
    assert requested.payload["accepted"] is True
    assert resolved.payload["final_position"] == {"row": 5, "col": 0}
