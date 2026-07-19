from dataclasses import dataclass

from model.board import BoardRepresentation
from model.position import Position
from .piece_rules import legal_destinations
from .interfaces import MoveValidator, MoveValidation


class StandardMoveValidator:
    def validate(self, board: BoardRepresentation, source: Position, destination: Position) -> MoveValidation:
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


def validate_move(board: BoardRepresentation, source: Position, destination: Position) -> MoveValidation:
    """Backward-compatible function."""
    return StandardMoveValidator().validate(board, source, destination)