from typing import Set

from model.board import BoardRepresentation
from model.piece import Piece, ROOK, BISHOP, QUEEN, KNIGHT, KING, PAWN
from model.position import Position
from .interfaces import MoveGenerator


class StandardMoveGenerator:
    def legal_destinations(self, board: BoardRepresentation, piece: Piece) -> Set[Position]:
        kind = piece.kind
        if kind == ROOK:
            return _rook_destinations(board, piece)
        if kind == BISHOP:
            return _bishop_destinations(board, piece)
        if kind == QUEEN:
            return _queen_destinations(board, piece)
        if kind == KNIGHT:
            return _knight_destinations(board, piece)
        if kind == KING:
            return _king_destinations(board, piece)
        if kind == PAWN:
            return _pawn_destinations(board, piece)
        return set()


def legal_destinations(board: BoardRepresentation, piece: Piece) -> Set[Position]:
    """Shared helper to get legal destinations for a piece."""
    return StandardMoveGenerator().legal_destinations(board, piece)


def _sliding_destinations(board: BoardRepresentation, piece: Piece, directions):
    positions: Set[Position] = set()
    for dr, dc in directions:
        current = Position(piece.cell.row + dr, piece.cell.col + dc)
        while board.is_in_bounds(current):
            target = board.get_piece(current)
            if target is None:
                positions.add(current)
            else:
                if target.color != piece.color:
                    positions.add(current)
                break
            current = Position(current.row + dr, current.col + dc)
    return positions


def _rook_destinations(board: BoardRepresentation, piece: Piece):
    return _sliding_destinations(board, piece, [(1, 0), (-1, 0), (0, 1), (0, -1)])


def _bishop_destinations(board: BoardRepresentation, piece: Piece):
    return _sliding_destinations(board, piece, [(1, 1), (1, -1), (-1, 1), (-1, -1)])


def _queen_destinations(board: BoardRepresentation, piece: Piece):
    return _sliding_destinations(
        board,
        piece,
        [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)],
    )


def _knight_destinations(board: BoardRepresentation, piece: Piece):
    positions: Set[Position] = set()
    for dr, dc in [(1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)]:
        candidate = Position(piece.cell.row + dr, piece.cell.col + dc)
        if board.is_in_bounds(candidate):
            target = board.get_piece(candidate)
            if target is None or target.color != piece.color:
                positions.add(candidate)
    return positions


def _king_destinations(board: BoardRepresentation, piece: Piece):
    positions: Set[Position] = set()
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            candidate = Position(piece.cell.row + dr, piece.cell.col + dc)
            if board.is_in_bounds(candidate):
                target = board.get_piece(candidate)
                if target is None or target.color != piece.color:
                    positions.add(candidate)
    return positions


def _pawn_destinations(board: BoardRepresentation, piece: Piece):
    positions: Set[Position] = set()
    forward = -1 if piece.color == "white" else 1
    row = piece.cell.row
    col = piece.cell.col
    forward_pos = Position(row + forward, col)
    if board.is_in_bounds(forward_pos) and board.get_piece(forward_pos) is None:
        positions.add(forward_pos)
    for dc in (-1, 1):
        capture = Position(row + forward, col + dc)
        if board.is_in_bounds(capture):
            target = board.get_piece(capture)
            if target is not None and target.color != piece.color:
                positions.add(capture)
    return positions