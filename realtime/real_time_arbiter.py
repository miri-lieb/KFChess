from typing import Optional

from model.board import Board
from model.piece import Piece
from model.position import Position
from .motion import Motion

class RealTimeArbiter:
    def __init__(self, board: Board):
        self.board = board
        self.active_motion: Optional[Motion] = None

    def has_active_motion(self) -> bool:
        return self.active_motion is not None

    def start_motion(
        self,
        piece: Pie
        source: Position,
        destination: Position,
        duration_ms: int,
    ) -> None:
        if self.active_motion is not None:
            raise RuntimeError("motion already active")
        self.active_motion = Motion(piece, source, destination, duration_ms)

    def advance_time(self, ms: int) -> Optional[Motion]:
        if self.active_motion is None:
            return None
        self.active_motion.advance(ms)
        if self.active_motion.done:
            motion = self.active_motion
            self.active_motion = None
            return motion
        return None