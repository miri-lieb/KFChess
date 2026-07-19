from model.piece import Piece
from model.position import Position

def move_notation(piece: Piece, source: Position, destination: Position, captured: Piece = None) -> str:
    piece_letter = piece.kind[0].upper()
    if piece.kind == "knight":
        piece_letter = "N"
    src_file = chr(ord('a') + source.col)
    src_rank = str(8 - source.row)
    dst_file = chr(ord('a') + destination.col)
    dst_rank = str(8 - destination.row)
    capture = "x" if captured else ""
    if piece.kind == "pawn":
        return f"{src_file}{capture}{dst_file}{dst_rank}"
    return f"{piece_letter}{capture}{dst_file}{dst_rank}"