import cv2
import numpy as np

FONT = cv2.FONT_HERSHEY_SIMPLEX

BG_COLOR = (46, 26, 26)
PANEL_COLOR = (62, 33, 22)
CARD_COLOR = (41, 22, 15)
INPUT_BG = (41, 22, 15)
INPUT_BORDER = (92, 58, 42)
INPUT_BORDER_FOCUS = (165, 111, 74)
TEXT_PRIMARY = (240, 248, 232)
TEXT_SECONDARY = (176, 146, 136)
TEXT_MUTED = (128, 102, 90)
ACCENT = (246, 181, 100)
ACCENT_HOVER = (249, 202, 144)
ERROR_COLOR = (80, 83, 239)
SUCCESS_COLOR = (106, 187, 102)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
DARK = (20, 12, 12)
DANGER = (80, 80, 239)
DANGER_HOVER = (60, 60, 200)
TABLE_ROW_ALT = (52, 32, 20)
TABLE_HOVER = (62, 42, 30)


def put_text(canvas, text, x, y, color=TEXT_PRIMARY, scale=0.5, thickness=1):
    cv2.putText(canvas, text, (x, y), FONT, scale, color, thickness, cv2.LINE_AA)


def text_size(text, scale=0.5, thickness=1):
    return cv2.getTextSize(text, FONT, scale, thickness)[0]


def draw_rounded_rect(canvas, x, y, w, h, color, radius=8):
    cv2.rectangle(canvas, (x + radius, y), (x + w - radius, y + h), color, -1)
    cv2.rectangle(canvas, (x, y + radius), (x + w, y + h - radius), color, -1)
    cv2.circle(canvas, (x + radius, y + radius), radius, color, -1)
    cv2.circle(canvas, (x + w - radius, y + radius), radius, color, -1)
    cv2.circle(canvas, (x + radius, y + h - radius), radius, color, -1)
    cv2.circle(canvas, (x + w - radius, y + h - radius), radius, color, -1)
