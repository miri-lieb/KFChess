from typing import Optional, Protocol
from model.position import Position
from model.board import BoardRepresentation


class EngineView(Protocol):
    board: BoardRepresentation
    game_over: bool
    def request_move(self, source: Position, destination: Position): ...


class Controller:
    def __init__(self, engine: EngineView):
        self.engine = engine
        self.selected: Optional[Position] = None

    def click(self, position: Position) -> Optional[str]:
        if position is None or not self.engine.board.is_in_bounds(position):
            if self.selected is not None:
                self.selected = None
            return None

        if self.selected is None:
            piece = self.engine.board.get_piece(position)
            if piece is not None:
                self.selected = position
            return None

        if self.selected == position:
            self.selected = None
            return None

        result = self.engine.request_move(self.selected, position)
        self.selected = None
        return result.reason
