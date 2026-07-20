import cv2
import numpy as np

from .img import Img
from .board_renderer import PANEL_WIDTH, TOP_MARGIN, BOTTOM_MARGIN
from config import (
    BOARD_FILE_NAMES,
    DEFAULT_BOARD_HEIGHT,
    GAME_OVER_TEXT,
    PANEL_HEADER_MOVE,
    PANEL_HEADER_TIME,
    PANEL_TITLE_BLACK,
    PANEL_TITLE_WHITE,
    ROLE_BLACK,
    ROLE_WHITE,
)

def _draw_border_labels(canvas_img, board_x, board_y, board_w, board_h):
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.8
    color = (20, 20, 20)
    thickness = 2
    cell_w = board_w / 8
    cell_h = board_h / 8

    for index, file_letter in enumerate(BOARD_FILE_NAMES):
        (text_w, text_h), _ = cv2.getTextSize(file_letter, font, font_scale, thickness)
        x = int(board_x + index * cell_w + cell_w / 2 - text_w / 2)
        top_y = int(board_y - 18)
        bottom_y = int(board_y + board_h + 28)
        cv2.putText(canvas_img, file_letter, (x, top_y), font, font_scale, color, thickness, cv2.LINE_AA)
        cv2.putText(canvas_img, file_letter, (x, bottom_y), font, font_scale, color, thickness, cv2.LINE_AA)

    for index in range(DEFAULT_BOARD_HEIGHT):
        rank = str(DEFAULT_BOARD_HEIGHT - index)
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
    cv2.putText(canvas_img, PANEL_HEADER_TIME, (origin_x + 12, origin_y + 60), header_font, header_scale, border_color, header_thickness, cv2.LINE_AA)
    cv2.putText(canvas_img, PANEL_HEADER_MOVE, (origin_x + 100, origin_y + 60), header_font, header_scale, border_color, header_thickness, cv2.LINE_AA)

    row_height = 30
    max_rows = min(len(entries), (panel_height - 90) // row_height)
    for index in range(max_rows):
        entry = entries[index]
        y = origin_y + 90 + index * row_height
        cv2.putText(canvas_img, entry["time"], (origin_x + 12, y), header_font, header_scale, border_color, 1, cv2.LINE_AA)
        cv2.putText(canvas_img, entry["notation"], (origin_x + 100, y), header_font, header_scale, border_color, 1, cv2.LINE_AA)


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
    cv2.putText(canvas_img, f"{PANEL_TITLE_BLACK}: {scores[ROLE_BLACK]}", (x + 10, y + 25), font, label_scale, (0, 0, 0), label_thickness, cv2.LINE_AA)
    cv2.putText(canvas_img, f"{PANEL_TITLE_WHITE}: {scores[ROLE_WHITE]}", (x + 10, y + 50), font, value_scale, (0, 0, 0), value_thickness, cv2.LINE_AA)


def _draw_game_over(canvas_img, board_x, board_y, board_w, board_h):
    font = cv2.FONT_HERSHEY_SIMPLEX
    text = GAME_OVER_TEXT
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
    panel_width = PANEL_WIDTH
    top_margin = TOP_MARGIN
    bottom_margin = BOTTOM_MARGIN
    total_w = board_w + panel_width * 2
    total_h = board_h + top_margin + bottom_margin
    canvas = Img()
    canvas.img = np.full((total_h, total_w, 3), 245, dtype=np.uint8)

    board_x = panel_width
    board_y = top_margin
    canvas.img[board_y:board_y + board_h, board_x:board_x + board_w] = board_frame.img
    cv2.rectangle(canvas.img, (board_x - 2, board_y - 2), (board_x + board_w + 2, board_y + board_h + 2), (30, 30, 30), 3)

    _draw_scores(canvas.img, board_x, board_y, board_w, scores)
    _draw_move_panel(canvas.img, 10, board_y, panel_width - 20, PANEL_TITLE_BLACK, [m for m in move_log if m["color"] == ROLE_BLACK])
    _draw_move_panel(canvas.img, board_x + board_w + 10, board_y, panel_width - 20, PANEL_TITLE_WHITE, [m for m in move_log if m["color"] == ROLE_WHITE])

    _draw_border_labels(canvas.img, board_x, board_y, board_w, board_h)

    if game_over:
        _draw_game_over(canvas.img, board_x, board_y, board_w, board_h)

    return canvas
