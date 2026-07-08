from typing import List, Optional, Tuple

from board import Board
from movement_rules import is_valid_move
from move_scheduler import MoveScheduler, PendingMove, JumpState
from command_parser import parse_click_command, parse_wait_command, parse_jump_command


class GameController:
    """
    מנהל את מצב האינטראקציה בזמן אמת: מה נבחר כרגע, אילו מהלכים/קפיצות ממתינים,
    ומפרש פקודות (click / jump / wait / print board) ומפעיל אותן על הלוח.
    """

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

    def resolve_click_action(self, row: int, col: int) -> Optional[str]:
        """
        קובע מה קליק על תא מסוים אמור לעשות, בהינתן שיש כבר כלי נבחר:
        'select' - להחליף בחירה לכלי ידידותי אחר, 'move' - לשלוח בקשת מהלך, או None - להתעלם.
        """
        if self.selected_pos is None:
            return None

        current_piece = self.board.get(self.selected_pos[0], self.selected_pos[1])
        if current_piece is None:
            return None

        target_piece = self.board.get(row, col)
        if target_piece is not None and current_piece.is_same_color(target_piece):
            return 'select'

        # בדיקה כפולה: קודם צורת התנועה של הכלי, ואז חוקיות ביחס למצב הלוח (חסימות/תפיסות)
        if current_piece.is_legal_move(self.selected_pos[0], self.selected_pos[1], row, col) and \
           is_valid_move(self.board, self.selected_pos[0], self.selected_pos[1], row, col):
            return 'move'

        return None

    def handle_click(self, command: str) -> None:
        """מטפל בפקודת click: בחירת כלי, החלפת בחירה, או יצירת מהלך ממתין."""
        if self.board.game_over:
            return

        click_position = parse_click_command(command)
        if click_position is None:
            return

        row, col = click_position
        if not self.board.is_valid_position(row, col):
            return

        target_piece = self.board.get(row, col)
        if target_piece is not None and self.selected_pos is None:
            # אין בחירה קודמת - קליק על כלי בוחר אותו
            self.selected_pos = (row, col)
            return

        if self.selected_pos is None:
            # אין בחירה קודמת וקליק על תא ריק - מתעלמים
            return

        if self.pending_jump is not None and self.selected_pos == (self.pending_jump.row, self.pending_jump.col):
            # הכלי הנבחר כרגע נמצא באוויר - אי אפשר להזיז אותו
            return

        if self.is_moving:
            # יש כבר מהלך בתנועה - אי אפשר לתכנת מהלך נוסף במקביל
            return

        action = self.resolve_click_action(row, col)
        if action == 'select':
            self.selected_pos = (row, col)
        elif action == 'move':
            self.pending_move = self.scheduler.schedule_move(self.selected_pos[0], self.selected_pos[1], row, col)
            self.selected_pos = None
        else:
            # מהלך לא חוקי - אם התא לפחות מכיל כלי, נבחר אותו; אחרת מבטלים את הבחירה
            if target_piece is not None:
                self.selected_pos = (row, col)
            else:
                self.selected_pos = None

    def handle_jump(self, command: str) -> None:
        """מטפל בפקודת jump: מעביר כלי למצב 'באוויר' למשך 1000ms."""
        if self.board.game_over:
            return

        jump_position = parse_jump_command(command, self.selected_pos)
        if jump_position is None:
            return

        if not self.board.is_valid_position(jump_position[0], jump_position[1]):
            return

        if self.pending_jump is not None:
            # כבר יש כלי באוויר - אי אפשר לקפוץ שוב במקביל
            return

        current_piece = self.board.get(jump_position[0], jump_position[1])
        if current_piece is None:
            return

        if self.pending_move is not None and self.pending_move.from_row == jump_position[0] and self.pending_move.from_col == jump_position[1]:
            # כלי שכבר בתנועה לא יכול לקפוץ
            return

        self.pending_jump = JumpState(jump_position[0], jump_position[1])
        self.selected_pos = None

    def handle_wait(self, command: str) -> None:
        """מטפל בפקודת wait: מקדם את שעון המשחק, ומיישם מהלכים/קפיצות שהסתיימו."""
        if self.board.game_over:
            return
        elapsed = parse_wait_command(command)
        self.pending_move = self.scheduler.tick(self.pending_move, self.pending_jump, elapsed)
        if self.pending_move is not None and self.pending_move.remaining_time <= 0:
            self.pending_move = None
        if self.pending_jump is not None:
            self.pending_jump.remaining_time -= elapsed
            if self.pending_jump.remaining_time <= 0:
                self.pending_jump = None

    def process_commands(self, commands: List[str]) -> None:
        """מריץ רשימת פקודות אחת אחרי השנייה, לפי סוג הפקודה."""
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
