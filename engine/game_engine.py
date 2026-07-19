from dataclasses import dataclass
from typing import Optional

from model.board import Board, BoardRepresentation
from model.piece import Piece, PAWN, QUEEN, WHITE, BLACK
from model.player import Player
from model.position import Position
from realtime.real_time_arbiter import RealTimeArbiter
from rules.interfaces import MoveValidator, MoveGenerator, WinConditionChecker, MoveValidation
from rules.promotion import PromotionService, PromotionResult
from config import MOTION_SPEED_MS_PER_CELL
from network.event_bus import InMemoryEventBus
from network.serialization import motion_to_dict, piece_to_dict, player_to_dict, position_to_dict


@dataclass
class MoveResult:
    is_accepted: bool
    reason: str


@dataclass
class ArrivalResult:
    captured: Optional[Piece]
    piece: Piece
    final_position: Position


class GameEngine:
    def __init__(
        self,
        board: Board,
        move_validator: Optional[MoveValidator] = None,
        move_generator: Optional[MoveGenerator] = None,
        win_checker: Optional[WinConditionChecker] = None,
        promotion_service: Optional[PromotionService] = None,
        arbiter: Optional[RealTimeArbiter] = None,
        event_bus: Optional[InMemoryEventBus] = None,
    ):
        self.board = board
        self._validator = move_validator or StandardMoveValidator()
        self._generator = move_generator or StandardMoveGenerator()
        self._win_checker = win_checker or StandardWinChecker()
        self._promotion = promotion_service or StandardPromotionService()
        self.arbiter = arbiter or RealTimeArbiter()
        self.event_bus = event_bus
        self.game_over = False
        self.players = {
            WHITE: Player(color=WHITE),
            BLACK: Player(color=BLACK),
        }
        self.winner = None

    def request_move(self, source: Position, destination: Position) -> MoveResult:
        if self.game_over:
            result = MoveResult(False, "game_over")
            self._publish_move_requested(source, destination, None, result)
            return result

        validation = self._validator.validate(self.board, source, destination)
        if not validation.is_valid:
            piece = self.board.get_piece(source)
            result = MoveResult(False, validation.reason)
            self._publish_move_requested(source, destination, piece, result)
            return result

        piece = self.board.get_piece(source)
        if piece is None:
            result = MoveResult(False, "empty_source")
            self._publish_move_requested(source, destination, None, result)
            return result

        # Check if piece is already in flight
        if self.arbiter.is_piece_in_flight(piece):
            result = MoveResult(False, "piece_in_flight")
            self._publish_move_requested(source, destination, piece, result)
            return result

        distance = max(abs(destination.row - source.row), abs(destination.col - source.col))
        duration_ms = max(1, distance * MOTION_SPEED_MS_PER_CELL)

        motion = self.arbiter.start_motion(piece, source, destination, duration_ms)
        result = MoveResult(True, "ok")
        self._publish_move_requested(source, destination, piece, result, motion)
        return result

    def wait(self, ms: int):
        arrived = self.arbiter.advance_time(ms)
        events = []
        for motion in arrived:
            arrival = self._resolve_arrival(motion)
            event = {
                "motion": motion,
                "captured": arrival.captured,
                "piece": arrival.piece,
                "final_position": arrival.final_position,
            }
            events.append(event)
            self._publish_move_resolved(motion, arrival)
        return events

    def check_win_condition(self):
        result = self._win_checker.check(self.board)
        if result:
            self._mark_game_over(result.winner_color, "win_condition")
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
                    self._mark_game_over(attacker.color, "king_captured")
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
        return ArrivalResult(captured=captured, piece=attacker, final_position=final_position)

    def _publish_move_requested(
        self,
        source: Position,
        destination: Position,
        piece: Optional[Piece],
        result: MoveResult,
        motion=None,
    ) -> None:
        if self.event_bus is None:
            return
        payload = {
            "source": position_to_dict(source),
            "destination": position_to_dict(destination),
            "accepted": result.is_accepted,
            "reason": result.reason,
            "elapsed_time_ms": self.arbiter.elapsed_time_ms,
        }
        if piece is not None:
            payload["piece"] = piece_to_dict(piece)
        if motion is not None:
            payload["motion"] = motion_to_dict(motion)
        self.event_bus.publish("move_requested", payload)

    def _publish_move_resolved(self, motion, arrival: ArrivalResult) -> None:
        if self.event_bus is None:
            return
        payload = {
            "motion": motion_to_dict(motion),
            "piece": piece_to_dict(arrival.piece),
            "final_position": position_to_dict(arrival.final_position),
            "captured": None if arrival.captured is None else piece_to_dict(arrival.captured),
            "players": {
                color: player_to_dict(player)
                for color, player in self.players.items()
            },
            "game_over": self.game_over,
            "winner_color": None if self.winner is None else self.winner.color,
            "elapsed_time_ms": self.arbiter.elapsed_time_ms,
        }
        self.event_bus.publish("move_resolved", payload)

    def _mark_game_over(self, winner_color: Optional[str], reason: str) -> None:
        if self.game_over:
            return
        self.game_over = True
        self.winner = self.players.get(winner_color) if winner_color is not None else None
        if self.event_bus is not None:
            self.event_bus.publish("game_over", {
                "winner_color": winner_color,
                "reason": reason,
            })


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
