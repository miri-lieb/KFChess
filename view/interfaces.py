"""View layer interfaces (Protocols) for decoupling the renderer from game logic."""

from typing import Protocol, Optional, Set, Any
from dataclasses import dataclass
from model.position import Position
from model.board import BoardRepresentation
from model.piece import Piece
from realtime.motion import Motion


@dataclass
class GameSnapshot:
    """Read-only snapshot of game state for rendering."""
    rest_timers: dict
    short_rest_timers: dict
    jump_timers: dict
    move_log: list
    legal_moves: Set[Position]
    scores: dict
    game_over: bool
    animation_tick: int


class EngineView(Protocol):
    """Read-only view of the game engine for rendering."""
    board: BoardRepresentation
    arbiter: Any  # RealTimeArbiterView
    game_over: bool
    
    def wait(self, ms: int) -> list: ...


class ArbiterView(Protocol):
    """Read-only view of the real-time arbiter."""
    active_motions: list[Motion]
    elapsed_time_ms: int


class ControllerView(Protocol):
    """Read-only view of the controller."""
    selected: Optional[Position]


class Renderer(Protocol):
    """Renderer interface."""
    def render(self, engine: EngineView, controller: ControllerView, state: GameSnapshot): ...
    def handle_input(self, controller: ControllerView, engine: EngineView, state: GameSnapshot) -> bool: ...
    def cleanup(self): ...