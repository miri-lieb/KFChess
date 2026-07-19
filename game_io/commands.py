from typing import List

from engine.game_engine import GameEngine
from input.controller import Controller
from model.position import Position
from game_io.board_printer import print_board

def run_commands(engine: GameEngine, controller: Controller, commands: List[str]) -> None:
    for raw_line in commands:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        command = parts[0].lower()
        if command == "click" and len(parts) == 3:
            x = int(parts[1])
            y = int(parts[2])
            controller.click(Position(x, y))
        elif command == "wait" and len(parts) == 2:
            ms = int(parts[1])
            engine.wait(ms)
        elif line.lower() == "print board":
            print_board(engine.board)
        else:
            raise ValueError(f"Unknown command: {line}")