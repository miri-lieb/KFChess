from dataclasses import dataclass
from typing import Optional, Protocol

from model.board import BoardRepresentation
from model.piece import Piece, PAWN, QUEEN, WHITE, BLACK
from model.position import Position
from model.piece_factory import PieceFactory


@dataclass
class PromotionResult:
    promoted_piece: Optional[Piece]
    was_promoted: bool


class PromotionService(Protocol):
    def try_promote(self, board: BoardRepresentation, piece: Piece, position: Position) -> PromotionResult: ...


class StandardPromotionService:
    def try_promote(self, board: BoardRepresentation, piece: Piece, position: Position) -> PromotionResult:
        if piece.kind != PAWN:
            return PromotionResult(promoted_piece=None, was_promoted=False)

        promotion_row = 0 if piece.color == WHITE else board.height - 1
        if position.row != promotion_row:
            return PromotionResult(promoted_piece=None, was_promoted=False)

        promoted_piece = PieceFactory.create_promoted_queen(piece, position)
        return PromotionResult(promoted_piece=promoted_piece, was_promoted=True)