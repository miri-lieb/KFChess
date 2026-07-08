from is_valid_pawn_move import is_valid_pawn_move
def is_valid_move(board, r1, c1, r2, c2):
    current_piece = board[r1][c1]
    target_piece = board[r2][c2]
    if target_piece != '.' and target_piece[0] == current_piece[0]:
        return False
    piece_type = current_piece[1]
    if piece_type == 'P':
        return is_valid_pawn_move(board, r1, c1, r2, c2)
    if piece_type in ('K', 'N'):
        return True
    step_r = (r2 > r1) - (r2 < r1)
    step_c = (c2 > c1) - (c2 < c1)
    curr_r = r1 + step_r
    curr_c = c1 + step_c
    while (curr_r, curr_c) != (r2, c2):
        if board[curr_r][curr_c] != '.':
            return False
        curr_r += step_r
        curr_c += step_c
    return True