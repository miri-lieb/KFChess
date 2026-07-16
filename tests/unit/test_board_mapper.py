from input.board_mapper import pixel_to_cell
from model.position import Position


def test_pixel_to_cell_basic():
    # cell size 100 -> pixel (150, 250) should map to col=1,row=2
    pos = pixel_to_cell(150, 250, cell_size=100)
    assert pos == Position(2, 1)


def test_pixel_to_cell_negative():
    assert pixel_to_cell(-5, 10, cell_size=50) is None
    assert pixel_to_cell(10, -1, cell_size=50) is None


def test_pixel_to_cell_with_board_offset():
    # simulate a board drawn at origin (board_x=50, board_y=20) with board width 800
    board_x = 50
    board_y = 20
    board_w = 800
    cell_size = board_w // 8

    # screen pixel coordinates of a click
    screen_x = board_x + 150
    screen_y = board_y + 250

    # view.input_handler subtracts board_x/board_y then calls pixel_to_cell
    rel_x = screen_x - board_x
    rel_y = screen_y - board_y

    pos = pixel_to_cell(rel_x, rel_y, cell_size=cell_size)
    assert pos == Position(2, 1)
