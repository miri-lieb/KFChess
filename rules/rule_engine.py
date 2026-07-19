from dataclasses import dataclass

from model.board import BoardRepresentation
from model.position import Position
from .piece_rules import StandardMoveGenerator
from .interfaces import MoveValidator, MoveGenerator, MoveValidation


class StandardMoveValidator:
    def __init__(self, generator: MoveGenerator = None):
        self._generator = generator or StandardMoveGenerator()

    def validate(self, board: BoardRepresentation, source: Position, destination: Position) -> MoveValidation:
        if not board.is_in_bounds(source) or not board.is_in_bounds(destination):
            return MoveValidation(False, "outside_board")
        piece = board.get_piece(source)
        if piece is None:
            return MoveValidation(False, "empty_source")
        target = board.get_piece(destination)
        if target is not None and target.color == piece.color:
            return MoveValidation(False, "friendly_destination")
        legal = self._generator.legal_destinations(board, piece)
        if destination in legal:
            return MoveValidation(True, "ok")
        return MoveValidation(False, "illegal_piece_move")