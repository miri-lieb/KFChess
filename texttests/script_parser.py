from typing import List


def parse_script_lines(lines: List[str]) -> List[str]:
    # Simple parser: strips comments and blank lines, returns command lines
    out = []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        out.append(line)
    return out
