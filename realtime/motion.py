from dataclasses import dataclass

from model.piece import Piece
from model.position import Position

@dataclass
class Motion:
    piece: Piece
    source: Position
    destination: Position
    duration_ms: int
    order: int
    start_time_ms: int
    return_to_fallback: bool = False

    @property
    def finish_time(self) -> int:
        return self.start_time_ms + self.duration_ms

    def remaining_time(self, current_time: int) -> int:
        return max(0, self.finish_time - current_time)

    def progress(self, current_time: int) -> float:
        if self.duration_ms <= 0:
            return 1.0
        elapsed = current_time - self.start_time_ms
        return max(0.0, min(1.0, elapsed / self.duration_ms))

    def is_done(self, current_time: int) -> bool:
        return current_time >= self.finish_time
