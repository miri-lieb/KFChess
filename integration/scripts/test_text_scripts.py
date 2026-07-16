import glob
from texttests.script_parser import parse_script_lines
from texttests.script_runner import run_script


def _load_script(path: str):
    with open(path, "r") as f:
        return f.readlines()


def test_all_scripts():
    paths = glob.glob("integration/scripts/*.kfc")
    for p in paths:
        lines = _load_script(p)
        cmds = parse_script_lines(lines)
        # run the script; ensure no exceptions
        run_script(lines)
