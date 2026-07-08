from dataclasses import dataclass
from typing import List, Optional, Tuple

from board import Board, Piece


@dataclass
class PendingMove:
    piece: str
    from_row: int
    from_col: int
    to_row: int
    to_col: int
    remaining_time: int


class MoveScheduler:
    def __init__(self, board: Board):
        self.board = board

    def schedule_move(self, from_row: int, from_col: int, to_row: int, to_col: int) -> PendingMove:
        distance = max(abs(to_row - from_row), abs(to_col - from_col))
        duration = distance * 1000
        piece = self.board.get(from_row, from_col)
        return PendingMove(
            piece=piece.token if piece is not None else '.',
            from_row=from_row,
            from_col=from_col,
            to_row=to_row,
            to_col=to_col,
            remaining_time=duration,
        )

    def tick(self, pending_move: Optional[PendingMove], elapsed: int = 1) -> Optional[PendingMove]:
        if pending_move is None:
            return None

        pending_move.remaining_time -= elapsed
        if pending_move.remaining_time <= 0:
            self.board.set(pending_move.to_row, pending_move.to_col, Piece.from_token(pending_move.piece))
            self.board.set(pending_move.from_row, pending_move.from_col, None)
            return None

        return pending_move


class GameController:
    def __init__(self, board: Board):
        self.board = board
        self.selected_pos: Optional[Tuple[int, int]] = None
        self.pending_move: Optional[PendingMove] = None
        self.scheduler = MoveScheduler(board)

    def parse_click_command(self, command: str) -> Optional[Tuple[int, int]]:
        parts = command.split()
        if len(parts) != 3 or parts[0] != 'click':
            return None

        try:
            x = int(parts[1])
            y = int(parts[2])
        except ValueError:
            return None

        return y // 100, x // 100

    def parse_wait_command(self, command: str) -> int:
        parts = command.split()
        if len(parts) != 2 or parts[0] != 'wait':
            return 1
        try:
            return int(parts[1])
        except ValueError:
            return 1

    def resolve_click_action(self, row: int, col: int) -> Optional[str]:
        if self.selected_pos is None:
            return None

        current_piece = self.board.get(self.selected_pos[0], self.selected_pos[1])
        if current_piece is None:
            return None

        target_piece = self.board.get(row, col)
        if target_piece is not None and current_piece.is_same_color(target_piece):
            return 'select'

        if current_piece.is_legal_move(self.selected_pos[0], self.selected_pos[1], row, col) and \
           self.board.is_valid_move(self.selected_pos[0], self.selected_pos[1], row, col):
            return 'move'

        return None

    def handle_click(self, command: str) -> None:
        if self.pending_move is not None:
            return

        click_position = self.parse_click_command(command)
        if click_position is None:
            return

        row, col = click_position
        if not self.board.is_valid_position(row, col):
            return

        target_piece = self.board.get(row, col)
        if target_piece is not None and self.selected_pos is None:
            self.selected_pos = (row, col)
            return

        if self.selected_pos is None:
            return

        action = self.resolve_click_action(row, col)
        if action == 'select':
            self.selected_pos = (row, col)
        elif action == 'move':
            self.pending_move = self.scheduler.schedule_move(self.selected_pos[0], self.selected_pos[1], row, col)
            self.selected_pos = None
        else:
            self.selected_pos = None

    def handle_wait(self, command: str) -> None:
        elapsed = self.parse_wait_command(command)
        self.pending_move = self.scheduler.tick(self.pending_move, elapsed)

    def process_commands(self, commands: List[str]) -> None:
        for command in commands:
            if command.startswith('click'):
                self.handle_click(command)
            elif command.startswith('wait'):
                self.handle_wait(command)
            elif command == 'print board':
                self.board.display()


def process_game_commands(parsed_board: Board, commands: List[str]) -> None:
    GameController(parsed_board).process_commands(commands)
