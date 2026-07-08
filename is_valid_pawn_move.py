def is_valid_pawn_move(board, r1, c1, r2, c2):
    current_piece = board[r1][c1]
    target_piece = board[r2][c2]
    color = current_piece[0]
    if target_piece != '.' and target_piece[0] == color:
        return False
    direction = -1 if color == 'w' else 1
    if c1 == c2 and r2 - r1 == direction:
        return target_piece == '.'
    elif abs(c2 - c1) == 1 and r2 - r1 == direction:
        return target_piece != '.'
    return False