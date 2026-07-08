def is_valid_pawn_move(board, r1, c1, r2, c2):
    current_piece = board.get(r1, c1)
    if current_piece is None:
        return False

    target_piece = board.get(r2, c2)
    color = current_piece.color
    if target_piece is not None and target_piece.color == color:
        return False

    direction = -1 if color == 'w' else 1
    start_row = board.height - 1 if color == 'w' else 0

    if c1 == c2 and r2 - r1 == direction:
        return target_piece is None

    if c1 == c2 and r2 - r1 == 2 * direction:
        if r1 != start_row:
            return False
        return target_piece is None and board.is_path_clear(r1, c1, r2, c2)

    if abs(c2 - c1) == 1 and r2 - r1 == direction:
        return target_piece is not None

    return False
