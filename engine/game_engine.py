from dataclasses import dataclass
from typing import List, Optional

from model.board import Board, BoardRepresentation
from model.piece import Piece, PAWN, QUEEN, WHITE, BLACK
from model.player import Player
from model.position import Position
from realtime.real_time_arbiter import RealTimeArbiter
from rules.interfaces import MoveValidator, MoveGenerator, WinConditionChecker, MoveValidation
from rules.promotion import PromotionService, PromotionResult
from config import MOTION_SPEED_MS_PER_CELL


@dataclass
class MoveResult:
    is_accepted: bool
    reason: str


class GameEngine:
    def __init__(
        self,
        board: Board,
        move_validator: Optional[MoveValidator] = None,
        move_generator: Optional[MoveGenerator] = None,
        win_checker: Optional[WinConditionChecker] = None,
        promotion_service: Optional[PromotionService] = None,
        arbiter: Optional[RealTimeArbiter] = None,
    ):
        self.board = board
        self._validator = move_validator or StandardMoveValidator()
        self._generator = move_generator or StandardMoveGenerator()
        self._win_checker = win_checker or StandardWinChecker()
        self._promotion = promotion_service or StandardPromotionService()
        self.arbiter = arbiter or RealTimeArbiter()
        self.game_over = False
        self.players = {
            WHITE: Player(color=WHITE),
            BLACK: Player(color=BLACK),
        }
        self.winner = None

    def request_move(self, source: Position, destination: Position) -> MoveResult:
        if self.game_over:
            return MoveResult(False, "game_over")

        validation = self._validator.validate(self.board, source, destination)
        if not validation.is_valid:
            return MoveResult(False, validation.reason)

        piece = self.board.get_piece(source)
        if piece is None:
            return MoveResult(False, "empty_source")

        # Check if piece is already in flight
        if self.arbiter.is_piece_in_flight(piece):
            return MoveResult(False, "piece_in_flight")

        distance = max(abs(destination.row - source.row), abs(destination.col - source.col))
        duration_ms = max(1, distance * MOTION_SPEED_MS_PER_CELL)

        self.arbiter.start_motion(piece, source, destination, duration_ms)
        return MoveResult(True, "ok")

    def wait(self, ms: int):
        arrived = self.arbiter.advance_time(ms)
        events = []
        for motion in arrived:
            captured = self._resolve_arrival(motion)
            events.append({"motion": motion, "captured": captured})
        return events

    def check_win_condition(self):
        result = self._win_checker.check(self.board)
        if result:
            self.game_over = True
            self.winner = self.players.get(result.winner_color)
        return result

    def _resolve_arrival(self, motion):
        attacker = motion.piece
        destination = motion.destination
        captured = None

        if motion.return_to_fallback:
            allowed_destinations = self._generator.legal_destinations(self.board, attacker)
            fallback_positions = [
                pos
                for pos in allowed_destinations
                if pos != destination and self.board.get_piece(pos) is None
            ]
            if fallback_positions:
                final_position = min(
                    fallback_positions,
                    key=lambda pos: abs(pos.row - destination.row) + abs(pos.col - destination.col),
                )
            else:
                final_position = motion.source
        else:
            target = self.board.get_piece(destination)
            if target is not None and target.color != attacker.color:
                capturer = self.players.get(attacker.color)
                if target.kind == "king":
                    self.game_over = True
                    self.winner = capturer
                self.board.remove_piece(destination)
                captured = target
                if capturer is not None:
                    capturer.capture(captured)
            final_position = destination

        promo_result = self._promotion.try_promote(self.board, attacker, final_position)
        if promo_result.was_promoted:
            attacker = promo_result.promoted_piece

        # Remove from source (if still there) and add to final position
        if self.board.get_piece(motion.source) is attacker:
            self.board.remove_piece(motion.source)
        attacker.cell = final_position
        self.board.add_piece(final_position, attacker)
        return captured


# Backward-compatible default implementations
class StandardMoveValidator:
    def __init__(self):
        from rules.rule_engine import StandardMoveValidator as RulesValidator
        self._impl = RulesValidator()

    def validate(self, board: BoardRepresentation, source: Position, destination: Position) -> MoveValidation:
        return self._impl.validate(board, source, destination)


class StandardMoveGenerator:
    def __init__(self):
        from rules.piece_rules import StandardMoveGenerator as RulesGenerator
        self._impl = RulesGenerator()

    def legal_destinations(self, board: BoardRepresentation, piece: Piece) -> set[Position]:
        return self._impl.legal_destinations(board, piece)


class StandardWinChecker:
    def __init__(self):
        from rules.win_conditions import StandardWinChecker as RulesWinChecker
        self._impl = RulesWinChecker()

    def check(self, board: BoardRepresentation):
        return self._impl.check(board)


class StandardPromotionService:
    def __init__(self):
        from rules.promotion import StandardPromotionService as RulesPromotion
        self._impl = RulesPromotion()

    def try_promote(self, board: BoardRepresentation, piece: Piece, position: Position) -> PromotionResult:
        return self._impl.try_promote(board, piece, position)
