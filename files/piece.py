from typing import Optional


class Piece:
    """מייצג כלי בודד על הלוח: צבע + סוג. לא יודע כלום על מצב הלוח או חסימות."""
    COLORS = {'w', 'b'}
    TYPES = {'K', 'Q', 'R', 'B', 'N', 'P'}
    def __init__(self, color: str, type_: str):
        self.color = color
        self.type = type_
    @property
    def token(self):
        """הייצוג הטקסטואלי של הכלי, למשל 'wK' עבור מלך לבן."""
        return f"{self.color}{self.type}"
    @classmethod
    def from_token(cls, token: str):
        """הופך טוקן טקסטואלי (למשל 'bQ' או '.') לאובייקט Piece, או None אם התא ריק/לא תקין."""
        if token == '.':
            return None
        if len(token) != 2:
            return None
        color, type_ = token[0], token[1]
        if color not in cls.COLORS or type_ not in cls.TYPES:
            return None
        return cls(color, type_)

    def is_same_color(self, other: Optional['Piece']) -> bool:
        """בודק אם כלי אחר הוא מאותו הצבע (למשל כדי למנוע תפיסה עצמית)."""
        return other is not None and self.color == other.color

    def is_legal_move(self, r1: int, c1: int, r2: int, c2: int) -> bool:
        """
        בודק אם התנועה חוקית מבחינת *צורת* הכלי בלבד (לא בודק חסימות/תפיסות בדרך).
        למשל: מלך - תא אחד בכל כיוון, פרש - צורת L, וכו'.
        """
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
            # לפאון יש חוקים מיוחדים (כיוון, תפיסה אלכסונית וכו') הנבדקים בנפרד ב-pawn_rules.py
            return True
        return False
