import sys
from typing import List, Optional

from engine.game_engine import GameEngine
from input.controller import Controller
from game_io.board_parser import parse_board_lines
from game_io.board_printer import print_board

def split_sections(lines: List[str]) -> tuple[List[str], List[str]]:
    board_lines: List[str] = []
    command_lines: List[str] = []
    section: Optional[str] = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped == "Board:":
            section = "board"
            continue
        if stripped == "Commands:":
            section = "commands"
            continue

        if section == "board":
            board_lines.append(line)
        elif section == "commands":
            command_lines.append(line)
        else:
            raise ValueError("Input must start with 'Board:' followed by 'Commands:'")

    if not board_lines:
        raise ValueError("Missing board section")
    return board_lines, command_lines

def run_commands(engine: GameEngine, controller: Controller, commands: List[str]) -> None:
    for raw_line in commands:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split()
        command = parts[0].lower()

        if command == "click" and len(parts) == 3:
            # Text protocol uses board cell coordinates (row, col), 0-indexed
            from model.position import Position

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

def main() -> None:
    lines = [line.rstrip("\n") for line in sys.stdin]
    board_lines, command_lines = split_sections(lines)
    board = parse_board_lines(board_lines)

    engine = GameEngine(board)
    controller = Controller(engine)

    run_commands(engine, controller, command_lines)

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)