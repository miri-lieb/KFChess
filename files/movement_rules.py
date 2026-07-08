from board import Board
from move_context import MoveContext
from pawn_rules import is_valid_pawn_move


def is_valid_move(board: Board, r1: int, c1: int, r2: int, c2: int) -> bool:
    """
    בודק אם מהלך חוקי בהתחשב *במצב הלוח* (חסימות בדרך, תפיסה עצמית וכו').
    זו שכבה נוספת מעל Piece.is_legal_move, שבודקת רק את צורת התנועה של הכלי
    בלי להתחשב בכלים אחרים על הלוח.
    """
    context = MoveContext(board=board, from_row=r1, from_col=c1, to_row=r2, to_col=c2)
    current_piece = context.current_piece
    target_piece = context.target_piece
    if current_piece is None:
        return False
    if target_piece is not None and current_piece.is_same_color(target_piece):
        # אסור לתפוס כלי מאותו הצבע
        return False

    if current_piece.type == 'P':
        # לפאון יש חוקי תנועה ייחודיים (כיוון, תפיסה אלכסונית, קפיצה כפולה)
        return is_valid_pawn_move(context)
    if current_piece.type in ('K', 'N'):
        # מלך ופרש לא צריכים דרך פנויה (פרש קופץ, מלך זז תא אחד בלבד)
        return True

    # רץ, רץ-פרוע ומלכה זקוקים לדרך פנויה בין ההתחלה ליעד
    return board.is_path_clear(r1, c1, r2, c2)
