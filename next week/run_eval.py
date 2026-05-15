#!/usr/bin/env python3
import json
import re
import subprocess
from datetime import datetime

CASES = [
    ("sgf_samples/opening_sample.sgf", 7),
    ("sgf_samples/middlegame_sample.sgf", 22),
    ("sgf_samples/endgame_sample.sgf", 34),
]
MODEL = "qwen2.5:7b"


def run_case(path: str, move: int):
    cmd = ["python3", "parse_sgf.py", path, "--move", str(move), "--model", MODEL, "--timeout", "60"]
    p = subprocess.run(cmd, capture_output=True, text=True)
    out = p.stdout

    target_line = ""
    review_length = 0
    used_fallback = ""

    for line in out.splitlines():
        if line.startswith("第") and "手:" in line:
            target_line = line
        if line.startswith("Review length:"):
            m = re.search(r"(\d+)", line)
            if m:
                review_length = int(m.group(1))

    if "=== Review Draft" in out and "当前局面位置：" in out:
        used_fallback = "possible"
    else:
        used_fallback = "unknown"

    return {
        "file": path,
        "move": move,
        "exit_code": p.returncode,
        "target": target_line,
        "review_length": review_length,
        "min_100_ok": review_length >= 100,
        "fallback_hint": used_fallback,
    }


def main():
    records = [run_case(path, move) for path, move in CASES]
    report = {
        "timestamp": datetime.now().isoformat(),
        "model": MODEL,
        "cases": records,
        "all_pass": all(r["exit_code"] == 0 and r["min_100_ok"] for r in records),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
