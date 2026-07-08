from dataclasses import dataclass
from typing import Optional

from board import Board
from piece import Piece


@dataclass
class MoveContext:
    board: Board
    from_row: int
    from_col: int
    to_row: int
    to_col: int

    @property
    def current_piece(self) -> Optional[Piece]:
        return self.board.get(self.from_row, self.from_col)

    @property
    def target_piece(self) -> Optional[Piece]:
        return self.board.get(self.to_row, self.to_col)

    @property
    def direction(self) -> int:
        if self.current_piece is None:
            return 0
        return -1 if self.current_piece.color == 'w' else 1
