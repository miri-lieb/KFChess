import os
import sys

import cv2

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from engine.game_runner import GameRunner
from view.board_renderer import board_image, board_origin, draw_board, draw_selection, draw_legal_moves, draw_rest_animation
from view.sprite_loader import load_sprites
from view.ui_renderer import compose_game_frame
from view.board_setup import create_initial_board
from view.input_handler import on_mouse
from view.interfaces import EngineView, ControllerView, Renderer, GameSnapshot
from config import WINDOW_TITLE


class OpenCVRenderer:
    """OpenCV-based renderer for the game."""

    def __init__(self):
        self.sprites = load_sprites()
        self.board_img = board_image()
        self.window_name = WINDOW_TITLE
        cv2.namedWindow(self.window_name)
        self._mouse_param = None

    def set_mouse_callback(self, controller, engine, state):
        """Set up mouse callback with necessary parameters."""
        self._mouse_param = {
            "controller": controller,
            "engine": engine,
            "rest_timers": state.rest_timers,
            "short_rest_timers": state.short_rest_timers,
            "jump_timers": state.jump_timers,
            "board_img": self.board_img.img,
            "move_log": state.move_log,
            "start_time": state.start_time,
            "legal_moves": state.legal_moves,
            "board_origin": board_origin,
        }
        cv2.setMouseCallback(self.window_name, on_mouse, self._mouse_param)

    def render(self, engine: EngineView, controller: ControllerView, state: GameSnapshot):
        frame = draw_board(
            engine.board,
            engine.arbiter.active_motions,
            self.sprites,
            state.animation_tick,
            state.rest_timers,
            state.short_rest_timers,
            state.jump_timers,
            engine.arbiter.elapsed_time_ms,
        )
        draw_rest_animation(frame, state.rest_timers, state.short_rest_timers, state.jump_timers, self.board_img.img, state.animation_tick)
        draw_legal_moves(frame, state.legal_moves, self.board_img.img)
        draw_selection(frame, controller.selected, self.board_img.img)
        composed = compose_game_frame(frame, state.move_log, state.scores, state.game_over)
        cv2.imshow(self.window_name, composed.img)

    def handle_input(self, controller: ControllerView, engine: EngineView, state: GameSnapshot) -> bool:
        key = cv2.waitKey(20)
        return key != 27  # Return False if ESC pressed

    def cleanup(self):
        cv2.destroyAllWindows()


def create_game():
    """Factory function to create engine and controller."""
    from engine.game_engine import GameEngine
    from input.controller import Controller
    board = create_initial_board()
    engine = GameEngine(board)
    controller = Controller(engine)
    return engine, controller

def main():
    engine, controller = create_game()
    renderer = OpenCVRenderer()
    runner = GameRunner(engine, controller)

    def render_callback(engine, controller, state):
        # Update mouse callback with current state
        renderer.set_mouse_callback(controller, engine, state)
        renderer.render(engine, controller, state)
        if not renderer.handle_input(controller, engine, state):
            raise KeyboardInterrupt()
    runner.run(render_callback)

if __name__ == "__main__":
    main()
