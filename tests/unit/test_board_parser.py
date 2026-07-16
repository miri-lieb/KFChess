from game_io.board_parser import parse_board_lines
from game_io.board_printer import token_for_piece
from model.setup import standard_starting_board_lines
from model.position import Position


def test_board_parser_and_printer_roundtrip():
    # start from the standard starting board textual lines
    lines = standard_starting_board_lines()
    board = parse_board_lines(lines)
    # print tokens using board_printer.token_for_piece and re-create the textual lines
    printed_lines = []
    width = board.width
    for row in range(board.height):
        tokens = []
        for col in range(width):
            p = board.get_piece(Position(row, col))
            tokens.append(token_for_piece(p) if p is not None else ".")
        printed_lines.append(" ".join(tokens))

    assert printed_lines == lines
