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


class JumpState:
    def __init__(self, row: int, col: int, remaining_time: int = 1000):
        self.row = row
        self.col = col
        self.remaining_time = remaining_time


class MoveScheduler:
    def __init__(self, board: Board):
        self.board = board

    def schedule_move(self, from_row: int, from_col: int, to_row: int, to_col: int) -> PendingMove:
        duration = 1000
        piece = self.board.get(from_row, from_col)
        return PendingMove(
            piece=piece.token if piece is not None else '.',
            from_row=from_row,
            from_col=from_col,
            to_row=to_row,
            to_col=to_col,
            remaining_time=duration,
        )

    def tick(self, pending_move: Optional[PendingMove], pending_jump: Optional[JumpState], elapsed: int = 1) -> Optional[PendingMove]:
        if pending_move is None:
            return None

        pending_move.remaining_time -= elapsed
        if pending_move.remaining_time <= 0:
            arriving_piece = Piece.from_token(pending_move.piece)
            if arriving_piece is None:
                self.board.set(pending_move.from_row, pending_move.from_col, None)
                return None

            if pending_jump is not None and pending_jump.row == pending_move.to_row and pending_jump.col == pending_move.to_col:
                airborne_piece = self.board.get(pending_jump.row, pending_jump.col)
                if airborne_piece is not None and airborne_piece.color != arriving_piece.color:
                    if arriving_piece.type == 'K':
                        self.board.game_over = True
                    self.board.set(pending_move.from_row, pending_move.from_col, None)
                    return None

            captured_piece = self.board.get(pending_move.to_row, pending_move.to_col)
            if captured_piece is not None and captured_piece.type == 'K' and arriving_piece.color != captured_piece.color:
                self.board.game_over = True

            if pending_jump is None or pending_jump.row != pending_move.to_row or pending_jump.col != pending_move.to_col:
                self.board.set(pending_move.to_row, pending_move.to_col, arriving_piece)
                self.board.set(pending_move.from_row, pending_move.from_col, None)
            else:
                self.board.set(pending_move.from_row, pending_move.from_col, None)

            return None

        return pending_move


class GameController:
    def __init__(self, board: Board):
        self.board = board
        self.selected_pos: Optional[Tuple[int, int]] = None
        self.pending_move: Optional[PendingMove] = None
        self.pending_jump: Optional[JumpState] = None
        self.scheduler = MoveScheduler(board)

    @property
    def is_moving(self) -> bool:
        return self.pending_move is not None

    @property
    def is_airborne(self) -> bool:
        return self.pending_jump is not None

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

    def parse_jump_command(self, command: str) -> Optional[Tuple[int, int]]:
        parts = command.split()
        if parts[0] != 'jump':
            return None
        if len(parts) == 1:
            return self.selected_pos
        if len(parts) == 3:
            try:
                x = int(parts[1])
                y = int(parts[2])
            except ValueError:
                return None
            return y // 100, x // 100
        return None

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
        if self.board.game_over:
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

        if self.pending_jump is not None and self.selected_pos == (self.pending_jump.row, self.pending_jump.col):
            return

        if self.is_moving:
            return

        action = self.resolve_click_action(row, col)
        if action == 'select':
            self.selected_pos = (row, col)
        elif action == 'move':
            self.pending_move = self.scheduler.schedule_move(self.selected_pos[0], self.selected_pos[1], row, col)
            self.selected_pos = None
        else:
            if target_piece is not None:
                self.selected_pos = (row, col)
            else:
                self.selected_pos = None

    def handle_jump(self, command: str) -> None:
        if self.board.game_over:
            return

        jump_position = self.parse_jump_command(command)
        if jump_position is None:
            return

        if not self.board.is_valid_position(jump_position[0], jump_position[1]):
            return

        if self.pending_jump is not None:
            return

        current_piece = self.board.get(jump_position[0], jump_position[1])
        if current_piece is None:
            return

        if self.pending_move is not None and self.pending_move.from_row == jump_position[0] and self.pending_move.from_col == jump_position[1]:
            return

        self.pending_jump = JumpState(jump_position[0], jump_position[1])
        self.selected_pos = None

    def handle_wait(self, command: str) -> None:
        if self.board.game_over:
            return
        elapsed = self.parse_wait_command(command)
        self.pending_move = self.scheduler.tick(self.pending_move, self.pending_jump, elapsed)
        if self.pending_move is not None and self.pending_move.remaining_time <= 0:
            self.pending_move = None
        if self.pending_jump is not None:
            self.pending_jump.remaining_time -= elapsed
            if self.pending_jump.remaining_time <= 0:
                self.pending_jump = None

    def process_commands(self, commands: List[str]) -> None:
        for command in commands:
            if command.startswith('click'):
                self.handle_click(command)
            elif command.startswith('jump'):
                self.handle_jump(command)
            elif command.startswith('wait'):
                self.handle_wait(command)
            elif command == 'print board':
                self.board.display()


def process_game_commands(parsed_board: Board, commands: List[str]) -> None:
    GameController(parsed_board).process_commands(commands)
