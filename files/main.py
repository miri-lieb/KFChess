import sys
from board import Board
from game import Game
from parser import parse_input
from validator import validate

def main():
    raw_lines = [line.strip() for line in sys.stdin if line.strip()]
    board_lines, commands = parse_input(raw_lines)
    if not board_lines:
        return
    error = validate(board_lines)
    if error is not None:
        print(error)
        return
    parsed_board = Board.from_lines(board_lines)
    if parsed_board is None:
        return
    game = Game(parsed_board)
    for command in commands:
        game.apply_command(command)
if __name__ == '__main__':
    main()