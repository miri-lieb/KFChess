from dataclasses import dataclass
from typing import Optional

from model.board import Board, BoardRepresentation
from model.piece import Piece, PAWN, QUEEN, WHITE, BLACK
from model.player import Player
from model.position import Position
from realtime.real_time_arbiter import RealTimeArbiter
from rules import (
    StandardMoveValidator,
    StandardMoveGenerator,
    StandardWinChecker,
    StandardPromotionService,
    PromotionResult,
)
from config import MOTION_SPEED_MS_PER_CELL
from network.event_bus import InMemoryEventBus

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
    """Coordinates move requests, time advancement, and game state."""
    def __init__(
        self,
        board: Board,
        arbiter: Optional[RealTimeArbiter] = None,
        event_bus: Optional[InMemoryEventBus] = None,
    ):
        self.board = board
        self.arbiter = arbiter or RealTimeArbiter()
        self.game_over = False
        self.players = {
            WHITE: Player(color=WHITE),
            BLACK: Player(color=BLACK),
        }
        self.winner = None

        self._validator = StandardMoveValidator()
        self._generator = StandardMoveGenerator()
        self._win_checker = StandardWinChecker()
        self._promotion = StandardPromotionService()
        self._publisher = EventPublisher(event_bus)

    def request_move(self, source: Position, destination: Position) -> MoveResult:
        if self.game_over:
            result = MoveResult(False, "game_over")
            self._publisher.publish_move_requested(
                source, destination, None, result, elapsed_time_ms=self.arbiter.elapsed_time_ms
            )
            return result

        validation = self._validator.validate(self.board, source, destination)
        if not validation.is_valid:
            piece = self.board.get_piece(source)
            result = MoveResult(False, validation.reason)
            self._publisher.publish_move_requested(
                source, destination, piece, result, elapsed_time_ms=self.arbiter.elapsed_time_ms
            )
            return result

        piece = self.board.get_piece(source)
        if piece is None:
            result = MoveResult(False, "empty_source")
            self._publisher.publish_move_requested(
                source, destination, None, result, elapsed_time_ms=self.arbiter.elapsed_time_ms
            )
            return result

        if self.arbiter.is_piece_in_flight(piece):
            result = MoveResult(False, "piece_in_flight")
            self._publisher.publish_move_requested(
                source, destination, piece, result, elapsed_time_ms=self.arbiter.elapsed_time_ms
            )
            return result

        distance = max(abs(destination.row - source.row), abs(destination.col - source.col))
        duration_ms = max(1, distance * MOTION_SPEED_MS_PER_CELL)

        motion = self.arbiter.start_motion(piece, source, destination, duration_ms)
        result = MoveResult(True, "ok")
        self._publisher.publish_move_requested(
            source, destination, piece, result, motion, self.arbiter.elapsed_time_ms
        )
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
            self._publisher.publish_move_resolved(
                motion,
                arrival,
                self.players,
                self.game_over,
                self.winner,
                self.arbiter.elapsed_time_ms,
            )
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

        if self.board.get_piece(motion.source) is attacker:
            self.board.remove_piece(motion.source)
        attacker.cell = final_position
        self.board.add_piece(final_position, attacker)
        return ArrivalResult(captured=captured, piece=attacker, final_position=final_position)

    def _mark_game_over(self, winner_color: Optional[str], reason: str) -> None:
        if self.game_over:
            return
        self.game_over = True
        self.winner = self.players.get(winner_color) if winner_color is not None else None
        self._publisher.publish_game_over(winner_color, reason)

class EventPublisher:
    """Publishes game events to an event bus."""
    def __init__(self, event_bus: Optional[InMemoryEventBus] = None):
        self.event_bus = event_bus

    def publish_move_requested(
        self,
        source: Position,
        destination: Position,
        piece: Optional[Piece],
        result: MoveResult,
        motion=None,
        elapsed_time_ms: int = 0,
    ) -> None:
        if self.event_bus is None:
            return
        payload = {
            "source": {"row": source.row, "col": source.col},
            "destination": {"row": destination.row, "col": destination.col},
            "accepted": result.is_accepted,
            "reason": result.reason,
            "elapsed_time_ms": elapsed_time_ms,
        }
        if piece is not None:
            payload["piece"] = {
                "id": piece.id,
                "color": piece.color,
                "kind": piece.kind,
                "cell": {"row": piece.cell.row, "col": piece.cell.col}
            }
        if motion is not None:
            payload["motion"] = {
                "piece": {
                    "id": motion.piece.id,
                    "color": motion.piece.color,
                    "kind": motion.piece.kind,
                    "cell": {"row": motion.piece.cell.row, "col": motion.piece.cell.col},
                },
                "source": {"row": motion.source.row, "col": motion.source.col},
                "destination": {"row": motion.destination.row, "col": motion.destination.col},
                "duration_ms": motion.duration_ms,
                "order": motion.order,
                "start_time_ms": motion.start_time_ms,
                "finish_time_ms": motion.finish_time,
                "return_to_fallback": motion.return_to_fallback
            }
        self.event_bus.publish("move_requested", payload)

    def publish_move_resolved(
        self,
        motion,
        arrival: ArrivalResult,
        players: dict,
        game_over: bool,
        winner: Optional[Piece] = None,
        elapsed_time_ms: int = 0,
    ) -> None:
        if self.event_bus is None:
            return
        payload = {
            "motion": {
                "piece": {
                    "id": motion.piece.id,
                    "color": motion.piece.color,
                    "kind": motion.piece.kind,
                    "cell": {"row": motion.piece.cell.row, "col": motion.piece.cell.col},
                },
                "source": {"row": motion.source.row, "col": motion.source.col},
                "destination": {"row": motion.destination.row, "col": motion.destination.col},
                "duration_ms": motion.duration_ms,
                "order": motion.order,
                "start_time_ms": motion.start_time_ms,
                "finish_time_ms": motion.finish_time,
                "return_to_fallback": motion.return_to_fallback,
            },
            "piece": {
                "id": arrival.piece.id,
                "color": arrival.piece.color,
                "kind": arrival.piece.kind,
                "cell": {"row": arrival.piece.cell.row, "col": arrival.piece.cell.col},
            },
            "final_position": {"row": arrival.final_position.row, "col": arrival.final_position.col},
            "captured": None if arrival.captured is None else {
                "id": arrival.captured.id,
                "color": arrival.captured.color,
                "kind": arrival.captured.kind,
                "cell": {"row": arrival.captured.cell.row, "col": arrival.captured.cell.col},
            },
            "players": {
                color: {
                    "color": player.color,
                    "name": player.name,
                    "captured_piece_ids": [p.id for p in player.captured_pieces],
                    "score": 0,
                }
                for color, player in players.items()
            },
            "game_over": game_over,
            "winner_color": None if winner is None else winner.color,
            "elapsed_time_ms": elapsed_time_ms,
        }
        self.event_bus.publish("move_resolved", payload)

    def publish_game_over(self, winner_color: Optional[str], reason: str) -> None:
        if self.event_bus is None:
            return
        self.event_bus.publish("game_over", {
            "winner_color": winner_color,
            "reason": reason
        })