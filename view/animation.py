import os

import cv2
import numpy as np

from model.piece import WHITE, BLACK, ROOK, KNIGHT, BISHOP, QUEEN, KING, PAWN
from model.position import Position
from engine.game_engine import GameEngine
from .img import Img

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(SCRIPT_DIR, "assets")
BOARD_PATH = os.path.join(ASSETS_DIR, "board.png")
PIECE_SIZE = (80, 80)
BOARD_SIZE = (800, 800)
ANIMATION_DELAY = 5
ANIMATION_FRAMES = 5
SHORT_REST_STATE = "short_rest"
LONG_REST_STATE = "long_rest"
REST_TICKS = 100
SHORT_REST_TICKS = 30
JUMP_TICKS = 20

SPRITE_PATHS = {
    code: os.path.join(ASSETS_DIR, "pieces_mine", f"{code[1]}{code[0]}", "states")
    for code in ["PW", "PB", "RW", "RB", "NW", "NB", "BW", "BB", "QW", "QB", "KW", "KB"]
}

KIND_TO_SYMBOL = {
    "king": "K",
    "queen": "Q",
    "rook": "R",
    "bishop": "B",
    "knight": "N",
    "pawn": "P",
}

def load_sprites():
    sprites = {}
    for code, state_dir in SPRITE_PATHS.items():
        state_frames = {}
        for state in ["idle", "move", "jump", SHORT_REST_STATE, LONG_REST_STATE]:
            frame_dir = os.path.join(state_dir, state, "sprites")
            frames = []
            for frame_index in range(1, ANIMATION_FRAMES + 1):
                frame_path = os.path.join(frame_dir, f"{frame_index}.png")
                frames.append(Img().read(frame_path, size=PIECE_SIZE, keep_aspect=True))
            state_frames[state] = frames
        sprites[code] = state_frames
    return sprites

def board_image():
    return Img().read(BOARD_PATH, size=BOARD_SIZE, keep_aspect=False)

def cell_center(row, col, board_img, sprite_img):
    cell_w = board_img.shape[1] / 8
    cell_h = board_img.shape[0] / 8
    x = int(col * cell_w + (cell_w - sprite_img.img.shape[1]) / 2)
    y = int(row * cell_h + (cell_h - sprite_img.img.shape[0]) / 2)
    return x, y

