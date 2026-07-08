
def parse_and_validate_board(board_lines):
    parsed_board = []
    expected_width = None
    valid_pieces = {'K', 'Q', 'R', 'B', 'N', 'P'}
    for line in board_lines:
        tokens = line.split()
        if not tokens:
            continue
        if expected_width is None:
            expected_width = len(tokens)
        elif len(tokens) != expected_width:
            print("ERROR ROW_WIDTH_MISMATCH")
            return None

        for token in tokens:
            if token == '.':
                continue
            if len(token) == 2 and token[0] in ('w', 'b') and token[1] in valid_pieces:
                continue
            print("ERROR UNKNOWN_TOKEN")
            return None
        parsed_board.append(tokens)
    return parsed_board
    