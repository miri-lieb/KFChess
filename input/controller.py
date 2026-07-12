from typing import Optional

from engine.game_engine import GameEngine
from input.board_mapper import pixel_to_cell
from model.position import Position


class Controller:
    def __init__(self, engine: GameEngine):
        self.engine = engine
        self.selected: Optional[Position] = None

    def click(self, x: int, y: int) -> Optional[str]:
        position = pixel_to_cell(x, y)
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
