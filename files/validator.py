from typing import List, Optional

from config import VALID_TOKENS


def validate(board_lines: Optional[List[str]]) -> Optional[str]:
    if board_lines is None or len(board_lines) == 0:
        return None

    width = None
    for line in board_lines:
        tokens = line.split()
        if width is None:
            width = len(tokens)
        elif len(tokens) != width:
            return "ERROR ROW_WIDTH_MISMATCH"

        for token in tokens:
            if token not in VALID_TOKENS:
                return "ERROR UNKNOWN_TOKEN"

    return None
