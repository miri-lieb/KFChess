from model.player import Player
from model.piece import Piece
from model.position import Position
def test_player_capture_list():
    p = Player(color="white", name="Alice")
    piece = Piece(id="x", color="black", kind="pawn", cell=Position(1, 1))
    assert p.captured_pieces == []
    p.capture(piece)
    assert p.captured_pieces == [piece]
