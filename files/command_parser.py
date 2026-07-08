from typing import Optional, Tuple

from config import CELL_SIZE, COMMAND_CLICK, COMMAND_JUMP, COMMAND_WAIT, DEFAULT_WAIT_MS


def parse_click_command(command: str) -> Optional[Tuple[int, int]]:
    """
    מפרסר פקודת 'click x y' לקואורדינטות תא (row, col).
    כל תא הוא CELL_SIZE x CELL_SIZE פיקסלים.
    מחזיר None אם הפורמט לא תקין.
    """
    parts = command.split()
    if len(parts) != 3 or parts[0] != COMMAND_CLICK:
        return None
    try:
        x = int(parts[1])
        y = int(parts[2])
    except ValueError:
        return None
    return y // CELL_SIZE, x // CELL_SIZE


def parse_wait_command(command: str) -> int:
    """מפרסר פקודת 'wait ms' ומחזיר את מספר המילישניות. ברירת מחדל DEFAULT_WAIT_MS אם הפורמט שגוי."""
    parts = command.split()
    if len(parts) != 2 or parts[0] != COMMAND_WAIT:
        return DEFAULT_WAIT_MS
    try:
        return int(parts[1])
    except ValueError:
        return DEFAULT_WAIT_MS


def parse_jump_command(command: str, selected_pos: Optional[Tuple[int, int]]) -> Optional[Tuple[int, int]]:
    """
    מפרסר פקודת 'jump' (קופץ עם הכלי הנבחר כרגע) או 'jump x y' (קפיצה מקואורדינטות מפורשות).
    selected_pos מועבר מבחוץ כי הפונקציה לא מכירה את מצב המשחק בעצמה.
    """
    parts = command.split()
    if parts[0] != COMMAND_JUMP:
        return None
    if len(parts) == 1:
        return selected_pos
    if len(parts) == 3:
        try:
            x = int(parts[1])
            y = int(parts[2])
        except ValueError:
            return None
        return y // CELL_SIZE, x // CELL_SIZE
    return None
