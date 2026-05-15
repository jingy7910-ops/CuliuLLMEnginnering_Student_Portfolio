#!/usr/bin/env python3
"""SGF parser prototype for single game records.

Features:
- Read local .sgf file
- Print game metadata (players, board size, komi, result)
- Print total moves, first 10 moves
- Return move info for user-specified move number
- Convert SGF coordinates to board semantic regions
- Generate beginner-friendly review text via Ollama (Qwen)
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


SGF_MOVE_PATTERN = re.compile(r";([BW])\[([a-s]{0,2})\]")
SGF_PROP_PATTERN = re.compile(r"([A-Z]{1,2})\[([^\]]*)\]")


@dataclass
class Move:
    move_no: int
    color: str
    coord: str
    board_xy: Optional[Tuple[int, int]]
    board_label: str
    region_desc: str


GO_TERMS = {
    "挂角": "在角部试探性落子，争取角地与外势平衡。",
    "拆边": "沿边扩展势力，常与角部配合形成框架。",
    "打入": "进入对方势力范围，破坏对方潜在实地。",
    "征子": "连续追赶吃子手段，路径可预测。",
    "劫": "双方反复提取单子形成争夺，需要劫材。",
    "眼": "棋块内部生存空间，通常两眼活棋。",
    "气": "棋子相邻空点，决定棋块死活基础。",
    "厚势": "稳固外势，强调效率与攻击潜力。",
    "实地": "已较稳定的地盘收益。",
    "定式": "局部常见平衡下法，需结合全局取舍。",
}


def read_sgf(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read().strip()


def parse_root_props(sgf_text: str) -> Dict[str, str]:
    first = sgf_text.find(";")
    second = sgf_text.find(";", first + 1)
    root = sgf_text[first: second if second != -1 else len(sgf_text)]
    props = dict(SGF_PROP_PATTERN.findall(root))
    return props


def sgf_to_xy(coord: str, size: int) -> Optional[Tuple[int, int]]:
    if len(coord) != 2:
        return None
    x = ord(coord[0]) - ord("a")
    y = ord(coord[1]) - ord("a")
    if 0 <= x < size and 0 <= y < size:
        return x, y
    return None


def xy_to_label(x: int, y: int, size: int) -> str:
    col = x + 1
    row = y + 1
    return f"({col},{row})"


def describe_region(x: int, y: int, size: int) -> str:
    left = x < size * 0.3
    right = x >= size * 0.7
    top = y < size * 0.3
    bottom = y >= size * 0.7

    if top and left:
        return "左上角"
    if top and right:
        return "右上角"
    if bottom and left:
        return "左下角"
    if bottom and right:
        return "右下角"

    edge_dist = min(x, y, size - 1 - x, size - 1 - y)
    if edge_dist <= 2:
        if top:
            return "上边三线附近"
        if bottom:
            return "下边三线附近"
        if left:
            return "左边三线附近"
        if right:
            return "右边三线附近"
        return "边路三线附近"

    if size * 0.35 <= x <= size * 0.65 and size * 0.35 <= y <= size * 0.65:
        return "中腹附近"

    return "边向中腹过渡地带"


def parse_moves(sgf_text: str, size: int) -> List[Move]:
    moves: List[Move] = []
    for i, (color, coord) in enumerate(SGF_MOVE_PATTERN.findall(sgf_text), start=1):
        xy = sgf_to_xy(coord, size)
        if xy is None:
            label = "Pass"
            region = "停一手"
        else:
            label = xy_to_label(xy[0], xy[1], size)
            region = describe_region(xy[0], xy[1], size)
        moves.append(Move(i, color, coord or "", xy, label, region))
    return moves


def build_prompt(move: Move, player_black: str, player_white: str, terms: Dict[str, str]) -> str:
    terms_hint = "；".join([f"{k}:{v}" for k, v in terms.items()])
    return (
        "你是一名围棋入门教练。请按固定结构输出：\n"
        "1) 当前局面位置\n"
        "2) 可能意图\n"
        "3) 初学者建议\n\n"
        f"对局：黑{player_black} vs 白{player_white}\n"
        f"当前手：第{move.move_no}手，{ '黑棋' if move.color == 'B' else '白棋' }，SGF坐标{move.coord}，棋盘坐标{move.board_label}，区域{move.region_desc}。\n"
        "要求：\n"
        "- 面向初学者，避免过深算路。\n"
        "- 不少于100字。\n"
        "- 尽量正确使用术语。\n"
        f"术语参考：{terms_hint}\n"
    )


def build_mock_review(move: Move) -> str:
    color = "黑棋" if move.color == "B" else "白棋"
    return (
        f"当前局面位置：第{move.move_no}手由{color}下在{move.region_desc}（{move.board_label}），"
        "这个点通常和角地经营或边上扩张有关，说明此时双方还在围绕效率与方向做取舍。"
        "可能意图：落子一方面希望巩固自身形状与气，另一方面限制对手在该区域的实地潜力，"
        "若后续配合得当，还能形成厚势并争取先手节奏。"
        "初学者建议：先看这手棋与附近已有棋子的联络是否紧凑，再判断是偏向取地还是取势；"
        "不要只盯局部吃子，优先保证自身薄弱处不被打入，必要时参考常见定式思路，但要结合全局判断。"
    )


def call_ollama_review(prompt: str, model: str, timeout_sec: int) -> Optional[str]:
    cmd = ["ollama", "run", model, prompt]
    try:
        result = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None

    if result.returncode != 0:
        return None

    text = (result.stdout or "").strip()
    return text or None


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse SGF and generate a basic review prototype.")
    parser.add_argument("sgf_file", help="Path to .sgf file")
    parser.add_argument("--move", type=int, default=1, help="Move number to inspect (1-based)")
    parser.add_argument("--model", default="qwen2.5:7b", help="Ollama model name")
    parser.add_argument("--timeout", type=int, default=45, help="Ollama timeout seconds")
    args = parser.parse_args()

    if not os.path.exists(args.sgf_file):
        raise FileNotFoundError(f"SGF file not found: {args.sgf_file}")

    sgf_text = read_sgf(args.sgf_file)
    props = parse_root_props(sgf_text)
    size = int(props.get("SZ", "19"))
    pb = props.get("PB", "Unknown")
    pw = props.get("PW", "Unknown")
    komi = props.get("KM", "?")
    result = props.get("RE", "?")

    moves = parse_moves(sgf_text, size)
    total = len(moves)

    print("=== SGF Basic Info ===")
    print(f"File: {args.sgf_file}")
    print(f"Board Size: {size}")
    print(f"Black: {pb}")
    print(f"White: {pw}")
    print(f"Komi: {komi}")
    print(f"Result: {result}")
    print(f"Total Moves: {total}")

    print("\n=== First 10 Moves ===")
    for m in moves[:10]:
        color = "B" if m.color == "B" else "W"
        print(f"{m.move_no:>3}. {color}[{m.coord}] -> {m.board_label} / {m.region_desc}")

    if total == 0:
        print("\nNo moves found in SGF.")
        return

    idx = max(1, min(args.move, total)) - 1
    target = moves[idx]
    who = "黑棋" if target.color == "B" else "白棋"
    print("\n=== Target Move ===")
    print(f"第{target.move_no}手: {who} {target.coord} -> {target.board_label} / {target.region_desc}")

    prompt = build_prompt(target, pb, pw, GO_TERMS)
    review = call_ollama_review(prompt, args.model, args.timeout) or build_mock_review(target)

    print("\n=== Prompt v1 ===")
    print(prompt)
    print("=== Review Draft (>=100 chars) ===")
    print(review)
    print(f"\nReview length: {len(review)}")


if __name__ == "__main__":
    main()
