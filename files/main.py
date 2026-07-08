import sys

from board import parse_and_validate_board
from game_controller import process_game_commands


def parse_input(lines):
    """מפריד את שורות הקלט לשני חלקים: שורות הלוח ורשימת הפקודות, לפי הכותרות 'Board:' ו-'Commands:'."""
    board_lines = []
    commands = []
    section = None

    for line in lines:
        if line.startswith('Board:'):
            section = 'board'
            continue

        if line.startswith('Commands:'):
            section = 'commands'
            continue

        if section == 'board':
            board_lines.append(line)
        elif section == 'commands':
            commands.append(line)

    return board_lines, commands


def main():
    raw_lines = [line.strip() for line in sys.stdin if line.strip()]
    board_lines, commands = parse_input(raw_lines)
    if not board_lines:
        return

    parsed_board = parse_and_validate_board(board_lines)
    if parsed_board is None:
        return

    process_game_commands(parsed_board, commands)


if __name__ == '__main__':
    main()
