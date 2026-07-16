import os

from model.setup import standard_starting_board
from model.board import Board

def create_initial_board() -> Board:
    return standard_starting_board()