def draw_board(engine: GameEngine, sprites, animation_tick: int, long_rest_timers, short_rest_timers, jump_timers):
    frame = board_image()
    motions = list(engine.arbiter.active_motions)
    moving_sources = {motion.source for motion in motions}

    for row in range(8):
        for col in range(8):
            position = Position(row, col)
            if position in moving_sources:
                continue
            piece = engine.board.get_piece(position)
            if piece is None:
                continue
            kind_code = KIND_TO_SYMBOL[piece.kind]
            code = f"{kind_code}{piece.color[0].upper()}"
            if position in jump_timers:
                state = "jump"
            elif position in short_rest_timers:
                state = SHORT_REST_STATE
            elif position in long_rest_timers:
                state = LONG_REST_STATE
            else:
                state = "idle"
            sprite_frames = sprites[code][state]
            frame_index = (animation_tick // ANIMATION_DELAY) % len(sprite_frames)
            sprite = sprite_frames[frame_index]
            pos = cell_center(row, col, frame.img, sprite)
            sprite.draw_on(frame, *pos)

    for motion in motions:
        kind_code = KIND_TO_SYMBOL[motion.piece.kind]
        moving_code = f"{kind_code}{motion.piece.color[0].upper()}"
        moving_sprite_frames = sprites[moving_code]["move"]
        move_progress = motion.progress(engine.arbiter.elapsed_time_ms)
        moving_start = cell_center(motion.source.row, motion.source.col, frame.img, moving_sprite_frames[0])
        moving_end = cell_center(motion.destination.row, motion.destination.col, frame.img, moving_sprite_frames[0])
        frame_index = (animation_tick // ANIMATION_DELAY) % len(moving_sprite_frames)
        sprite = moving_sprite_frames[frame_index]
        x = int(moving_start[0] + (moving_end[0] - moving_start[0]) * move_progress)
        y = int(moving_start[1] + (moving_end[1] - moving_start[1]) * move_progress)
        sprite.draw_on(frame, x, y)

    return frame

PANEL_WIDTH = 260
TOP_MARGIN = 60
BOTTOM_MARGIN = 40


def board_origin():
    return PANEL_WIDTH, TOP_MARGIN

def _draw_border_labels(canvas_img, board_x, board_y, board_w, board_h):
    files = "abcdefgh"
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.8
    color = (20, 20, 20)
    thickness = 2
    cell_w = board_w / 8
    cell_h = board_h / 8

    for index, file_letter in enumerate(files):
        (text_w, text_h), _ = cv2.getTextSize(file_letter, font, font_scale, thickness)
        x = int(board_x + index * cell_w + cell_w / 2 - text_w / 2)
        top_y = int(board_y - 18)
        bottom_y = int(board_y + board_h + 28)
        cv2.putText(canvas_img, file_letter, (x, top_y), font, font_scale, color, thickness, cv2.LINE_AA)
        cv2.putText(canvas_img, file_letter, (x, bottom_y), font, font_scale, color, thickness, cv2.LINE_AA)

    for index in range(8):
        rank = str(8 - index)
        (text_w, text_h), _ = cv2.getTextSize(rank, font, font_scale, thickness)
        y = int(board_y + index * cell_h + cell_h / 2 + text_h / 2)
        left_x = int(board_x - 26)
        right_x = int(board_x + board_w + 20)
        cv2.putText(canvas_img, rank, (left_x, y), font, font_scale, color, thickness, cv2.LINE_AA)
        cv2.putText(canvas_img, rank, (right_x, y), font, font_scale, color, thickness, cv2.LINE_AA)

def _draw_move_panel(canvas_img, origin_x, origin_y, width, title, entries):
    panel_height = canvas_img.shape[0] - origin_y - 40
    background_color = (230, 230, 230)
    border_color = (40, 40, 40)
    cv2.rectangle(canvas_img, (origin_x, origin_y), (origin_x + width, origin_y + panel_height), background_color, -1)
    cv2.rectangle(canvas_img, (origin_x, origin_y), (origin_x + width, origin_y + panel_height), border_color, 2)

    title_font = cv2.FONT_HERSHEY_SIMPLEX
    title_scale = 0.9
    title_thickness = 2
    cv2.putText(canvas_img, title, (origin_x + 12, origin_y + 30), title_font, title_scale, border_color, title_thickness, cv2.LINE_AA)

    header_font = cv2.FONT_HERSHEY_SIMPLEX
    header_scale = 0.6
    header_thickness = 1
    cv2.putText(canvas_img, "Time", (origin_x + 12, origin_y + 60), header_font, header_scale, border_color, header_thickness, cv2.LINE_AA)
    cv2.putText(canvas_img, "Move", (origin_x + 100, origin_y + 60), header_font, header_scale, border_color, header_thickness, cv2.LINE_AA)

    row_height = 30
    max_rows = min(len(entries), (panel_height - 90) // row_height)
    for index in range(max_rows):
        entry = entries[index]
        y = origin_y + 90 + index * row_height
        cv2.putText(canvas_img, entry["time"], (origin_x + 12, y), header_font, header_scale, border_color, 1, cv2.LINE_AA)
        cv2.putText(canvas_img, entry["notation"], (origin_x + 100, y), header_font, header_scale, border_color, 1, cv2.LINE_AA)

def draw_legal_moves(frame: Img, legal_moves, board_img):
    if not legal_moves:
        return

    overlay = frame.img.copy()
    board_h, board_w = board_img.shape[:2]
    cell_w = board_w / 8
    cell_h = board_h / 8

    for position in legal_moves:
        x1 = int(position.col * cell_w)
        y1 = int(position.row * cell_h)
        x2 = int(x1 + cell_w)
        y2 = int(y1 + cell_h)
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 255, 0), -1)

    cv2.addWeighted(overlay, 0.25, frame.img, 0.75, 0, frame.img)

def draw_rest_animation(frame: Img, long_rest_timers, short_rest_timers, jump_timers, board_img, animation_tick: int):
    if not (long_rest_timers or short_rest_timers or jump_timers):
        return

    board_h, board_w = board_img.shape[:2]
    cell_w = board_w / 8
    cell_h = board_h / 8
    overlay = frame.img.copy()
    phase = (animation_tick % (max(1, REST_TICKS * 2))) / (REST_TICKS * 2)

    for position, timer in jump_timers.items():
        x1 = int(position.col * cell_w + cell_w * 0.08)
        y1 = int(position.row * cell_h + cell_h * 0.08)
        x2 = int(position.col * cell_w + cell_w * 0.92)
        y2 = int(position.row * cell_h + cell_h * 0.92)
        alpha = 0.35 + 0.25 * abs(2 * phase - 1)
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (10, 250, 200), -1)
        cv2.addWeighted(overlay, alpha, frame.img, 1 - alpha, 0, overlay)

    for position, timer in short_rest_timers.items():
        percent = max(0.0, min(1.0, timer / SHORT_REST_TICKS))
        if percent <= 0:
            continue
        x1 = int(position.col * cell_w + cell_w * 0.18)
        x2 = int(position.col * cell_w + cell_w * 0.82)
        y2 = int(position.row * cell_h + cell_h - 6)
        y1 = int(y2 - percent * (cell_h * 0.6))
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 220, 220), -1)
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (255, 255, 255), 1)

    for position, timer in long_rest_timers.items():
        percent = max(0.0, min(1.0, timer / REST_TICKS))
        if percent <= 0:
            continue
        x1 = int(position.col * cell_w + cell_w * 0.18)
        x2 = int(position.col * cell_w + cell_w * 0.82)
        y2 = int(position.row * cell_h + cell_h - 6)
        y1 = int(y2 - percent * (cell_h * 0.8))
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 120, 220), -1)
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (255, 255, 255), 1)

    cv2.addWeighted(overlay, 0.45, frame.img, 0.55, 0, frame.img)

