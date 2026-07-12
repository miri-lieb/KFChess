from dataclasses import dataclass
from typing import List, Optional

from model.position import Position


@dataclass
class PieceSnapshot:
    id: str
    color: str
    kind: str
    position: Position
    state: str


@dataclass
class GameSnapshot:
    width: int
    height: int
    pieces: List[PieceSnapshot]
    selected: Optional[Position]
    game_over: bool


class Renderer:
    def render(self, snapshot: GameSnapshot) -> None:
        # ממשק בסיסי לגרסת renderer, ניתן להרחיב עם גרפיקה מאוחרת יותר.
        print("Renderer.render: צבעתי פה רק ממשק ולא ממש UI אמיתי")
