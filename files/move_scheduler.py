from dataclasses import dataclass
from typing import Optional

from board import Board
from piece import Piece
from pawn_rules import promote_if_needed


@dataclass
class PendingMove:
    """מהלך שעדיין בתנועה (לא הסתיים) - הכלי עדיין מוצג בתא המקור עד שהזמן נגמר."""
    piece: str
    from_row: int
    from_col: int
    to_row: int
    to_col: int
    remaining_time: int


class JumpState:
    """מייצג כלי שנמצא 'באוויר' (קפץ) ומחכה 1000ms לפני שהוא נוחת בחזרה."""

    def __init__(self, row: int, col: int, remaining_time: int = 1000):
        self.row = row
        self.col = col
        self.remaining_time = remaining_time


class MoveScheduler:
    """אחראי על יצירת מהלכים ממתינים ועל התקדמות הזמן שלהם (tick)."""

    def __init__(self, board: Board):
        self.board = board

    def schedule_move(self, from_row: int, from_col: int, to_row: int, to_col: int) -> PendingMove:
        """יוצר מהלך ממתין חדש, שיסתיים כעבור 1000ms."""
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
        """
        מקדם את הזמן של מהלך ממתין. אם הזמן נגמר - מיישם את המהלך בפועל על הלוח,
        כולל טיפול בהתנגשות עם כלי קופץ (jump) ובתפיסת מלך (סיום משחק).
        """
        if pending_move is None:
            return None

        pending_move.remaining_time -= elapsed
        if pending_move.remaining_time <= 0:
            arriving_piece = Piece.from_token(pending_move.piece)
            if arriving_piece is None:
                self.board.set(pending_move.from_row, pending_move.from_col, None)
                return None

            # אם יש כלי קופץ באותו תא יעד, והוא יריב - הוא תופס את הכלי המגיע באוויר
            if pending_jump is not None and pending_jump.row == pending_move.to_row and pending_jump.col == pending_move.to_col:
                airborne_piece = self.board.get(pending_jump.row, pending_jump.col)
                if airborne_piece is not None and airborne_piece.color != arriving_piece.color:
                    if arriving_piece.type == 'K':
                        # מלך "שנתפס באוויר" מסיים את המשחק
                        self.board.game_over = True
                    self.board.set(pending_move.from_row, pending_move.from_col, None)
                    return None

            # תפיסת מלך רגילה (לא דרך קפיצה) מסיימת את המשחק
            captured_piece = self.board.get(pending_move.to_row, pending_move.to_col)
            if captured_piece is not None and captured_piece.type == 'K' and arriving_piece.color != captured_piece.color:
                self.board.game_over = True

            if pending_jump is None or pending_jump.row != pending_move.to_row or pending_jump.col != pending_move.to_col:
                # אין התנגשות עם קפיצה - הכלי נוחת רגיל, כולל בדיקת הכתרה לפאון
                settled_piece = promote_if_needed(arriving_piece, pending_move.to_row, self.board)
                self.board.set(pending_move.to_row, pending_move.to_col, settled_piece)
                self.board.set(pending_move.from_row, pending_move.from_col, None)
            else:
                # הכלי המגיע נתפס באוויר - רק מנקים את תא המקור, בלי להציב אותו ביעד
                self.board.set(pending_move.from_row, pending_move.from_col, None)

            return None

        return pending_move
