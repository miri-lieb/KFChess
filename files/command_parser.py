from typing import Optional, Tuple
from config import SIZE_OF_SQUARE

def parse_click_command(command: str) -> Optional[Tuple[int, int]]:
    """
    מפרסר פקודת 'click x y' לקואורדינטות תא (row, col).
    כל תא הוא 100x100 פיקסלים, ולכן חלוקה שלמה ב-100 נותנת את מספר התא.
    מחזיר None אם הפורמט לא תקין.
    """
    parts = command.split()
    if len(parts) != 3 or parts[0] != 'click':
        return None

    try:
        x = int(parts[1])
        y = int(parts[2])
    except ValueError:
        return None

    return y // SIZE_OF_SQUARE, x // SIZE_OF_SQUARE


def parse_wait_command(command: str) -> int:
    """מפרסר פקודת 'wait ms' ומחזיר את מספר המילישניות. ברירת מחדל 1 אם הפורמט שגוי."""
    parts = command.split()
    if len(parts) != 2 or parts[0] != 'wait':
        return 1
    try:
        return int(parts[1])
    except ValueError:
        return 1

def parse_jump_command(command: str, selected_pos: Optional[Tuple[int, int]]) -> Optional[Tuple[int, int]]:
    """
    מפרסר פקודת 'jump' (קופץ עם הכלי הנבחר כרגע) או 'jump x y' (קפיצה מקואורדינטות מפורשות).
    selected_pos מועבר מבחוץ כי הפונקציה לא מכירה את מצב המשחק בעצמה.
    """
    parts = command.split()
    if parts[0] != 'jump':
        return None
    if len(parts) == 1:
        return selected_pos
    if len(parts) == 3:
        try:
            x = int(parts[1])
            y = int(parts[2])
        except ValueError:
            return None
        return y // SIZE_OF_SQUARE, x // SIZE_OF_SQUARE
    return None