from typing import Optional

from dataclasses import dataclass
from model.board import Board
from model.piece import KING

@dataclass
class WinResult:
    winner_color: str
    reason: str

def check_win_condition(board: Board) -> Optional[WinResult]:
    # If a king is missing for one side, the other side wins.
    # This is a simple check scanning for kings.
    kings = {"white": 0, "black": 0}
    for pos, piece in getattr(board, "_cells", {}).items():
        if piece.kind == KING:
            kings[piece.color] = kings.get(piece.color, 0) + 1
    if kings.get("white", 0) == 0 and kings.get("black", 0) > 0:
        return WinResult(winner_color="black", reason="king_missing_white")
    if kings.get("black", 0) == 0 and kings.get("white", 0) > 0:
        return WinResult(winner_color="white", reason="king_missing_black")
    return None