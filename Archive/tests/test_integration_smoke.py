import os
import sys
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'files'))


def test_smoke_main_moves_pawn(tmp_path):
    input_text = """
Board:
. . .
. . .
. wP .
Commands:
click 100 200
click 100 100
wait 1000
print board
"""
    p = subprocess.run(['python3', 'files/main.py'], input=input_text, text=True, capture_output=True)
    out = p.stdout.strip()
    # expect full board printed (top-to-bottom)
    expected = '. . .\n. wP .\n. . .'
    assert out == expected
