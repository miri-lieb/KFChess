import cv2
import numpy as np

from config import MESSAGE_LIST_ROOMS
from view.draw import (
    ACCENT,
    BG_COLOR,
    CARD_COLOR,
    ERROR_COLOR,
    INPUT_BG,
    INPUT_BORDER,
    INPUT_BORDER_FOCUS,
    PANEL_COLOR,
    SUCCESS_COLOR,
    TABLE_ROW_ALT,
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
HEADER_H = 50

LEFT_PANEL_X = 20
LEFT_PANEL_W = 310
LEFT_PANEL_Y = HEADER_H + 16
LEFT_PANEL_H = 340

RIGHT_PANEL_X = LEFT_PANEL_X + LEFT_PANEL_W + 16
RIGHT_PANEL_W = CANVAS_W - RIGHT_PANEL_X - 20
RIGHT_PANEL_Y = LEFT_PANEL_Y
RIGHT_PANEL_H = LEFT_PANEL_H + 70

FIELD_H = 40
FIELD_W_LEFT = LEFT_PANEL_W - 40
FIELD_X_LEFT = LEFT_PANEL_X + 20

TABLE_X = RIGHT_PANEL_X + 14
TABLE_Y = RIGHT_PANEL_Y + 78
TABLE_W = RIGHT_PANEL_W - 28
ROW_H = 36


def _draw_header(canvas, username):
    cv2.rectangle(canvas, (0, 0), (CANVAS_W, HEADER_H), PANEL_COLOR, -1)
    cv2.line(canvas, (0, HEADER_H), (CANVAS_W, HEADER_H), INPUT_BORDER, 1)
    icon = chr(9816)
    put_text(canvas, icon + "  KFChess Lobby", 20, 33, ACCENT, scale=0.6)
    put_text(canvas, "Logged in as: ", CANVAS_W - 340, 33, TEXT_MUTED, scale=0.45)
    put_text(canvas, username, CANVAS_W - 220, 33, TEXT_PRIMARY, scale=0.5)


def _draw_left_panel(canvas, room_name, cursor_visible, msg_text, msg_is_error, waiting):
    px = LEFT_PANEL_X
    py = LEFT_PANEL_Y
    pw = LEFT_PANEL_W
    ph = LEFT_PANEL_H

    draw_rounded_rect(canvas, px, py, pw, ph, PANEL_COLOR, 10)
    cv2.rectangle(canvas, (px, py), (px + pw, py + ph), INPUT_BORDER, 1)

    put_text(canvas, "Create a Room", px + 20, py + 32, TEXT_PRIMARY, scale=0.55)

    label_y = py + 72
    put_text(canvas, "Room Name", FIELD_X_LEFT, label_y, TEXT_SECONDARY, scale=0.42)

    fy = label_y + 14
    focused = not waiting
    border_color = INPUT_BORDER_FOCUS if focused else INPUT_BORDER
    cv2.rectangle(canvas, (FIELD_X_LEFT - 1, fy - 1), (FIELD_X_LEFT + FIELD_W_LEFT + 1, fy + FIELD_H + 1), border_color, 1)
    cv2.rectangle(canvas, (FIELD_X_LEFT, fy), (FIELD_X_LEFT + FIELD_W_LEFT, fy + FIELD_H), INPUT_BG, -1)

    if room_name:
        put_text(canvas, room_name, FIELD_X_LEFT + 10, fy + FIELD_H // 2 + 6, TEXT_PRIMARY, scale=0.5)
    elif not waiting:
        put_text(canvas, "e.g. Championship Match", FIELD_X_LEFT + 10, fy + FIELD_H // 2 + 6, TEXT_MUTED, scale=0.5)

    if focused and cursor_visible and not waiting:
        tw = text_size(room_name, scale=0.5)[0] if room_name else 0
        cx = FIELD_X_LEFT + 10 + tw + 2
        cv2.line(canvas, (cx, fy + 8), (cx, fy + FIELD_H - 8), TEXT_PRIMARY, 1)

    btn_y = fy + FIELD_H + 12
    btn_w = FIELD_W_LEFT
    draw_rounded_rect(canvas, FIELD_X_LEFT, btn_y, btn_w, 40, ACCENT, 6)

    if waiting:
        put_text(canvas, "Creating...", FIELD_X_LEFT + btn_w // 2 - text_size("Creating...", scale=0.55)[0] // 2,
                 btn_y + 27, WHITE, scale=0.55)
    else:
        put_text(canvas, "Create Room", FIELD_X_LEFT + btn_w // 2 - text_size("Create Room", scale=0.55)[0] // 2,
                 btn_y + 27, WHITE, scale=0.55)

    if msg_text:
        color = ERROR_COLOR if msg_is_error else SUCCESS_COLOR
        put_text(canvas, msg_text, px + 20, py + ph - 16, color, scale=0.42)

    return {
        "create_btn": (FIELD_X_LEFT, btn_y, btn_w, 40),
        "name_field": (FIELD_X_LEFT, fy, FIELD_W_LEFT, FIELD_H),
    }


def _draw_right_panel(canvas, rooms, selected_idx, join_id, cursor_visible, msg_text, msg_is_error, waiting):
    px = RIGHT_PANEL_X
    py = RIGHT_PANEL_Y
    pw = RIGHT_PANEL_W
    ph = RIGHT_PANEL_H

    draw_rounded_rect(canvas, px, py, pw, ph, PANEL_COLOR, 10)
    cv2.rectangle(canvas, (px, py), (px + pw, py + ph), INPUT_BORDER, 1)

    put_text(canvas, "Available Rooms", px + 16, py + 32, TEXT_PRIMARY, scale=0.55)

    ref_x = px + pw - 16 - 90
    ref_y = py + 16
    ref_w = 90
    ref_h = 28
    draw_rounded_rect(canvas, ref_x, ref_y, ref_w, ref_h, ACCENT, 5)
    put_text(canvas, "Refresh", ref_x + ref_w // 2 - text_size("Refresh", scale=0.42)[0] // 2,
             ref_y + 19, WHITE, scale=0.42)

    table_top = py + 56
    table_bottom = py + ph - 90
    table_h = table_bottom - table_top

    header_y = table_top
    cv2.rectangle(canvas, (px + 1, header_y), (px + pw - 1, header_y + 30), CARD_COLOR, -1)
    col_starts = [16, 100, 190, 250, 310]

    for i, label in enumerate(["Room", "Creator", "Players", "Status", ""]):
        cx = px + col_starts[i]
        cy = header_y + 20
        if i == 4:
            continue
        put_text(canvas, label, cx + 4, cy, TEXT_SECONDARY, scale=0.4)

    row_start_y = header_y + 32
    max_visible = max(1, (table_h - 4) // ROW_H)
    visible_rooms = rooms[:max_visible]

    for i, room in enumerate(visible_rooms):
        ry = row_start_y + i * ROW_H
        if i == selected_idx and not waiting:
            cv2.rectangle(canvas, (px + 2, ry), (px + pw - 2, ry + ROW_H), INPUT_BORDER_FOCUS, 1)
        elif i % 2 == 0:
            cv2.rectangle(canvas, (px + 2, ry), (px + pw - 2, ry + ROW_H), TABLE_ROW_ALT, -1)

        player_count = room.get("players", 0)
        status_text = "Waiting" if player_count < 2 else "Full"

        put_text(canvas, room.get("name", ""), px + col_starts[0] + 4, ry + 24, TEXT_PRIMARY, scale=0.42)
        put_text(canvas, room.get("creator", ""), px + col_starts[1] + 4, ry + 24, TEXT_SECONDARY, scale=0.42)
        put_text(canvas, f"{player_count}/2", px + col_starts[2] + 4, ry + 24, TEXT_PRIMARY, scale=0.42)

        if player_count < 2:
            status_color = SUCCESS_COLOR
        else:
            status_color = ERROR_COLOR
        put_text(canvas, status_text, px + col_starts[3] + 4, ry + 24, status_color, scale=0.4)

        if player_count < 2:
            btn_x = px + pw - 16 - 56
            btn_y_ = ry + 4
            draw_rounded_rect(canvas, btn_x, btn_y_, 56, 28, ACCENT, 5)
            put_text(canvas, "Join", btn_x + 28 - text_size("Join", scale=0.42)[0] // 2,
                     btn_y_ + 19, WHITE, scale=0.42)

    if not visible_rooms:
        put_text(canvas, "No rooms available. Create one!", px + 30, row_start_y + 30, TEXT_MUTED, scale=0.45)

    if waiting:
        put_text(canvas, "Joining...", px + pw // 2 - 40, table_bottom - 6, TEXT_MUTED, scale=0.45)

    id_y = table_bottom + 6
    cv2.line(canvas, (px + 16, id_y), (px + pw - 16, id_y), INPUT_BORDER, 1)
    id_label_y = id_y + 20
    put_text(canvas, "Or join by Room ID:", px + 16, id_label_y, TEXT_SECONDARY, scale=0.42)

    id_field_y = id_label_y + 20
    id_field_w = 160
    focused = not waiting and selected_idx < 0
    border_color = INPUT_BORDER_FOCUS if focused else INPUT_BORDER
    cv2.rectangle(canvas, (px + 16, id_field_y), (px + 16 + id_field_w, id_field_y + FIELD_H), INPUT_BG, -1)
    cv2.rectangle(canvas, (px + 16 - 1, id_field_y - 1), (px + 16 + id_field_w + 1, id_field_y + FIELD_H + 1), border_color, 1)

    if join_id:
        put_text(canvas, join_id, px + 26, id_field_y + FIELD_H // 2 + 6, TEXT_PRIMARY, scale=0.5)
    elif not waiting:
        put_text(canvas, "Enter Room ID", px + 26, id_field_y + FIELD_H // 2 + 6, TEXT_MUTED, scale=0.5)

    if focused and cursor_visible and not waiting and not join_id:
        cx = px + 26 + 2
        cv2.line(canvas, (cx, id_field_y + 8), (cx, id_field_y + FIELD_H - 8), TEXT_PRIMARY, 1)
    elif focused and cursor_visible and join_id:
        tw = text_size(join_id, scale=0.5)[0]
        cx = px + 26 + tw + 2
        cv2.line(canvas, (cx, id_field_y + 8), (cx, id_field_y + FIELD_H - 8), TEXT_PRIMARY, 1)

    id_btn_x = px + 16 + id_field_w + 10
    draw_rounded_rect(canvas, id_btn_x, id_field_y, 60, FIELD_H, ACCENT, 5)
    put_text(canvas, "Join", id_btn_x + 30 - text_size("Join", scale=0.5)[0] // 2,
             id_field_y + FIELD_H // 2 + 6, WHITE, scale=0.5)

    if msg_text:
        color = ERROR_COLOR if msg_is_error else SUCCESS_COLOR
        put_text(canvas, msg_text, px + 16, py + ph - 14, color, scale=0.42)

    clickables = {
        "refresh": (ref_x, ref_y, ref_w, ref_h),
        "id_btn": (id_btn_x, id_field_y, 60, FIELD_H),
        "id_field": (px + 16, id_field_y, id_field_w, FIELD_H),
    }
    return clickables, visible_rooms


class LobbyState:
    def __init__(self):
        self.room_name_input = ""
        self.join_id_input = ""
        self.rooms = []
        self.selected_room_idx = -1
        self.active_section = "create_name"
        self.error_msg = ""
        self.success_msg = ""
        self.waiting = False
        self.waiting_type = ""
        self.cursor_visible = True
        self._cursor_tick = 0
        self.username = ""
        self.last_clickables = {}
        self.visible_rooms = []
        self.needs_refresh = True

    def handle_key(self, key):
        if key == -1:
            return
        self._cursor_tick += 1
        if self._cursor_tick % 8 == 0:
            self.cursor_visible = not self.cursor_visible

        if self.waiting:
            return

        if key == 9:
            self._cycle_active()
            self.clear_messages()
            return
        if key == 27:
            self.clear_messages()
            return
        if key == 13:
            if self.active_section == "create_name" and self.room_name_input.strip():
                return ("create", self.room_name_input.strip())
            if self.active_section == "id_field" and self.join_id_input.strip():
                return ("join_id", self.join_id_input.strip().upper())
            if self.active_section == "rooms_list" and self.selected_room_idx >= 0:
                room = self.rooms[self.selected_room_idx]
                return ("join_room", room.get("id"))
            return None
        if key == 8:
            if self.active_section == "create_name":
                self.room_name_input = self.room_name_input[:-1]
            elif self.active_section == "id_field":
                self.join_id_input = self.join_id_input[:-1]
            self.clear_messages()
            self.cursor_visible = True
            return None
        if key == 38:
            if self.active_section == "rooms_list":
                self.selected_room_idx = max(-1, self.selected_room_idx - 1)
                self.cursor_visible = True
            return None
        if key == 40:
            if self.active_section == "rooms_list":
                self.selected_room_idx = min(len(self.rooms) - 1, self.selected_room_idx + 1)
                if self.selected_room_idx < 0 and self.rooms:
                    self.selected_room_idx = 0
                self.cursor_visible = True
            return None
        if key == 32 or 33 <= key <= 126:
            ch = chr(key)
            if self.active_section == "create_name" and len(self.room_name_input) < 50:
                self.room_name_input += ch
            elif self.active_section == "id_field" and len(self.join_id_input) < 6:
                self.join_id_input += ch.upper()
            self.clear_messages()
            self.cursor_visible = True

    def handle_click(self, x, y):
        if self.waiting:
            return None

        clickables = self.last_clickables
        if self._in_rect(x, y, clickables.get("create_btn")):
            if self.room_name_input.strip():
                return ("create", self.room_name_input.strip())
            self.set_error("Enter a room name first")
            return None
        if self._in_rect(x, y, clickables.get("refresh")):
            self.needs_refresh = True
            self.clear_messages()
            return None
        if self._in_rect(x, y, clickables.get("id_field")):
            self.active_section = "id_field"
            self.selected_room_idx = -1
            self.cursor_visible = True
            return None
        if self._in_rect(x, y, clickables.get("id_btn")):
            if self.join_id_input.strip():
                return ("join_id", self.join_id_input.strip().upper())
            self.set_error("Enter a room ID first")
            return None
        if x >= RIGHT_PANEL_X and x <= RIGHT_PANEL_X + RIGHT_PANEL_W:
            for i, room in enumerate(self.visible_rooms):
                ry = self._get_row_y(i)
                if ry is not None and ry <= y <= ry + ROW_H:
                    player_count = room.get("players", 0)
                    if player_count < 2:
                        self.selected_room_idx = i
                        self.active_section = "rooms_list"
                        self.cursor_visible = True
                        return ("join_room", room.get("id"))
                    else:
                        self.set_error("Room is full")
                        return None
        if self._in_rect(x, y, clickables.get("name_field")):
            self.active_section = "create_name"
            self.selected_room_idx = -1
            self.cursor_visible = True
            return None
        if self._in_rect(x, y, (FIELD_X_LEFT, LEFT_PANEL_Y + 86, FIELD_W_LEFT, FIELD_H)):
            self.active_section = "create_name"
            self.selected_room_idx = -1
            self.cursor_visible = True

    def set_waiting(self, wt):
        self.waiting = True
        self.waiting_type = wt
        self.clear_messages()

    def clear_waiting(self):
        self.waiting = False
        self.waiting_type = ""

    def set_error(self, msg):
        self.error_msg = msg
        self.success_msg = ""

    def set_success(self, msg):
        self.success_msg = msg
        self.error_msg = ""

    def clear_messages(self):
        self.error_msg = ""
        self.success_msg = ""

    def _cycle_active(self):
        order = ["create_name", "id_field", "rooms_list"]
        idx = order.index(self.active_section)
        self.active_section = order[(idx + 1) % len(order)]
        if self.active_section == "rooms_list":
            self.selected_room_idx = -1 if not self.rooms else 0

    def _in_rect(self, x, y, rect):
        if rect is None:
            return False
        rx, ry, rw, rh = rect
        return rx <= x <= rx + rw and ry <= y <= ry + rh

    def _get_row_y(self, i):
        row_start_y = RIGHT_PANEL_Y + 56 + 32 + 4
        return row_start_y + i * ROW_H


def render_lobby_screen(canvas, lobby_state):
    canvas[:] = BG_COLOR

    _draw_header(canvas, lobby_state.username)

    msg = lobby_state.error_msg or lobby_state.success_msg
    msg_err = bool(lobby_state.error_msg)

    left_clickables = _draw_left_panel(canvas, lobby_state.room_name_input, lobby_state.cursor_visible,
                                       msg if lobby_state.active_section == "create_name" else "", msg_err,
                                       lobby_state.waiting and lobby_state.waiting_type == "create")

    right_clickables, visible = _draw_right_panel(canvas, lobby_state.rooms, lobby_state.selected_room_idx,
                                                  lobby_state.join_id_input, lobby_state.cursor_visible,
                                                  msg if lobby_state.active_section != "create_name" else "", msg_err,
                                                  lobby_state.waiting and lobby_state.waiting_type == "join")

    lobby_state.last_clickables = {**left_clickables, **right_clickables}
    lobby_state.visible_rooms = visible

    hints = "Tab: cycle fields  |  Up/Down: navigate rooms  |  Enter: select  |  Esc: clear"
    put_text(canvas, hints, 20, CANVAS_H - 12, TEXT_MUTED, scale=0.38)

def create_lobby_canvas():
    return np.full((CANVAS_H, CANVAS_W, 3), BG_COLOR, dtype=np.uint8)