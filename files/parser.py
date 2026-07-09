from typing import List, Tuple
from config import BOARD_HEADER, COMMANDS_HEADER

def parse_input(lines: List[str]) -> Tuple[List[str], List[str]]:
    board_lines: List[str] = []
    commands: List[str] = []
    reading_board = False
    reading_commands = False
    for line in lines:
        if line == BOARD_HEADER:
            reading_board = True
            reading_commands = False
            continue
        if line == COMMANDS_HEADER:
            reading_board = False
            reading_commands = True
            continue
        if reading_board and line:
            board_lines.append(line)
        elif reading_commands and line:
            commands.append(line)
    return board_lines, commands
