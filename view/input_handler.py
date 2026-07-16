import cv2

from engine.game_engine import GameEngine
from input.controller import Controller
from model.position import Position
from rules.piece_rules import legal_destinations

def position_to_algebraic(position: Position) -> str:
    file_names = "abcdefgh"
    rank = 8 - position.row
    return f"{file_names[position.col]}{rank}"

def board_pixel_to_position(x: int, y: int, board_x: int, board_y: int, board_w: int, board_h: int) -> Position | None:
    if x < board_x or y < board_y or x >= board_x + board_w or y >= board_y + board_h:
        return None

    rel_x = x - board_x
    rel_y = y - board_y
    cell_w = board_w / 8
    cell_h = board_h / 8
    col = int(rel_x // cell_w)
    row = int(rel_y // cell_h)
    if row < 0 or row >= 8 or col < 0 or col >= 8:
        return None
    return Position(row, col)

def format_elapsed(seconds: float) -> str:
    minutes = int(seconds // 60)
    seconds_rem = seconds - minutes * 60
    return f"{minutes:02d}:{seconds_rem:05.2f}"

def move_notation(piece, source: Position, destination: Position, target) -> str:
    dest_notation = position_to_algebraic(destination)
    piece_map = {"king": "K", "queen": "Q", "rook": "R", "bishop": "B", "knight": "N"}
    if piece.kind == "pawn":
        prefix = "" if target is None else position_to_algebraic(source)[0] + "x"
    else:
        prefix = piece_map.get(piece.kind, "")
        if target is not None:
            prefix += "x"
    return f"{prefix}{dest_notation}"

def on_mouse(event, x, y, flags, param):
    if event != cv2.EVENT_LBUTTONDOWN:
        return

    controller: Controller = param["controller"]
    engine: GameEngine = param["engine"]
    if engine.game_over:
        return
    rest_timers = param["rest_timers"]
    short_rest_timers = param["short_rest_timers"]
    jump_timers = param["jump_timers"]
    board_img = param["board_img"]

    board_x, board_y = param["board_origin"]()
    board_w = board_img.shape[1]
    board_h = board_img.shape[0]
    position = board_pixel_to_position(x, y, board_x, board_y, board_w, board_h)
    if position is None:
        return

    selected = controller.selected
    if selected is None and position in rest_timers:
        print("Piece is resting and cannot be selected.")
        return
    if selected is not None and position in rest_timers:
        selected_piece = engine.board.get_piece(selected)
        target_piece = engine.board.get_piece(position)
        if target_piece is None or selected_piece is None or target_piece.color == selected_piece.color:
            print("Target square is resting and cannot be selected.")
            return
    if selected is not None and selected == position:
        if position not in jump_timers and position not in short_rest_timers and position not in rest_timers:
            jump_timers[position] = param["jump_ticks"]
            short_rest_timers[position] = param["short_rest_ticks"]
        controller.selected = None
        return

    reason = controller.click(position)
    if reason is None and controller.selected is not None:
        print(f"Selected piece at {controller.selected.row},{controller.selected.col}")
    elif reason is not None:
        print(f"click {x},{y} -> row={position.row},col={position.col}, reason={reason}")

    legal_moves = param["legal_moves"]
    legal_moves.clear()
    if controller.selected is not None:
        selected_piece = engine.board.get_piece(controller.selected)
        if selected_piece is not None:
            legal_moves.update(legal_destinations(engine.board, selected_piece))