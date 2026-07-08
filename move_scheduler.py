def schedule_move(parsed_board, from_row, from_col, to_row, to_col):
    distance = max(abs(to_row - from_row), abs(to_col - from_col))
    duration = distance * 1000
    return {
        "piece": parsed_board[from_row][from_col],
        "from_row": from_row,
        "from_col": from_col,
        "to_row": to_row,
        "to_col": to_col,
        "remaining_time": duration,
    }


def tick_pending_move(parsed_board, pending_move, elapsed=1):
    if pending_move is None:
        return None
    pending_move["remaining_time"] -= elapsed
    if pending_move["remaining_time"] <= 0:
        parsed_board[pending_move["to_row"]][pending_move["to_col"]] = pending_move["piece"]
        parsed_board[pending_move["from_row"]][pending_move["from_col"]] = '.'
        return None
    return pending_move
