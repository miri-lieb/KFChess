from is_legal_move import is_legal_move
from print_board import print_board
from is_valid_move import is_valid_move

def process_game_commands(parsed_board, commands):
    height = len(parsed_board)
    width = len(parsed_board[0]) if height > 0 else 0
    selected_pos = None
    for cmd in commands:
        if cmd.startswith("click"):
            parts = cmd.split()
            if len(parts) != 3:
                continue
            try:
                x = int(parts[1])
                y = int(parts[2])
            except ValueError:
                continue
                
            col = x // 100
            row = y // 100
            if not (0 <= row < height and 0 <= col < width):
                continue

            target = parsed_board[row][col]

            if target != '.':
                if selected_pos is None:
                    selected_pos = (row, col)
                else:
                    current_piece = parsed_board[selected_pos[0]][selected_pos[1]]
                    if target[0] == current_piece[0]:
                        selected_pos = (row, col)
                    else:
                        if is_legal_move(current_piece, selected_pos[0], selected_pos[1], row, col) and \
                           is_valid_move(parsed_board, selected_pos[0], selected_pos[1], row, col):
                            parsed_board[row][col] = current_piece
                            parsed_board[selected_pos[0]][selected_pos[1]] = '.'
                            selected_pos = None
                        else:
                            selected_pos = None
            else:
                if selected_pos is not None:
                    current_piece = parsed_board[selected_pos[0]][selected_pos[1]]
                    if is_legal_move(current_piece, selected_pos[0], selected_pos[1], row, col) and \
                       is_valid_move(parsed_board, selected_pos[0], selected_pos[1], row, col):
                        parsed_board[row][col] = current_piece
                        parsed_board[selected_pos[0]][selected_pos[1]] = '.'
                        selected_pos = None
                    else:
                        selected_pos = None
                else:
                    continue
                    
        elif cmd.startswith("wait"):
            continue
        elif cmd == "print board":
            print_board(parsed_board)