import sys
from validate_board import parse_and_validate_board
from process_game_commands import process_game_commands

def main():
    raw_lines = [line.strip() for line in sys.stdin if line.strip()]
    
    board_lines = []
    commands = []
    in_board_section = False
    in_commands_section = False

    for line in raw_lines:
        if line.startswith("Board:"):
            in_board_section = True
            in_commands_section = False
            continue
        elif line.startswith("Commands:"):
            in_board_section = False
            in_commands_section = True
            continue
            
        if in_board_section:
            board_lines.append(line)
        elif in_commands_section:
            commands.append(line)

    if not board_lines:
        return

    # הרצת שלב 1: עיבוד ובדיקת תקינות הלוח
    parsed_board = parse_and_validate_board(board_lines)
    
    # אם הלוח לא תקין (הפונקציה הדפיסה שגיאה והחזירה None), עוצרים כאן
    if parsed_board is None:
        return

    # הרצת שלב 2: עיבוד הפקודות על הלוח שחזר
    process_game_commands(parsed_board, commands)


if __name__ == "__main__":
    main()