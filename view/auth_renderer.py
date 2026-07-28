import cv2
import numpy as np

from view.draw import (
    ACCENT,
    BG_COLOR,
    DARK,
    ERROR_COLOR,
    FONT,
    INPUT_BG,
    INPUT_BORDER,
    INPUT_BORDER_FOCUS,
    PANEL_COLOR,
    SUCCESS_COLOR,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    WHITE,
    draw_rounded_rect,
    put_text,
    text_size,
)

CANVAS_W = 900
CANVAS_H = 700
CARD_W = 440
CARD_H = 480
CARD_X = (CANVAS_W - CARD_W) // 2
CARD_Y = (CANVAS_H - CARD_H) // 2
FIELD_W = CARD_W - 80
FIELD_X = CARD_X + 40
FIELD_H = 44

AUTH_USERNAME = 0
AUTH_PASSWORD = 1

class AuthInput:
    def __init__(self):
        self.username = ""
        self.password = ""
        self.active_field = 0
        self.active_tab = "login"
        self.error_msg = ""
        self.success_msg = ""
        self.submitted = False
        self.submit_data = None
        self.cursor_visible = True
        self._cursor_tick = 0

    def handle_key(self, key):
        if key == -1:
            return
        self._cursor_tick += 1
        if self._cursor_tick % 8 == 0:
            self.cursor_visible = not self.cursor_visible
        if key == 9:
            if self.active_field == AUTH_USERNAME:
                self.active_field = AUTH_PASSWORD
            else:
                self.active_field = AUTH_USERNAME
            self.cursor_visible = True
            return
        if key == 27:
            self.clear_messages()
            return
        if key == 13:
            if self.username.strip() and self.password.strip():
                self.submitted = True
                self.submit_data = (self.active_tab, self.username.strip(), self.password.strip())
            return
        if key == 8:
            if self.active_field == AUTH_USERNAME:
                self.username = self.username[:-1]
            else:
                self.password = self.password[:-1]
            self.cursor_visible = True
            return
        if 32 <= key <= 126:
            ch = chr(key)
            if self.active_field == AUTH_USERNAME and len(self.username) < 50:
                self.username += ch
            elif self.active_field == AUTH_PASSWORD and len(self.password) < 50:
                self.password += ch
            self.cursor_visible = True

    def consume_submit(self):
        if self.submitted:
            self.submitted = False
            data = self.submit_data
            self.submit_data = None
            return data
        return None

    def set_error(self, msg):
        self.error_msg = msg
        self.success_msg = ""

    def set_success(self, msg):
        self.success_msg = msg
        self.error_msg = ""

    def clear_messages(self):
        self.error_msg = ""
        self.success_msg = ""

    def switch_tab(self, tab):
        if tab in ("login", "register") and tab != self.active_tab:
            self.active_tab = tab
            self.clear_messages()
            self.cursor_visible = True


def _draw_card(canvas):
    draw_rounded_rect(canvas, CARD_X, CARD_Y, CARD_W, CARD_H, PANEL_COLOR, 12)


def _draw_logo(canvas):
    text = "KFChess"
    ts = text_size(text, scale=1.4, thickness=2)
    tx = CARD_X + (CARD_W - ts[0]) // 2
    ty = CARD_Y + 60
    put_text(canvas, text, tx, ty, ACCENT, scale=1.4, thickness=2)
    icon = chr(9816)
    ets = text_size(icon, scale=1.8, thickness=2)
    ex = CARD_X + (CARD_W - ets[0]) // 2
    ey = ty + 36
    put_text(canvas, icon, ex, ey, TEXT_PRIMARY, scale=1.8, thickness=2)


def _draw_tabs(canvas, active_tab):
    tab_w = CARD_W // 2
    tab_h = 44
    tab_y = CARD_Y + 110
    for i, label in enumerate(["Login", "Register"]):
        tx = CARD_X + i * tab_w
        is_active = (i == 0 and active_tab == "login") or (i == 1 and active_tab == "register")
        bg = ACCENT if is_active else PANEL_COLOR
        draw_rounded_rect(canvas, tx, tab_y, tab_w, tab_h, bg, 6)
        ts = text_size(label, scale=0.55, thickness=1)
        ttx = tx + (tab_w - ts[0]) // 2
        tty = tab_y + tab_h // 2 + 7
        text_color = WHITE if is_active else TEXT_SECONDARY
        put_text(canvas, label, ttx, tty, text_color, scale=0.55, thickness=1)


