from dataclasses import dataclass
from typing import Optional

from model.board import Board
from model.piece import Piece
from model.position import Position


@dataclass
class MoveContext:
    board: Board
    source: Position
    destination: Position

    @property
    def current_piece(self) -> Optional[Piece]:
        return self.board.get_piece(self.source)

    @property
    def target_piece(self) -> Optional[Piece]:
        return self.board.get_piece(self.destination)

    @property
    def direction(self) -> int:
        current = self.current_piece
        if current is None:
            return 0
        return -1 if current.color == "white" else 1
