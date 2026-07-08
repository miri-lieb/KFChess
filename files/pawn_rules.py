from typing import Optional

from piece import Piece


def is_valid_pawn_move(board, r1: int, c1: int, r2: int, c2: int) -> bool:
    """
    בודק חוקיות מהלך פאון בהתחשב בצבע (כיוון תנועה הפוך ללבן ולשחור),
    תא התחלה, תפיסה אלכסונית וקפיצה כפולה משורת ההתחלה.
    """
    current_piece = board.get(r1, c1)
    if current_piece is None:
        return False

    target_piece = board.get(r2, c2)
    color = current_piece.color
    if target_piece is not None and target_piece.color == color:
        return False

    # לבן זז כלפי מעלה (שורה קטנה יותר), שחור זז כלפי מטה
    direction = -1 if color == 'w' else 1
    start_row = board.height - 1 if color == 'w' else 0

    # תנועה רגילה - תא אחד קדימה, בלי תפיסה
    if c1 == c2 and r2 - r1 == direction:
        return target_piece is None

    # קפיצה כפולה - מותר רק משורת ההתחלה, והדרך חייבת להיות פנויה
    if c1 == c2 and r2 - r1 == 2 * direction:
        if r1 != start_row:
            return False
        return target_piece is None and board.is_path_clear(r1, c1, r2, c2)

    # תפיסה - אלכסון אחד קדימה, רק אם יש כלי יריב ביעד
    if abs(c2 - c1) == 1 and r2 - r1 == direction:
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
