def is_move_legal(board, r1, c1, r2, c2):
    if not board.is_valid_position(r1, c1) or not board.is_valid_position(r2, c2):
        return False

    if (r1, c1) == (r2, c2):
        return False

    piece = board.get(r1, c1)
    if piece is None:
        return False

    destination = board.get(r2, c2)
    color, piece_type = piece.color, piece.type

    if destination is not None and destination.color == color:
        return False

    dr = abs(r2 - r1)
    dc = abs(c2 - c1)

    rule = RULES.get(piece_type)
    if rule is None:
        return False

    return rule(board, r1, c1, r2, c2, color, dr, dc)


def king_rule(board, r1, c1, r2, c2, color, dr, dc):
    return dr <= 1 and dc <= 1


def rook_rule(board, r1, c1, r2, c2, color, dr, dc):
    return (r1 == r2 or c1 == c2) and board.is_path_clear(r1, c1, r2, c2)


def bishop_rule(board, r1, c1, r2, c2, color, dr, dc):
    return dr == dc and board.is_path_clear(r1, c1, r2, c2)


def queen_rule(board, r1, c1, r2, c2, color, dr, dc):
    return (r1 == r2 or c1 == c2 or dr == dc) and board.is_path_clear(r1, c1, r2, c2)


def knight_rule(board, r1, c1, r2, c2, color, dr, dc):
    return (dr == 2 and dc == 1) or (dr == 1 and dc == 2)


def pawn_rule(board, r1, c1, r2, c2, color, dr, dc):
    direction = -1 if color == 'w' else 1

    if c1 == c2 and (r2 - r1 == direction):
        return board.get(r2, c2) is None

    if abs(r2 - r1) == 2 and c1 == c2:
        start_row = board.height - 1 if color == 'w' else 0
        return r1 == start_row and board.get(r2, c2) is None and board.is_path_clear(r1, c1, r2, c2)

    if abs(c2 - c1) == 1 and (r2 - r1 == direction):
        return board.get(r2, c2) is not None

    return False


RULES = {
    'K': king_rule,
    'R': rook_rule,
    'B': bishop_rule,
    'Q': queen_rule,
    'N': knight_rule,
    'P': pawn_rule,
}
