from config import PIECE_VALUES, STATE_IDLE
from model.piece import Piece
from model.position import Position
from realtime.motion import Motion


def position_to_dict(position: Position) -> dict[str, int]:
    return {"row": position.row, "col": position.col}


def position_from_dict(payload: dict) -> Position:
    return Position(row=int(payload["row"]), col=int(payload["col"]))


def piece_to_dict(piece) -> dict:
    return {
        "id": piece.id,
        "color": piece.color,
        "kind": piece.kind,
        "cell": position_to_dict(piece.cell),
    }


def motion_to_dict(motion) -> dict:
    return {
        "piece": piece_to_dict(motion.piece),
        "source": position_to_dict(motion.source),
        "destination": position_to_dict(motion.destination),
        "duration_ms": motion.duration_ms,
        "order": motion.order,
        "start_time_ms": motion.start_time_ms,
        "finish_time_ms": motion.finish_time,
        "return_to_fallback": motion.return_to_fallback,
    }


def board_to_dict(board) -> dict:
    pieces = [
        piece_to_dict(piece)
        for _, piece in sorted(
            board.iter_pieces(),
            key=lambda entry: (entry[0].row, entry[0].col),
        )
    ]
    return {"width": board.width, "height": board.height, "pieces": pieces}


def player_to_dict(player) -> dict:
    return {
        "color": player.color,
        "name": player.name,
        "captured_piece_ids": [piece.id for piece in player.captured_pieces],
        "score": sum(PIECE_VALUES.get(piece.kind, 0) for piece in player.captured_pieces),
    }


def snapshot_to_dict(engine) -> dict:
    return {
        "board": board_to_dict(engine.board),
        "players": {
            color: player_to_dict(player)
            for color, player in engine.players.items()
        },
        "active_motions": [motion_to_dict(motion) for motion in engine.arbiter.active_motions],
        "elapsed_time_ms": engine.arbiter.elapsed_time_ms,
        "game_over": engine.game_over,
        "winner_color": None if engine.winner is None else engine.winner.color,
    }


def piece_from_dict(payload: dict) -> Piece:
    cell = position_from_dict(payload["cell"])
    return Piece(
        id=payload["id"],
        color=payload["color"],
        kind=payload["kind"],
        cell=cell,
        state=payload.get("state", STATE_IDLE),
    )


def motion_from_dict(payload: dict) -> Motion:
    return Motion(
        piece=piece_from_dict(payload["piece"]),
        source=position_from_dict(payload["source"]),
        destination=position_from_dict(payload["destination"]),
        duration_ms=int(payload["duration_ms"]),
        order=int(payload["order"]),
        start_time_ms=int(payload["start_time_ms"]),
        return_to_fallback=bool(payload.get("return_to_fallback", False)),
    )


def engine_from_snapshot(snapshot: dict, event_bus=None):
    """Reconstruct a GameEngine from a snapshot dict (e.g. loaded from DB)."""
    from engine.game_engine import GameEngine
    from model.board import Board
    from realtime.real_time_arbiter import RealTimeArbiter

    board_payload = snapshot["board"]
    board = Board(board_payload["width"], board_payload["height"])
    for piece_payload in board_payload["pieces"]:
        piece = piece_from_dict(piece_payload)
        board.add_piece(piece.cell, piece)

    arbiter = RealTimeArbiter()
    arbiter.elapsed_time_ms = int(snapshot.get("elapsed_time_ms", 0))
    active_motions = [motion_from_dict(m) for m in snapshot.get("active_motions", [])]
    arbiter.active_motions = active_motions
    if active_motions:
        arbiter.order_counter = max(m.order for m in active_motions)

    engine = GameEngine(board, arbiter=arbiter, event_bus=event_bus)
    engine.game_over = bool(snapshot.get("game_over", False))
    return engine
