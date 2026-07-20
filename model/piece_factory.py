"""Piece Factory for consistent piece creation."""

from typing import Optional
from model.piece import Piece, WHITE, BLACK, KING, QUEEN, ROOK, BISHOP, KNIGHT, PAWN
from model.position import Position

class PieceFactory:
    """Factory for creating pieces with consistent IDs and properties."""
    
    _counter = 0
    
    @classmethod
    def create(
        cls,
        kind: str,
        color: str,
        position: Position,
        piece_id: Optional[str] = None,
    ) -> Piece:
        """Create a new piece.
        
        Args:
            kind: Piece type (KING, QUEEN, ROOK, BISHOP, KNIGHT, PAWN)
            color: Piece color (WHITE, BLACK)
            position: Board position
            piece_id: Optional custom ID (auto-generated if not provided)
            
        Returns:
            New Piece instance
        """
        if piece_id is None:
            cls._counter += 1
            kind_initial = kind[0].upper() if kind else "P"
            piece_id = f"{kind_initial}{color[0].upper()}-{position.row}-{position.col}-{cls._counter}"
            
        return Piece(
            id=piece_id,
            color=color,
            kind=kind,
            cell=position,
        )
    
    @classmethod
    def create_pawn(cls, color: str, position: Position, piece_id: Optional[str] = None) -> Piece:
        return cls.create(PAWN, color, position, piece_id)
    
    @classmethod
    def create_rook(cls, color: str, position: Position, piece_id: Optional[str] = None) -> Piece:
        return cls.create(ROOK, color, position, piece_id)
    
    @classmethod
    def create_knight(cls, color: str, position: Position, piece_id: Optional[str] = None) -> Piece:
        return cls.create(KNIGHT, color, position, piece_id)
    
    @classmethod
    def create_bishop(cls, color: str, position: Position, piece_id: Optional[str] = None) -> Piece:
        return cls.create(BISHOP, color, position, piece_id)
    
    @classmethod
    def create_queen(cls, color: str, position: Position, piece_id: Optional[str] = None) -> Piece:
        return cls.create(QUEEN, color, position, piece_id)
    
    @classmethod
    def create_king(cls, color: str, position: Position, piece_id: Optional[str] = None) -> Piece:
        return cls.create(KING, color, position, piece_id)
    
    @classmethod
    def create_promoted_queen(cls, original_piece: Piece, position: Position) -> Piece:
        """Create a queen from a promoted pawn."""
        return cls.create(
            kind=QUEEN,
            color=original_piece.color,
            position=position,
            piece_id=f"Q{original_piece.color[0].upper()}-{position.row}-{position.col}",
        )
    
    @classmethod
    def reset_counter(cls):
        """Reset the ID counter (useful for tests)."""
        cls._counter = 0

# Convenience function for backward compatibility
def create_piece(kind: str, color: str, position: Position, piece_id: Optional[str] = None) -> Piece:
    return PieceFactory.create(kind, color, position, piece_id)