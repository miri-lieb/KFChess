from typing import Optional

from dataclasses import dataclass
from model.board import BoardRepresentation
from model.piece import KING
from .interfaces import WinConditionChecker, WinResult


class StandardWinChecker:
    def check(self, board: BoardRepresentation) -> Optional[WinResult]:
        kings = {"white": 0, "black": 0}
        for pos, piece in board.iter_pieces():
            if piece.kind == KING:
                kings[piece.color] = kings.get(piece.color, 0) + 1
        if kings.get("white", 0) == 0 and kings.get("black", 0) > 0:
            return WinResult(winner_color="black", reason="king_missing_white")
        if kings.get("black", 0) == 0 and kings.get("white", 0) > 0:
            return WinResult(winner_color="white", reason="king_missing_black")
        return None