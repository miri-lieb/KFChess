import time
from dataclasses import dataclass, field
from typing import Optional

from config import (
    DEFAULT_BOARD_HEIGHT,
    DEFAULT_BOARD_WIDTH,
    MESSAGE_GAME_OVER,
    MESSAGE_LOGIN_ACK,
    MESSAGE_MOVE_REQUESTED,
    MESSAGE_MOVE_RESOLVED,
    MESSAGE_SNAPSHOT,
    REASON_EMPTY_SOURCE,
    REASON_OBSERVER_READ_ONLY,
    REASON_OK,
    REASON_WRONG_PLAYER_COLOR,
    ROLE_BLACK,
    ROLE_WHITE,
    REST_TICKS,
    TICK_DURATION_MS,
)
from model.board import Board
from model.position import Position
from network.serialization import motion_from_dict, piece_from_dict
from realtime.motion import Motion
from view.input_handler import move_notation


class RemoteArbiterView:
    def __init__(self):
        self.active_motions: list[Motion] = []
        self.elapsed_time_ms = 0


class RemoteEngineView:
    def __init__(self):
        self.board = Board(DEFAULT_BOARD_WIDTH, DEFAULT_BOARD_HEIGHT)
        self.arbiter = RemoteArbiterView()
        self.game_over = False

    def wait(self, ms: int) -> list:
        self.arbiter.elapsed_time_ms += ms
        return []


