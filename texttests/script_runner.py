from typing import List
from engine.game_engine import GameEngine
from input.controller import Controller
from game_io.board_parser import parse_board_lines


def run_script(lines: List[str]):
    board_lines = []
    commands = []
    section = None
    for line in lines:
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s == "Board:":
            section = "board"
            continue
        if s == "Commands:":
            section = "commands"
            continue
        if section == "board":
            board_lines.append(line)
        elif section == "commands":
            commands.append(line)
    board = parse_board_lines(board_lines)
    engine = GameEngine(board)
    controller = Controller(engine)
    # reuse main.run_commands logic by importing here to avoid duplication
    from main import run_commands
    run_commands(engine, controller, commands)
    return engine, controller
