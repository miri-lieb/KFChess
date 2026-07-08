from typing import List, Optional

from is_valid_pawn_move import is_valid_pawn_move


class Piece:
    COLORS = {'w', 'b'}
    TYPES = {'K', 'Q', 'R', 'B', 'N', 'P'}

    def __init__(self, color: str, type_: str):
        self.color = color
        self.type = type_

    @property
    def token(self) -> str:
        return f"{self.color}{self.type}"

    @classmethod
    def from_token(cls, token: str) -> Optional['Piece']:
        if token == '.':
            return None
        if len(token) != 2:
            return None
        color, type_ = token[0], token[1]
        if color not in cls.COLORS or type_ not in cls.TYPES:
            return None
        return cls(color, type_)

    def is_same_color(self, other: Optional['Piece']) -> bool:
        return other is not None and self.color == other.color

    def is_legal_move(self, r1: int, c1: int, r2: int, c2: int) -> bool:
        dr = abs(r2 - r1)
        dc = abs(c2 - c1)
        if self.type == 'K':
            return max(dr, dc) == 1
        if self.type == 'R':
            return (dr > 0 and dc == 0) or (dr == 0 and dc > 0)
        if self.type == 'B':
            return dr == dc and dr > 0
        if self.type == 'Q':
            return (dr == 0 or dc == 0 or dr == dc) and (dr > 0 or dc > 0)
        if self.type == 'N':
            return (dr == 1 and dc == 2) or (dr == 2 and dc == 1)
        if self.type == 'P':
            return True
        return False


class Board:
    def __init__(self, grid: List[List[Optional[Piece]]]):
        self.grid = grid

    @classmethod
    def from_lines(cls, board_lines: List[str]) -> Optional['Board']:
        grid: List[List[Optional[Piece]]] = []
        expected_width = None

        for line in board_lines:
            tokens = line.split()
            if not tokens:
                continue

            if expected_width is None:
                expected_width = len(tokens)
            elif len(tokens) != expected_width:
                print("ERROR ROW_WIDTH_MISMATCH")
                return None

            row: List[Optional[Piece]] = []
            for token in tokens:
                piece = Piece.from_token(token)
                if token != '.' and piece is None:
                    print("ERROR UNKNOWN_TOKEN")
                    return None
                row.append(piece)
            grid.append(row)

        return cls(grid)

    @classmethod
    def parse_and_validate_board(cls, board_lines: List[str]) -> Optional['Board']:
        return cls.from_lines(board_lines)

    @property
    def height(self) -> int:
        return len(self.grid)

    @property
    def width(self) -> int:
        return len(self.grid[0]) if self.grid else 0

    def get(self, row: int, col: int) -> Optional[Piece]:
        return self.grid[row][col]

    def set(self, row: int, col: int, piece: Optional[Piece]) -> None:
        self.grid[row][col] = piece

    def is_valid_position(self, row: int, col: int) -> bool:
        return 0 <= row < self.height and 0 <= col < self.width

    def is_path_clear(self, r1: int, c1: int, r2: int, c2: int) -> bool:
        step_r = (r2 > r1) - (r2 < r1)
        step_c = (c2 > c1) - (c2 < c1)
        curr_r = r1 + step_r
        curr_c = c1 + step_c
        while (curr_r, curr_c) != (r2, c2):
            if self.grid[curr_r][curr_c] is not None:
                return False
            curr_r += step_r
            curr_c += step_c
        return True

    def is_valid_move(self, r1: int, c1: int, r2: int, c2: int) -> bool:
        current_piece = self.get(r1, c1)
        target_piece = self.get(r2, c2)
        if current_piece is None:
            return False
        if target_piece is not None and current_piece.is_same_color(target_piece):
            return False

        if current_piece.type == 'P':
            return is_valid_pawn_move(self, r1, c1, r2, c2)
        if current_piece.type in ('K', 'N'):
            return True
        return self.is_path_clear(r1, c1, r2, c2)

    def display(self) -> None:
        for row in self.grid:
            print(' '.join(piece.token if piece is not None else '.' for piece in row))


def parse_and_validate_board(board_lines: List[str]) -> Optional[Board]:
    return Board.parse_and_validate_board(board_lines)
