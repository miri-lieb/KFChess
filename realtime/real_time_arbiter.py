from typing import List

from model.board import Board
from model.piece import Piece
from model.position import Position
from .motion import Motion

class RealTimeArbiter:
    def __init__(self, board: Board):
        self.board = board
        self.active_motions: List[Motion] = []
        self.elapsed_time_ms = 0
        self.order_counter = 0

    def has_active_motion(self) -> bool:
        return len(self.active_motions) > 0

    def start_motion( self, piece: Piece, source: Position, destination: Position, duration_ms: int):
        self.order_counter += 1
        should_return_to_fallback = any( motion.destination == destination and motion.piece.color == piece.color for motion in self.active_motions)
        motion = Motion( piece=piece, source=source, destination=destination, duration_ms=duration_ms, order=self.order_counter, start_time_ms=self.elapsed_time_ms, return_to_fallback=should_return_to_fallback)
        self.active_motions.append(motion)
        self.board.remove_piece(source)

    def advance_time(self, ms: int):
        self.elapsed_time_ms += ms
        if not self.active_motions:
            return []
        arrived = [ motion for motion in self.active_motions if motion.is_done(self.elapsed_time_ms)]
        if not arrived:
            return []
        arrived.sort(key=lambda motion: (motion.finish_time, motion.order))
        self.active_motions = [motion for motion in self.active_motions if motion not in arrived]
        return arrived
