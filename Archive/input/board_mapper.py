from typing import Optional

from model.position import Position


def pixel_to_cell(x: int, y: int, cell_size: int = 100) -> Optional[Position]:
    if x < 0 or y < 0:
        return None
    return Position(y // cell_size, x // cell_size)
