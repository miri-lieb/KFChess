from dataclasses import dataclass

from model.piece import Piece
from model.position import Position


@dataclass
class Motion:
    piece: Piece
    source: Position
    destination: Position
    remaining_time_ms: int

    def advance(self, ms: int) -> None:
        self.remaining_time_ms -= ms

    @property
    def done(self) -> bool:
        return self.remaining_time_ms <= 0
