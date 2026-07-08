from typing import Optional

from move_context import MoveContext
from piece import Piece


def is_valid_pawn_move(context: MoveContext) -> bool:
    """
    בודק חוקיות מהלך פאון בהתחשב בצבע (כיוון תנועה הפוך ללבן ולשחור),
    תא התחלה, תפיסה אלכסונית וקפיצה כפולה משורת ההתחלה.
    """
    current_piece = context.current_piece
    if current_piece is None:
        return False

    target_piece = context.target_piece
    color = current_piece.color
    if target_piece is not None and target_piece.color == color:
        return False

    direction = context.direction
    start_row = context.board.height - 1 if color == 'w' else 0

    # תנועה רגילה - תא אחד קדימה, בלי תפיסה
    if context.from_col == context.to_col and context.to_row - context.from_row == direction:
        return target_piece is None

    # קפיצה כפולה - מותר רק משורת ההתחלה, והדרך חייבת להיות פנויה
    if context.from_col == context.to_col and context.to_row - context.from_row == 2 * direction:
        if context.from_row != start_row:
            return False
        return target_piece is None and context.board.is_path_clear(
            context.from_row, context.from_col, context.to_row, context.to_col
        )

    # תפיסה - אלכסון אחד קדימה, רק אם יש כלי יריב ביעד
    if abs(context.to_col - context.from_col) == 1 and context.to_row - context.from_row == direction:
        return target_piece is not None

    return False


def promote_if_needed(piece: Optional[Piece], row: int, board) -> Optional[Piece]:
    """
    בודק אם כלי שהגיע לתא מסוים הוא פאון שהגיע לשורה האחרונה שלו,
    ואם כן - מחזיר מלכה חדשה מאותו צבע במקומו (הכתרה).
    כל כלי אחר (או None) מוחזר ללא שינוי.
    """
    if piece is None or piece.type != 'P':
        return piece

    last_row = 0 if piece.color == 'w' else board.height - 1
    if row == last_row:
        return Piece(piece.color, 'Q')

    return piece
