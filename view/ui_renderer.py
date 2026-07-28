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
        top_y = int(board_y - 22)
        bottom_y = int(board_y + board_h + 32)
        cv2.putText(canvas_img, file_letter, (x, top_y), font, font_scale, color, thickness, cv2.LINE_AA)
        cv2.putText(canvas_img, file_letter, (x, bottom_y), font, font_scale, color, thickness, cv2.LINE_AA)

    for index in range(DEFAULT_BOARD_HEIGHT):
        rank = str(DEFAULT_BOARD_HEIGHT - index)
        (text_w, text_h), _ = cv2.getTextSize(rank, font, font_scale, thickness)
        y = int(board_y + index * cell_h + cell_h / 2 + text_h / 2)
        left_x = int(board_x - 30)
        right_x = int(board_x + board_w + 24)
        cv2.putText(canvas_img, rank, (left_x, y), font, font_scale, color, thickness, cv2.LINE_AA)
        cv2.putText(canvas_img, rank, (right_x, y), font, font_scale, color, thickness, cv2.LINE_AA)


def _draw_move_panel(canvas_img, origin_x, origin_y, width, title, entries):
    panel_height = canvas_img.shape[0] - origin_y - 40
    background_color = (230, 230, 230)
    border_color = (40, 40, 40)
    cv2.rectangle(canvas_img, (origin_x, origin_y), (origin_x + width, origin_y + panel_height), background_color, -1)
    cv2.rectangle(canvas_img, (origin_x, origin_y), (origin_x + width, origin_y + panel_height), border_color, 2)

    title_font = cv2.FONT_HERSHEY_SIMPLEX
    title_scale = 0.65
    title_thickness = 2
    cv2.putText(canvas_img, title, (origin_x + 12, origin_y + 26), title_font, title_scale, border_color, title_thickness, cv2.LINE_AA)

    header_font = cv2.FONT_HERSHEY_SIMPLEX
    header_scale = 0.55
    header_thickness = 1
    cv2.putText(canvas_img, PANEL_HEADER_TIME, (origin_x + 12, origin_y + 50), header_font, header_scale, border_color, header_thickness, cv2.LINE_AA)
    cv2.putText(canvas_img, PANEL_HEADER_MOVE, (origin_x + 100, origin_y + 50), header_font, header_scale, border_color, header_thickness, cv2.LINE_AA)

    row_height = 26
    max_rows = min(len(entries), (panel_height - 72) // row_height)
    for index in range(max_rows):
        entry = entries[index]
        y = origin_y + 72 + index * row_height
        cv2.putText(canvas_img, entry["time"], (origin_x + 12, y), header_font, header_scale, border_color, 1, cv2.LINE_AA)
        cv2.putText(canvas_img, entry["notation"], (origin_x + 100, y), header_font, header_scale, border_color, 1, cv2.LINE_AA)


def _draw_scores(canvas_img, board_x, board_y, board_w, scores):
    score_box_width = 240
    score_box_height = 76
    x = int(board_x + board_w / 2 - score_box_width / 2)
    y = int(board_y - score_box_height - 14)
    background_color = (220, 220, 220)
    border_color = (20, 20, 20)
    cv2.rectangle(canvas_img, (x, y), (x + score_box_width, y + score_box_height), background_color, -1)
    cv2.rectangle(canvas_img, (x, y), (x + score_box_width, y + score_box_height), border_color, 2)

    font = cv2.FONT_HERSHEY_SIMPLEX
    text_scale = 0.75
    text_thickness = 2
    cv2.putText(canvas_img, f"{PANEL_TITLE_BLACK}: {scores[ROLE_BLACK]}", (x + 12, y + 28), font, text_scale, (0, 0, 0), text_thickness, cv2.LINE_AA)
    cv2.putText(canvas_img, f"{PANEL_TITLE_WHITE}: {scores[ROLE_WHITE]}", (x + 12, y + 58), font, text_scale, (0, 0, 0), text_thickness, cv2.LINE_AA)


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


def _draw_waiting_overlay(canvas_img, board_x, board_y, board_w, board_h):
    font = cv2.FONT_HERSHEY_SIMPLEX
    text = "Waiting for opponent to join..."
    scale = 1.2
    thickness = 3
    (text_w, text_h), _ = cv2.getTextSize(text, font, scale, thickness)
    x = board_x + board_w // 2 - text_w // 2
    y = board_y + board_h // 2 + text_h // 2
    overlay = canvas_img.copy()
    cv2.rectangle(overlay, (board_x, board_y), (board_x + board_w, board_y + board_h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, canvas_img, 0.5, 0, canvas_img)
    cv2.putText(canvas_img, text, (x, y), font, scale, (200, 200, 0), thickness, cv2.LINE_AA)

def _build_panel_title(color_name, player_name, score):
    if player_name:
        return f"{color_name} — {player_name} ({score})"
    return f"{color_name} — Player ({score})"

def compose_game_frame(board_frame: Img, move_log, scores, game_over=False, player_names=None, waiting_for_opponent=False):
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

    names = player_names or {}
    black_title = _build_panel_title(PANEL_TITLE_BLACK, names.get(ROLE_BLACK), scores.get(ROLE_BLACK, 0))
    white_title = _build_panel_title(PANEL_TITLE_WHITE, names.get(ROLE_WHITE), scores.get(ROLE_WHITE, 0))

    _draw_scores(canvas.img, board_x, board_y, board_w, scores)
    _draw_move_panel(canvas.img, 10, board_y, panel_width - 20, black_title, [m for m in move_log if m["color"] == ROLE_BLACK])
    _draw_move_panel(canvas.img, board_x + board_w + 10, board_y, panel_width - 20, white_title, [m for m in move_log if m["color"] == ROLE_WHITE])

    _draw_border_labels(canvas.img, board_x, board_y, board_w, board_h)

    if game_over:
        _draw_game_over(canvas.img, board_x, board_y, board_w, board_h)
    elif waiting_for_opponent:
        names = player_names or {}
        if move_log or (names.get(ROLE_BLACK) and names.get(ROLE_WHITE)):
            waiting_for_opponent = False
        else:
            _draw_waiting_overlay(canvas.img, board_x, board_y, board_w, board_h)

    return canvas