def _draw_field(canvas, label, value, y, focused, cursor_visible, is_password):
    lx = CARD_X + 40
    put_text(canvas, label, lx, y - 8, TEXT_SECONDARY, scale=0.5)
    fy = y + 8
    border_color = INPUT_BORDER_FOCUS if focused else INPUT_BORDER
    cv2.rectangle(canvas, (FIELD_X - 1, fy - 1), (FIELD_X + FIELD_W + 1, fy + FIELD_H + 1), border_color, 1)
    cv2.rectangle(canvas, (FIELD_X, fy), (FIELD_X + FIELD_W, fy + FIELD_H), INPUT_BG, -1)

    display = value
    placeholder = "Enter your password" if is_password else "Enter your username"
    if is_password:
        display = chr(9679) * len(value)

    if display:
        put_text(canvas, display, FIELD_X + 12, fy + FIELD_H // 2 + 6, TEXT_PRIMARY, scale=0.55)
    else:
        put_text(canvas, placeholder, FIELD_X + 12, fy + FIELD_H // 2 + 6, TEXT_MUTED, scale=0.55)

    if focused and cursor_visible:
        tw = text_size(display, scale=0.55)[0] if display else 0
        cx = FIELD_X + 12 + tw + 2
        cv2.line(canvas, (cx, fy + 8), (cx, fy + FIELD_H - 8), TEXT_PRIMARY, 1)


def _draw_button(canvas, text):
    btn_y = CARD_Y + 310
    draw_rounded_rect(canvas, FIELD_X, btn_y, FIELD_W, 46, ACCENT, 6)
    ts = text_size(text, scale=0.65)
    tx = FIELD_X + (FIELD_W - ts[0]) // 2
    ty = btn_y + 32
    put_text(canvas, text, tx, ty, WHITE, scale=0.65)


def _draw_message(canvas, text, is_error):
    ts = text_size(text, scale=0.45)
    tx = CARD_X + (CARD_W - ts[0]) // 2
    ty = CARD_Y + CARD_H - 30
    color = ERROR_COLOR if is_error else SUCCESS_COLOR
    put_text(canvas, text, tx, ty, color, scale=0.45)


def _draw_hints(canvas):
    hints = "Tab: switch field  |  Enter: submit  |  Esc: clear"
    ts = text_size(hints, scale=0.38)
    tx = (CANVAS_W - ts[0]) // 2
    put_text(canvas, hints, tx, CANVAS_H - 20, TEXT_MUTED, scale=0.38)


def render_auth_screen(canvas, auth_input):
    canvas[:] = BG_COLOR
    cv2.rectangle(canvas, (0, 0), (CANVAS_W, CANVAS_H), DARK, 4)
    _draw_card(canvas)
    _draw_logo(canvas)
    _draw_tabs(canvas, auth_input.active_tab)

    focused_on = "username" if auth_input.active_field == 0 else "password"
    _draw_field(canvas, "Username", auth_input.username, CARD_Y + 170, focused_on == "username", auth_input.cursor_visible, is_password=False)
    _draw_field(canvas, "Password", auth_input.password, CARD_Y + 244, focused_on == "password", auth_input.cursor_visible, is_password=True)

    btn_label = "Register" if auth_input.active_tab == "register" else "Login"
    _draw_button(canvas, btn_label)

    if auth_input.error_msg:
        _draw_message(canvas, auth_input.error_msg, True)
    elif auth_input.success_msg:
        _draw_message(canvas, auth_input.success_msg, False)

    _draw_hints(canvas)


def create_auth_canvas():
    return np.full((CANVAS_H, CANVAS_W, 3), BG_COLOR, dtype=np.uint8)
