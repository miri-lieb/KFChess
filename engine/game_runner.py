import time
from typing import Optional, Callable
from dataclasses import dataclass, field

from engine.game_engine import GameEngine
from input.controller import Controller
from model.position import Position
from config import (
    TICK_DURATION_MS,
    REST_TICKS,
    SHORT_REST_TICKS,
    JUMP_TICKS,
    PIECE_VALUES,
)


@dataclass
class GameState:
    rest_timers: dict = field(default_factory=dict)
    short_rest_timers: dict = field(default_factory=dict)
    jump_timers: dict = field(default_factory=dict)
    move_log: list = field(default_factory=list)
    legal_moves: set = field(default_factory=set)
    scores: dict = field(default_factory=lambda: {"white": 0, "black": 0})
    start_time: float = field(default_factory=time.perf_counter)
    animation_tick: int = 0
    game_over: bool = False


@dataclass
class GameRunner:
    engine: GameEngine
    controller: Controller
    state: GameState = field(default_factory=GameState)
    tick_duration_ms: int = TICK_DURATION_MS

    def run(self, renderer: Optional[Callable] = None):
        """Main game loop. If renderer is provided, call it each frame."""
        try:
            while True:
                self.tick()
                if renderer:
                    renderer(self.engine, self.controller, self.state)
                if self.state.game_over:
                    break
        finally:
            if renderer:
                renderer.cleanup()

    def tick(self):
        # Advance time and process motion events
        motion_events = self.engine.wait(self.tick_duration_ms)
        for event in motion_events:
            motion = event["motion"]
            captured_piece = event["captured"]
            if captured_piece is not None:
                value = PIECE_VALUES.get(captured_piece.kind, 0)
                self.state.scores["black" if captured_piece.color == "white" else "white"] += value
            notation = self._move_notation(motion, captured_piece)
            self.state.move_log.append({
                "color": motion.piece.color,
                "time": self._format_elapsed(time.perf_counter() - self.state.start_time),
                "notation": notation,
            })
            self.state.rest_timers[motion.destination] = REST_TICKS

        # Update timers
        self._decrement_timers(self.state.rest_timers, REST_TICKS)
        self._decrement_timers(self.state.short_rest_timers, SHORT_REST_TICKS)
        self._decrement_timers(self.state.jump_timers, JUMP_TICKS)

        # Update legal moves
        self.state.legal_moves.clear()
        if self.controller.selected is not None:
            piece = self.engine.board.get_piece(self.controller.selected)
            if piece is not None:
                from rules.piece_rules import legal_destinations
                self.state.legal_moves.update(legal_destinations(self.engine.board, piece))

        self.state.game_over = self.engine.game_over
        self.state.animation_tick += 1

    def _move_notation(self, motion, captured) -> str:
        from view.input_handler import move_notation
        return move_notation(motion.piece, motion.source, motion.destination, captured)

    def _format_elapsed(self, seconds: float) -> str:
        minutes = int(seconds // 60)
        seconds_rem = seconds - minutes * 60
        return f"{minutes:02d}:{seconds_rem:05.2f}"

    def _decrement_timers(self, timers: dict, max_ticks: int):
        for pos in list(timers):
            timers[pos] -= 1
            if timers[pos] <= 0:
                del timers[pos]

    def handle_click(self, position: Position):
        """Process a click from the view layer."""
        from view.input_handler import on_mouse
        # Delegate to input handler logic
        pass