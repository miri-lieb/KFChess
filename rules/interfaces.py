from typing import Protocol, Set, Optional
from dataclasses import dataclass

from model.board import BoardRepresentation
from model.piece import Piece
from model.position import Position


@dataclass
class MoveValidation:
    is_valid: bool
    reason: str


@dataclass
class WinResult:
    winner_color: str
    reason: str


@dataclass
class PromotionResult:
    promoted_piece: Optional[Piece]
    was_promoted: bool


class MoveValidator(Protocol):
    def validate(self, board: BoardRepresentation, source: Position, destination: Position) -> MoveValidation: ...


class MoveGenerator(Protocol):
    def legal_destinations(self, board: BoardRepresentation, piece: Piece) -> Set[Position]: ...


class WinConditionChecker(Protocol):
    def check(self, board: BoardRepresentation) -> Optional[WinResult]: ...


class PromotionService(Protocol):
    def try_promote(self, board: BoardRepresentation, piece: Piece, position: Position) -> PromotionResult: ...