from dataclasses import dataclass
from typing import Optional

from model.board import Board
from model.position import Position
from realtime.real_time_arbiter import RealTimeArbiter
from rules.rule_engine import MoveValidation, validate_move

@dataclass
class MoveResult:
    is_accepted: bool
    reason: str

class GameEngine:
    def __init__(self, board: Board):
        self.board = board
        self.arbiter = RealTimeArbiter(board)
        self.game_over = False

    def request_move(self, source: Position, destination: Position) -> MoveResult:
        if self.game_over:
            return MoveResult(False, "game_over")
        if self.arbiter.has_active_motion():
            return MoveResult(False, "motion_in_progress")

        validation = validate_move(self.board, source, destination)
        if not validation.is_valid:
            return MoveResult(False, validation.reason)

        piece = self.board.get_piece(source)
        if piece is None:
            return MoveResult(False, "empty_source")

        distance = max(abs(destination.row - source.row), abs(destination.col - source.col))
        duration_ms = distance * 1000

        self.arbiter.start_motion(piece, source, destination, duration_ms)
        return MoveResult(True, "ok")

    def wait(self, ms: int) -> None:
        arrived = self.arbiter.advance_time(ms)
        if arrived is not None:
            self._resolve_arrival(arrived)

    def _resolve_arrival(self, motion) -> None:
        source = motion.source
        destination = motion.destination
        attacker = self.board.get_piece(source)
        if attacker is None:
            return

        target = self.board.get_piece(destination)
        if target is not None and target.color != attacker.color and target.kind == "king":
            self.game_over = True

        self.board.remove_piece(source)
        if target is not None:
            self.board.remove_piece(destination)
        self.board.add_piece(destination, attacker)
