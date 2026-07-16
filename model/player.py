from dataclasses import dataclass, field
from typing import List, Optional

from model.piece import Piece

@dataclass
class Player:
    color: str
    name: Optional[str] = None
    captured_pieces: List[Piece] = field(default_factory=list)
    def capture(self, piece: Piece) -> None:
        self.captured_pieces.append(piece)