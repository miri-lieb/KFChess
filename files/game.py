from typing import List, Optional, Tuple

from config import CELL_SIZE, COMMAND_CLICK, COMMAND_JUMP, COMMAND_PRINT_BOARD, COMMAND_WAIT, MOVE_DURATION_MS
from move_rules import is_move_legal
from board import Board


class Game:
    def __init__(self, board: Board):
        self.board = board
        self.time = 0
        self.selected: Optional[Tuple[int, int]] = None
        self.pending_moves: List[dict] = []
        self.pending_jump: Optional[dict] = None

    def apply_command(self, command: str) -> None:
        if command == COMMAND_PRINT_BOARD:
            self.print_board()
            return

        tokens = command.split()
        if not tokens:
            return

        verb = tokens[0]
        if verb == COMMAND_WAIT and len(tokens) == 2:
            self.wait(int(tokens[1]))
            return

        if verb == COMMAND_JUMP:
            if len(tokens) == 3:
                self.jump(int(tokens[1]), int(tokens[2]))
            elif len(tokens) == 1 and self.selected is not None:
                self.jump(self.selected[0], self.selected[1])
            return

        if verb == COMMAND_CLICK and len(tokens) == 3:
            self.click(int(tokens[1]), int(tokens[2]))
            return

    def click(self, x: int, y: int) -> None:
        row = y // CELL_SIZE
        col = x // CELL_SIZE

        if not self.board.is_valid_position(row, col):
            return

        piece = self.board.get(row, col)

        if self.selected is None:
            if piece is not None and not self._is_moving(row, col):
                self.selected = (row, col)
            return

        old_row, old_col = self.selected
        old_piece = self.board.get(old_row, old_col)
        if old_piece is None:
            self.selected = None
            return

        if piece is not None and piece.color == old_piece.color:
            if not self._is_moving(row, col):
                self.selected = (row, col)
            else:
                self.selected = None
            return

        if self.pending_jump is not None and self.pending_jump['r1'] == old_row and self.pending_jump['c1'] == old_col:
            # כלי קופץ לא יכול לבצע מהלך רגיל עד שינחת
            return

        if is_move_legal(self.board, old_row, old_col, row, col):
            self.pending_moves.append({
                'r1': old_row,
                'c1': old_col,
                'r2': row,
                'c2': col,
                'arrival': self.time + MOVE_DURATION_MS,
            })

        self.selected = None

    def _is_moving(self, row: int, col: int) -> bool:
        if self.pending_jump is not None and self.pending_jump['r1'] == row and self.pending_jump['c1'] == col:
            return True
        return any(move['r1'] == row and move['c1'] == col for move in self.pending_moves)

    def _resolve_pending_moves(self) -> None:
        still_pending = []
        for move in self.pending_moves:
            if self.time >= move['arrival']:
                destination_row = move['r2']
                destination_col = move['c2']
                origin_row = move['r1']
                origin_col = move['c1']
                if self.pending_jump is not None and \
                   destination_row == self.pending_jump['r1'] and \
                   destination_col == self.pending_jump['c1']:
                    attacker = self.board.get(origin_row, origin_col)
                    airborne = self.board.get(destination_row, destination_col)
                    if attacker is not None and airborne is not None and attacker.color != airborne.color:
                        self.board.set(origin_row, origin_col, None)
                        continue
                destination_piece = self.board.get(origin_row, origin_col)
                self.board.set(destination_row, destination_col, destination_piece)
                self.board.set(origin_row, origin_col, None)
            else:
                still_pending.append(move)
        self.pending_moves = still_pending

    def _resolve_pending_jump(self) -> None:
        if self.pending_jump is None:
            return

        if self.time >= self.pending_jump['arrival']:
            self.pending_jump = None

    def wait(self, ms: int) -> None:
        self.time += ms
        self._resolve_pending_moves()
        self._resolve_pending_jump()

    def print_board(self) -> None:
        self._resolve_pending_moves()
        self._resolve_pending_jump()
        self.board.print_board()

    def jump(self, x: int, y: int) -> None:
        row = y // CELL_SIZE
        col = x // CELL_SIZE

        if not self.board.is_valid_position(row, col):
            return

        if self.pending_jump is not None:
            return

        piece = self.board.get(row, col)
        if piece is None:
            return

        if self._is_moving(row, col):
            return

        self.pending_jump = {
            'r1': row,
            'c1': col,
            'arrival': self.time + MOVE_DURATION_MS,
        }
        self.selected = None
