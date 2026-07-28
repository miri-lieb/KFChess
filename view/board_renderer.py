import cv2

from model.position import Position
from .img import Img
from .sprite_loader import (
    BOARD_PATH,
    BOARD_SIZE,
    JUMP_TICKS,
    SHORT_REST_TICKS,
    REST_TICKS,
    piece_sprite,
    piece_state,
)
from config import BOARD_FILE_NAMES, DEFAULT_BOARD_HEIGHT, DEFAULT_BOARD_WIDTH, STATE_MOVE

PANEL_WIDTH = 260
TOP_MARGIN = 90
BOTTOM_MARGIN = 40

def board_image():
    return Img().read(BOARD_PATH, size=BOARD_SIZE, keep_aspect=False)

def board_origin():
    return PANEL_WIDTH, TOP_MARGIN

def board_cell_size(board_img):
    return board_img.shape[1] / DEFAULT_BOARD_WIDTH, board_img.shape[0] / DEFAULT_BOARD_HEIGHT

def cell_center(row: int, col: int, board_img, sprite_img):
    cell_w, cell_h = board_cell_size(board_img)
    x = int(col * cell_w + (cell_w - sprite_img.img.shape[1]) / 2)
    y = int(row * cell_h + (cell_h - sprite_img.img.shape[0]) / 2)
    return x, y

def draw_board(board, motions, sprites, animation_tick: int, long_rest_timers, short_rest_timers, jump_timers, current_time_ms: int):
    frame = board_image()
    moving_sources = {motion.source for motion in motions}

    for row in range(DEFAULT_BOARD_HEIGHT):
        for col in range(DEFAULT_BOARD_WIDTH):
            position = Position(row, col)
            if position in moving_sources:
                continue
            piece = board.get_piece(position)
            if piece is None:
                continue
            state = piece_state(position, jump_timers, short_rest_timers, long_rest_timers)
            sprite = piece_sprite(sprites, piece, state, animation_tick)
            sprite.draw_on(frame, *cell_center(row, col, frame.img, sprite))

    for motion in motions:
        sprite = piece_sprite(sprites, motion.piece, STATE_MOVE, animation_tick)
        move_progress = motion.progress(current_time_ms)
        moving_start = cell_center(motion.source.row, motion.source.col, frame.img, sprite)
        moving_end = cell_center(motion.destination.row, motion.destination.col, frame.img, sprite)
        x = int(moving_start[0] + (moving_end[0] - moving_start[0]) * move_progress)
        y = int(moving_start[1] + (moving_end[1] - moving_start[1]) * move_progress)
        sprite.draw_on(frame, x, y)

    return frame

def draw_legal_moves(frame: Img, legal_moves, board_img):
    if not legal_moves:
        return

    overlay = frame.img.copy()
    board_h, board_w = board_img.shape[:2]
    cell_w = board_w / DEFAULT_BOARD_WIDTH
    cell_h = board_h / DEFAULT_BOARD_HEIGHT

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
    cell_w = board_w / DEFAULT_BOARD_WIDTH
    cell_h = board_h / DEFAULT_BOARD_HEIGHT
    overlay = frame.img.copy()
    phase = (animation_tick % (max(1, 100 * 2))) / (100 * 2)

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

def draw_selection(frame: Img, selected, board_img):
    if selected is None:
        return
    cell_w = board_img.shape[1] / DEFAULT_BOARD_WIDTH
    cell_h = board_img.shape[0] / DEFAULT_BOARD_HEIGHT
    row = selected.row
    col = selected.col
    x1 = int(col * cell_w)
    y1 = int(row * cell_h)
    x2 = int(x1 + cell_w)
    y2 = int(y1 + cell_h)
    cv2.rectangle(frame.img, (x1, y1), (x2, y2), (0, 255, 255), 3)