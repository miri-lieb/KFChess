import os
import sys
import time

import cv2

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from engine.game_engine import GameEngine
from input.controller import Controller
from model.board import Board
from model.piece import Piece, WHITE, BLACK, ROOK, KNIGHT, BISHOP, QUEEN, KING, PAWN, IDLE
from model.position import Position
from rules.piece_rules import legal_destinations
from view.animation import (
    load_sprites,
    board_image,
    draw_board,
    draw_selection,
    draw_legal_moves,
    draw_rest_animation,
    compose_game_frame,
    board_origin,
    REST_TICKS,
    SHORT_REST_TICKS,
    JUMP_TICKS,
)

START_PIECES = [
    ["RB", "NB", "BB", "QB", "KB", "BB", "NB", "RB"],
    ["PB"] * 8,
    [None] * 8,
    [None] * 8,
    [None] * 8,
    [None] * 8,
    ["PW"] * 8,
    ["RW", "NW", "BW", "QW", "KW", "BW", "NW", "RW"],
]

REST_TICKS = 100

def make_piece(code: str, row: int, col: int) -> Piece:
    kind_map = {"R": ROOK, "N": KNIGHT, "B": BISHOP, "Q": QUEEN, "K": KING, "P": PAWN}
    color = WHITE if code[1] == "W" else BLACK
    kind = kind_map[code[0]]
    return Piece(id=f"{code}-{row}-{col}", color=color, kind=kind, cell=Position(row, col), state=IDLE)

def create_initial_board() -> Board:
    board = Board(8, 8)
    for row in range(8):
        for col in range(8):
            code = START_PIECES[row][col]
            if code is None:
                continue
            board.add_piece(Position(row, col), make_piece(code, row, col))
    return board

def position_to_algebraic(position: Position) -> str:
    file_names = "abcdefgh"
    rank = 8 - position.row
    return f"{file_names[position.col]}{rank}"

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
    move_log = param["move_log"]
    start_time = param["start_time"]

    board_x, board_y = board_origin()
    board_w = board_img.shape[1]
    board_h = board_img.shape[0]
    if x < board_x or y < board_y or x >= board_x + board_w or y >= board_y + board_h:
        return

    rel_x = x - board_x
    rel_y = y - board_y
    cell_w = board_w / 8
    cell_h = board_h / 8
    col = int(rel_x // cell_w)
    row = int(rel_y // cell_h)
    position = Position(row, col)

    if row < 0 or row >= 8 or col < 0 or col >= 8:
        return

    selected = controller.selected
    if selected is None and position in rest_timers:
        print("Piece is resting and cannot be selected.")
        return
    if selected is not None and position in rest_timers:
        print("Target square is resting and cannot be selected.")
        return
    if selected is not None and selected == position:
        # request a jump action on the selected piece
        if position not in jump_timers and position not in short_rest_timers and position not in rest_timers:
            jump_timers[position] = JUMP_TICKS
            short_rest_timers[position] = SHORT_REST_TICKS
        controller.selected = None
        return

    reason = controller.click(position)
    if reason is None and controller.selected is not None:
        print(f"Selected piece at {controller.selected.row},{controller.selected.col}")
    elif reason is not None:
        print(f"click {x},{y} -> row={position.row},col={position.col}, reason={reason}")
        if reason == "ok" and engine.arbiter.active_motion is not None:
            motion = engine.arbiter.active_motion
            target_piece = engine.board.get_piece(motion.destination)
            notation = move_notation(motion.piece, motion.source, motion.destination, target_piece)
            move_log.append({
                "color": motion.piece.color,
                "time": format_elapsed(time.perf_counter() - start_time),
                "notation": notation,
            })

    legal_moves = param["legal_moves"]
    legal_moves.clear()
    if controller.selected is not None:
        selected_piece = engine.board.get_piece(controller.selected)
        if selected_piece is not None:
            legal_moves.update(legal_destinations(engine.board, selected_piece))

def main():
    sprites = load_sprites()
    board = create_initial_board()
    engine = GameEngine(board)
    controller = Controller(engine)
    board_img = board_image()

    cv2.namedWindow("Chess Board")
    rest_timers = {}
    short_rest_timers = {}
    jump_timers = {}
    move_log = []
    legal_moves = set()
    scores = {"white": 0, "black": 0}
    start_time = time.perf_counter()
    cv2.setMouseCallback(
        "Chess Board",
        on_mouse,
        {
            "controller": controller,
            "engine": engine,
            "rest_timers": rest_timers,
            "short_rest_timers": short_rest_timers,
            "jump_timers": jump_timers,
            "board_img": board_img.img,
            "move_log": move_log,
            "start_time": start_time,
            "legal_moves": legal_moves,
        },
    )

    prev_motion = None
    animation_tick = 0
    while True:
        current_motion = engine.arbiter.active_motion
        captured_piece = engine.wait(20)
        if captured_piece is not None:
            value = {
                "pawn": 1,
                "knight": 3,
                "bishop": 3,
                "rook": 5,
                "queen": 9,
                "king": 0,
            }.get(captured_piece.kind, 0)
            scores["black" if captured_piece.color == "white" else "white"] += value

        if prev_motion is not None and current_motion is None:
            dest = prev_motion.destination
            rest_timers[dest] = REST_TICKS
        prev_motion = current_motion

        for pos in list(rest_timers):
            rest_timers[pos] -= 1
            if rest_timers[pos] <= 0:
                del rest_timers[pos]

        for pos in list(short_rest_timers):
            short_rest_timers[pos] -= 1
            if short_rest_timers[pos] <= 0:
                del short_rest_timers[pos]

        for pos in list(jump_timers):
            jump_timers[pos] -= 1
            if jump_timers[pos] <= 0:
                del jump_timers[pos]

        frame = draw_board(engine, sprites, animation_tick, rest_timers, short_rest_timers, jump_timers)
        draw_rest_animation(frame, rest_timers, short_rest_timers, jump_timers, board_img.img, animation_tick)
        draw_legal_moves(frame, legal_moves, board_img.img)
        draw_selection(frame, controller.selected, board_img.img)
        composed = compose_game_frame(frame, move_log, scores, engine.game_over)
        cv2.imshow("Chess Board", composed.img)
        if cv2.waitKey(20) == 27:
            break
        animation_tick += 1

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()