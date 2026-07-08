from typing import List, Optional

from piece import Piece


class Board:
    """
    מייצג את מצב הלוח בלבד: הגריד, גודל, קריאה/כתיבה לתאים והדפסה.
    בכוונה לא מכיל חוקי תנועה של שח - אלה נמצאים ב-movement_rules.py.
    כך Board נשאר "טיפש" ומתמקד רק באחסון המצב.
    """

    def __init__(self, grid: List[List[Optional[Piece]]]):
        self.grid = grid
        self.game_over = False

    @classmethod
    def from_lines(cls, board_lines: List[str]) -> Optional['Board']:
        """מפרסר רשימת שורות טקסט לאובייקט Board. מחזיר None ומדפיס שגיאה אם הקלט לא תקין."""
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
        """בודק שהקואורדינטות בתוך גבולות הלוח."""
        return 0 <= row < self.height and 0 <= col < self.width

    def is_path_clear(self, r1: int, c1: int, r2: int, c2: int) -> bool:
        """
        בודק שכל התאים שבין (r1,c1) ל-(r2,c2) ריקים (לא כולל נקודת ההתחלה והסיום).
        זו פונקציית עזר גנרית על הגריד, לא חוק שח ספציפי - לכן נשארה כאן ולא ב-movement_rules.
        """
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

    def print_board(self) -> None:
        """מדפיס את מצב הלוח הנוכחי בפורמט הטקסטואלי (טוקן לכל תא, מופרד ברווחים)."""
        for row in self.grid:
            print(' '.join(piece.token if piece is not None else '.' for piece in row))

    display = print_board


def parse_and_validate_board(board_lines: List[str]) -> Optional[Board]:
    return Board.parse_and_validate_board(board_lines)
