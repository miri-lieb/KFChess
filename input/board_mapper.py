from typing import Optional

from model.position import Position

def pixel_to_cell(x: int, y: int, cell_size: int = 100) -> Optional[Position]:
    # x,y are pixel coords relative to board origin. cell_size is pixel size of a cell
    if x < 0 or y < 0:
        return None
    col = int(x // cell_size)
    row = int(y // cell_size)
    if row < 0 or col < 0:
        return None
    return Position(row, col)