@dataclass
class RemoteGameState:
    rest_timers: dict = field(default_factory=dict)
    short_rest_timers: dict = field(default_factory=dict)
    jump_timers: dict = field(default_factory=dict)
    move_log: list = field(default_factory=list)
    legal_moves: set = field(default_factory=set)
    scores: dict = field(default_factory=lambda: {ROLE_WHITE: 0, ROLE_BLACK: 0})
    start_time: float = field(default_factory=time.perf_counter)
    game_over: bool = False
    animation_tick: int = 0
    local_role: Optional[str] = None
    local_color: Optional[str] = None
    username: Optional[str] = None

    def apply_snapshot(self, engine: RemoteEngineView, payload: dict) -> None:
        board_payload = payload["board"]
        board = Board(board_payload["width"], board_payload["height"])
        for piece_payload in board_payload["pieces"]:
            piece = piece_from_dict(piece_payload)
            board.add_piece(piece.cell, piece)
        engine.board = board
        engine.arbiter.active_motions = [
            motion_from_dict(motion_payload)
            for motion_payload in payload.get("active_motions", [])
        ]
        engine.arbiter.elapsed_time_ms = int(payload.get("elapsed_time_ms", 0))
        engine.game_over = bool(payload.get("game_over", False))
        self.game_over = engine.game_over
        players = payload.get("players", {})
        self.scores = {
            ROLE_WHITE: players.get(ROLE_WHITE, {}).get("score", 0),
            ROLE_BLACK: players.get(ROLE_BLACK, {}).get("score", 0),
        }

    def tick(self, engine: RemoteEngineView, tick_duration_ms: int = TICK_DURATION_MS) -> None:
        engine.arbiter.elapsed_time_ms += tick_duration_ms
        self.animation_tick += 1
        for timers in (self.rest_timers, self.short_rest_timers, self.jump_timers):
            for pos in list(timers):
                timers[pos] -= 1
                if timers[pos] <= 0:
                    del timers[pos]

    def apply_message(self, engine: RemoteEngineView, message: dict) -> None:
        message_type = message.get("type")
        payload = message.get("payload", {})
        if message_type in {MESSAGE_LOGIN_ACK, MESSAGE_SNAPSHOT} and "snapshot" in payload:
            self.apply_snapshot(engine, payload["snapshot"])
        elif message_type == MESSAGE_SNAPSHOT:
            self.apply_snapshot(engine, payload)
        elif message_type == MESSAGE_MOVE_REQUESTED:
            self._apply_move_requested(engine, payload)
        elif message_type == MESSAGE_MOVE_RESOLVED:
            self._apply_move_resolved(engine, payload)
        elif message_type == MESSAGE_GAME_OVER:
            engine.game_over = True
            self.game_over = True

    def _apply_move_requested(self, engine: RemoteEngineView, payload: dict) -> None:
        if not payload.get("accepted") or "motion" not in payload:
            return
        engine.arbiter.elapsed_time_ms = int(payload.get("elapsed_time_ms", engine.arbiter.elapsed_time_ms))
        motion = motion_from_dict(payload["motion"])
        engine.arbiter.active_motions = [
            existing
            for existing in engine.arbiter.active_motions
            if existing.order != motion.order
        ]
        engine.arbiter.active_motions.append(motion)

    def _apply_move_resolved(self, engine: RemoteEngineView, payload: dict) -> None:
        engine.arbiter.elapsed_time_ms = int(payload.get("elapsed_time_ms", engine.arbiter.elapsed_time_ms))
        motion = motion_from_dict(payload["motion"])
        engine.arbiter.active_motions = [
            existing
            for existing in engine.arbiter.active_motions
            if existing.order != motion.order
        ]
        source = motion.source
        destination = motion.destination
        moving_piece = engine.board.get_piece(source)
        if moving_piece is not None:
            engine.board.remove_piece(source)
        captured_payload = payload.get("captured")
        if captured_payload is not None:
            target_position = Position(
                row=int(captured_payload["cell"]["row"]),
                col=int(captured_payload["cell"]["col"]),
            )
            target_piece = engine.board.get_piece(target_position)
            if target_piece is not None:
                engine.board.remove_piece(target_position)
        final_piece = piece_from_dict(payload["piece"])
        final_position = Position(
            row=int(payload["final_position"]["row"]),
            col=int(payload["final_position"]["col"]),
        )
        existing_piece = engine.board.get_piece(final_position)
        if existing_piece is not None:
            engine.board.remove_piece(final_position)
        engine.board.add_piece(final_position, final_piece)
        self.rest_timers[final_position] = REST_TICKS
        self.move_log.append({
            "color": final_piece.color,
            "time": self._format_elapsed(engine.arbiter.elapsed_time_ms / 1000),
            "notation": move_notation(final_piece, source, destination, None if captured_payload is None else piece_from_dict(captured_payload)),
        })
        players = payload.get("players")
        if players:
            self.scores = {
                ROLE_WHITE: players.get(ROLE_WHITE, {}).get("score", self.scores[ROLE_WHITE]),
                ROLE_BLACK: players.get(ROLE_BLACK, {}).get("score", self.scores[ROLE_BLACK]),
            }
        self.game_over = bool(payload.get("game_over", False))
        engine.game_over = self.game_over

    def _format_elapsed(self, seconds: float) -> str:
        minutes = int(seconds // 60)
        seconds_rem = seconds - minutes * 60
        return f"{minutes:02d}:{seconds_rem:05.2f}"


class RemoteController:
    def __init__(self, engine: RemoteEngineView, state: RemoteGameState, send_move):
        self.engine = engine
        self.state = state
        self.send_move = send_move
        self.selected: Optional[Position] = None

    def click(self, position: Position) -> Optional[str]:
        piece = self.engine.board.get_piece(position)
        if self.selected is None:
            if self.state.local_color is None:
                return REASON_OBSERVER_READ_ONLY
            if piece is None or piece.color != self.state.local_color:
                return REASON_WRONG_PLAYER_COLOR
            self.selected = position
            return None

        if self.selected == position:
            self.selected = None
            return None

        selected_piece = self.engine.board.get_piece(self.selected)
        if selected_piece is None:
            self.selected = None
            return REASON_EMPTY_SOURCE
        if selected_piece.color != self.state.local_color:
            self.selected = None
            return REASON_WRONG_PLAYER_COLOR
        self.send_move(self.selected, position)
        self.selected = None
        return REASON_OK
