from config import REST_TICKS
from network.remote_state import RemoteEngineView, RemoteGameState


def test_remote_state_applies_snapshot_and_move_events():
    engine = RemoteEngineView()
    state = RemoteGameState()

    state.apply_message(engine, {
        "type": "login_ack",
        "payload": {
            "snapshot": {
                "board": {
                    "width": 8,
                    "height": 8,
                    "pieces": [
                        {"id": "p1", "color": "white", "kind": "pawn", "cell": {"row": 6, "col": 0}, "state": "idle"},
                    ],
                },
                "players": {
                    "white": {"score": 0},
                    "black": {"score": 0},
                },
                "active_motions": [],
                "elapsed_time_ms": 0,
                "game_over": False,
                "winner_color": None,
            },
        },
    })

    state.apply_message(engine, {
        "type": "move_requested",
        "payload": {
            "accepted": True,
            "elapsed_time_ms": 0,
            "motion": {
                "piece": {"id": "p1", "color": "white", "kind": "pawn", "cell": {"row": 6, "col": 0}, "state": "idle"},
                "source": {"row": 6, "col": 0},
                "destination": {"row": 5, "col": 0},
                "duration_ms": 1000,
                "order": 1,
                "start_time_ms": 0,
                "finish_time_ms": 1000,
                "return_to_fallback": False,
            },
        },
    })
    assert len(engine.arbiter.active_motions) == 1

    state.apply_message(engine, {
        "type": "move_resolved",
        "payload": {
            "motion": {
                "piece": {"id": "p1", "color": "white", "kind": "pawn", "cell": {"row": 6, "col": 0}, "state": "idle"},
                "source": {"row": 6, "col": 0},
                "destination": {"row": 5, "col": 0},
                "duration_ms": 1000,
                "order": 1,
                "start_time_ms": 0,
                "finish_time_ms": 1000,
                "return_to_fallback": False,
            },
            "piece": {"id": "p1", "color": "white", "kind": "pawn", "cell": {"row": 5, "col": 0}, "state": "idle"},
            "final_position": {"row": 5, "col": 0},
            "captured": None,
            "game_over": False,
            "winner_color": None,
            "elapsed_time_ms": 1000,
        },
    })

    assert engine.board.get_piece(type("Pos", (), {"row": 5, "col": 0})()) is None
    from model.position import Position
    assert engine.board.get_piece(Position(5, 0)).id == "p1"
    assert state.rest_timers[Position(5, 0)] == REST_TICKS
