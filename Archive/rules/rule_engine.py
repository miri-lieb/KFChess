from dataclasses import dataclass

from model.board import Board
from model.position import Position
from .piece_rules import legal_destinations


@dataclass
class MoveValidation:
    is_valid: bool
    reason: str


def validate_move(board: Board, source: Position, destination: Position) -> MoveValidation:
    if not board.is_in_bounds(source) or not board.is_in_bounds(destination):
        return MoveValidation(False, "outside_board")

    piece = board.get_piece(source)
    if piece is None:
        return MoveValidation(False, "empty_source")

    target = board.get_piece(destination)
    if target is not None and target.color == piece.color:
        return MoveValidation(False, "friendly_destination")

    legal = legal_destinations(board, piece)
    if destination in legal:
        return MoveValidation(True, "ok")

    return MoveValidation(False, "illegal_piece_move")