def _draw_scores(canvas_img, board_x, board_y, board_w, scores):
    score_box_width = 200
    score_box_height = 60
    x = int(board_x + board_w / 2 - score_box_width / 2)
    y = int(board_y - score_box_height - 10)
    background_color = (220, 220, 220)
    border_color = (20, 20, 20)
    cv2.rectangle(canvas_img, (x, y), (x + score_box_width, y + score_box_height), background_color, -1)
    cv2.rectangle(canvas_img, (x, y), (x + score_box_width, y + score_box_height), border_color, 2)

    font = cv2.FONT_HERSHEY_SIMPLEX
    label_scale = 0.7
    label_thickness = 2
    value_scale = 1.0
    value_thickness = 2
    cv2.putText(canvas_img, f"Black: {scores['black']}", (x + 10, y + 25), font, label_scale, (0, 0, 0), label_thickness, cv2.LINE_AA)
    cv2.putText(canvas_img, f"White: {scores['white']}", (x + 10, y + 50), font, value_scale, (0, 0, 0), value_thickness, cv2.LINE_AA)

def _draw_game_over(canvas_img, board_x, board_y, board_w, board_h):
    font = cv2.FONT_HERSHEY_SIMPLEX
    text = "GAME OVER"
    scale = 2.0
    thickness = 4
    (text_w, text_h), _ = cv2.getTextSize(text, font, scale, thickness)
    x = board_x + board_w // 2 - text_w // 2
    y = board_y + board_h // 2 + text_h // 2
    overlay = canvas_img.copy()
    cv2.rectangle(overlay, (board_x, board_y), (board_x + board_w, board_y + board_h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, canvas_img, 0.5, 0, canvas_img)
    cv2.putText(canvas_img, text, (x, y), font, scale, (0, 0, 255), thickness, cv2.LINE_AA)

def compose_game_frame(board_frame: Img, move_log, scores, game_over=False):
    if board_frame.img.shape[2] == 4:
        board_frame.img = cv2.cvtColor(board_frame.img, cv2.COLOR_BGRA2BGR)

    board_h, board_w = board_frame.img.shape[:2]
    panel_width = 260
    top_margin = 60
    bottom_margin = 40
    total_w = board_w + panel_width * 2
    total_h = board_h + top_margin + bottom_margin
    canvas = Img()
    canvas.img = np.full((total_h, total_w, 3), 245, dtype=np.uint8)

    board_x = panel_width
    board_y = top_margin
    canvas.img[board_y:board_y + board_h, board_x:board_x + board_w] = board_frame.img
    cv2.rectangle(canvas.img, (board_x - 2, board_y - 2), (board_x + board_w + 2, board_y + board_h + 2), (30, 30, 30), 3)

    _draw_scores(canvas.img, board_x, board_y, board_w, scores)
    _draw_move_panel(canvas.img, 10, board_y, panel_width - 20, "Black", [m for m in move_log if m["color"] == "black"])
    _draw_move_panel(canvas.img, board_x + board_w + 10, board_y, panel_width - 20, "White", [m for m in move_log if m["color"] == "white"])

    _draw_border_labels(canvas.img, board_x, board_y, board_w, board_h)

    if game_over:
        _draw_game_over(canvas.img, board_x, board_y, board_w, board_h)

    return canvas

def draw_selection(frame: Img, selected, board_img):
    if selected is None:
        return
    cell_w = board_img.shape[1] / 8
    cell_h = board_img.shape[0] / 8
    row = selected.row
    col = selected.col
    x1 = int(col * cell_w)
    y1 = int(row * cell_h)
    x2 = int(x1 + cell_w)
    y2 = int(y1 + cell_h)
    cv2.rectangle(frame.img, (x1, y1), (x2, y2), (0, 255, 255), 3)