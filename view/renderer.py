import cv2
from CTD26.py.img import Img

BOARD_PATH = "CTD26/board.png"
PIECE_SIZE = (80, 80)

START_PIECES = [
    ["RB", "NB", "BB", "QB", "KB", "BB", "NB", "RB"],
    ["PB", "PB", "PB", "PB", "PB", "PB", "PB", "PB"],
    [None] * 8,
    [None] * 8,
    [None] * 8,
    [None] * 8,
    ["PW", "PW", "PW", "PW", "PW", "PW", "PW", "PW"],
    ["RW", "NW", "BW", "QW", "KW", "BW", "NW", "RW"],
]

SPRITE_PATHS = {
    "PW": "CTD26/pieces2/PW/states/idle/sprites/1.png",
    "PB": "CTD26/pieces2/PB/states/idle/sprites/1.png",
    "RW": "CTD26/pieces2/RW/states/idle/sprites/1.png",
    "RB": "CTD26/pieces2/RB/states/idle/sprites/1.png",
    "NW": "CTD26/pieces2/NW/states/idle/sprites/1.png",
    "NB": "CTD26/pieces2/NB/states/idle/sprites/1.png",
    "BW": "CTD26/pieces2/BW/states/idle/sprites/1.png",
    "BB": "CTD26/pieces2/BB/states/idle/sprites/1.png",
    "QW": "CTD26/pieces2/QW/states/idle/sprites/1.png",
    "QB": "CTD26/pieces2/QB/states/idle/sprites/1.png",
    "KW": "CTD26/pieces2/KW/states/idle/sprites/1.png",
    "KB": "CTD26/pieces2/KB/states/idle/sprites/1.png",
}

def load_sprites():
    sprites = {}
    for code, path in SPRITE_PATHS.items():
        sprites[code] = Img().read(path, size=PIECE_SIZE, keep_aspect=True)
    return sprites

def cell_center(row, col, board_img, piece_img):
    cell_w = board_img.shape[1] / 8
    cell_h = board_img.shape[0] / 8
    x = int(col * cell_w + (cell_w - piece_img.img.shape[1]) / 2)
    y = int(row * cell_h + (cell_h - piece_img.img.shape[0]) / 2)
    return x, y

def draw_board_state(state, sprites):
    frame = Img().read(BOARD_PATH)
    for row in range(8):
        for col in range(8):
            code = state[row][col]
            if code is None:
                continue
            sprite = sprites[code]
            pos = cell_center(row, col, frame.img, sprite)
            sprite.draw_on(frame, *pos)
    return frame

def main():
    sprites = load_sprites()
    state = [row[:] for row in START_PIECES]
    frame = draw_board_state(state, sprites)

    cv2.imshow("Chess Board", frame.img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()