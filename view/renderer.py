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
from view.board_renderer import board_image, board_origin, draw_board, draw_selection, draw_legal_moves, draw_rest_animation
from view.sprite_loader import load_sprites, REST_TICKS, SHORT_REST_TICKS, JUMP_TICKS
from view.ui_renderer import compose_game_frame
from view.board_setup import create_initial_board
from view.input_handler import on_mouse, move_notation


def format_elapsed(seconds: float) -> str:
    minutes = int(seconds // 60)
    seconds_rem = seconds - minutes * 60
    return f"{minutes:02d}:{seconds_rem:05.2f}"

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
            "board_origin": board_origin,
            "short_rest_ticks": SHORT_REST_TICKS,
            "jump_ticks": JUMP_TICKS,
        },
    )

    animation_tick = 0
    while True:
        motion_events = engine.wait(20)
        for event in motion_events:
            motion = event["motion"]
            captured_piece = event["captured"]
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
            notation = move_notation(motion.piece, motion.source, motion.destination, captured_piece)
            move_log.append({
                "color": motion.piece.color,
                "time": format_elapsed(time.perf_counter() - start_time),
                "notation": notation,
            })
            rest_timers[motion.destination] = REST_TICKS

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

        frame = draw_board(
            engine.board,
            engine.arbiter.active_motions,
            sprites,
            animation_tick,
            rest_timers,
            short_rest_timers,
            jump_timers,
            engine.arbiter.elapsed_time_ms,
        )
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
