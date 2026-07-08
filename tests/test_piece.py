import os
import sys

# Ensure we can import modules from files/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'files'))

from piece import Piece


def test_from_token_dot_returns_none():
    assert Piece.from_token('.') is None


def test_from_token_roundtrip():
    p = Piece.from_token('wK')
    assert p is not None
    assert p.color == 'w'
    assert p.type == 'K'
    assert p.token == 'wK'
