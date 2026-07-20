from typing import Optional

from config import ROLE_WHITE, ROLE_BLACK
from model.board import BoardRepresentation
from model.piece import KING
from .interfaces import WinConditionChecker, WinResult


class StandardWinChecker:
    def check(self, board: BoardRepresentation) -> Optional[WinResult]:
        kings = {ROLE_WHITE: 0, ROLE_BLACK: 0}
        for pos, piece in board.iter_pieces():
            if piece.kind == KING:
                kings[piece.color] = kings.get(piece.color, 0) + 1
        if kings.get(ROLE_WHITE, 0) == 0 and kings.get(ROLE_BLACK, 0) > 0:
            return WinResult(winner_color=ROLE_BLACK, reason="king_missing_white")
        if kings.get(ROLE_BLACK, 0) == 0 and kings.get(ROLE_WHITE, 0) > 0:
            return WinResult(winner_color=ROLE_WHITE, reason="king_missing_black")
        return None