import sys
from typing import List, Optional

from engine.game_engine import GameEngine
from input.controller import Controller
from game_io.board_parser import parse_board_lines
from game_io.commands import run_commands


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