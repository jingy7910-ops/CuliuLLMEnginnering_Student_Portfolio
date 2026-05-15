#!/usr/bin/env python3
import os
import tempfile
import json

import streamlit as st
import pandas as pd
import altair as alt

from parse_sgf import (
    GO_TERMS,
    build_mock_review,
    build_prompt,
    call_ollama_review,
    parse_moves,
    parse_root_props,
    read_sgf,
)


st.set_page_config(page_title="围棋 SGF 复盘原型", layout="wide")
st.title("围棋 SGF 复盘原型（MVP Web）")
st.caption("上传 SGF，指定手数，调用 Ollama/Qwen 生成初学者复盘说明")

with st.sidebar:
    st.header("参数区")
    uploaded = st.file_uploader("上传 SGF 文件", type=["sgf"])
    sample_path = st.selectbox(
        "或直接选择本地样本",
        options=["", "sgf_samples/opening_sample.sgf", "sgf_samples/middlegame_sample.sgf", "sgf_samples/endgame_sample.sgf"],
    )
    move_no = st.number_input("指定手数（1-based）", min_value=1, value=7, step=1)
    model_name = st.text_input("Ollama 模型名", value="qwen2.5:7b")
    timeout = st.number_input("超时秒数", min_value=5, value=60, step=5)
    run_btn = st.button("开始解析并生成复盘", type="primary", use_container_width=True)

left, right = st.columns([1, 1])

sgf_path = None
if uploaded is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".sgf") as tmp:
        tmp.write(uploaded.getvalue())
        sgf_path = tmp.name
elif sample_path:
    sgf_path = sample_path

if run_btn:
    if not sgf_path:
        st.error("请先上传 SGF 文件或选择样本。")
    else:
        try:
            sgf_text = read_sgf(sgf_path)
            props = parse_root_props(sgf_text)
            size = int(props.get("SZ", "19"))
            pb = props.get("PB", "Unknown")
            pw = props.get("PW", "Unknown")
            km = props.get("KM", "?")
            re_ = props.get("RE", "?")

            moves = parse_moves(sgf_text, size)
            if not moves:
                st.error("该 SGF 未解析到有效着手。")
            else:
                idx = max(1, min(int(move_no), len(moves))) - 1
                target = moves[idx]

                prompt = build_prompt(target, pb, pw, GO_TERMS)
                review = call_ollama_review(prompt, model_name, int(timeout))
                source = "model"
                if not review:
                    review = build_mock_review(target)
                    source = "fallback"

                with right:
                    st.subheader("对局基本信息")
                    st.write({
                        "file": os.path.basename(sgf_path),
                        "board_size": size,
                        "black": pb,
                        "white": pw,
                        "komi": km,
                        "result": re_,
                        "total_moves": len(moves),
                    })

                    st.subheader("前10手")
                    first10 = [
                        {
                            "move": m.move_no,
                            "color": m.color,
                            "sgf": m.coord,
                            "board": m.board_label,
                            "region": m.region_desc,
                        }
                        for m in moves[:10]
                    ]
                    st.table(first10)

                    st.subheader("指定手信息")
                    st.write({
                        "move": target.move_no,
                        "color": "黑棋" if target.color == "B" else "白棋",
                        "sgf": target.coord,
                        "board": target.board_label,
                        "region": target.region_desc,
                    })

                    st.subheader("复盘 Prompt v1")
                    st.code(prompt)

                    st.subheader("模型复盘输出")
                    st.info(f"输出来源: {source}")
                    st.write(review)
                    st.write({"review_length": len(review), "min_100_ok": len(review) >= 100})

                with left:
                    st.subheader("棋盘可视化（19x19）")
                    grid = []
                    for x in range(1, size + 1):
                        for y in range(1, size + 1):
                            grid.append({"x": x, "y": y})
                    grid_df = pd.DataFrame(grid)

                    stone_points = []
                    for m in moves[:10]:
                        if m.board_xy is None:
                            continue
                        x = m.board_xy[0] + 1
                        y = m.board_xy[1] + 1
                        stone_points.append(
                            {
                                "x": x,
                                "y": y,
                                "move": m.move_no,
                                "color": "black" if m.color == "B" else "white",
                                "is_target": m.move_no == target.move_no,
                            }
                        )
                    if target.move_no > 10 and target.board_xy is not None:
                        stone_points.append(
                            {
                                "x": target.board_xy[0] + 1,
                                "y": target.board_xy[1] + 1,
                                "move": target.move_no,
                                "color": "black" if target.color == "B" else "white",
                                "is_target": True,
                            }
                        )
                    stones_df = pd.DataFrame(stone_points)

                    base = (
                        alt.Chart(grid_df)
                        .mark_point(size=40, opacity=0.15)
                        .encode(
                            x=alt.X("x:Q", scale=alt.Scale(domain=[1, size]), axis=alt.Axis(title="列")),
                            y=alt.Y("y:Q", scale=alt.Scale(domain=[size, 1]), axis=alt.Axis(title="行")),
                        )
                        .properties(height=500)
                    )

                    if not stones_df.empty:
                        stones = (
                            alt.Chart(stones_df)
                            .mark_circle(size=180, stroke="black")
                            .encode(
                                x="x:Q",
                                y=alt.Y("y:Q", scale=alt.Scale(domain=[size, 1])),
                                color=alt.Color("color:N", scale=alt.Scale(domain=["black", "white"], range=["#000000", "#FFFFFF"]), legend=None),
                                tooltip=["move:Q", "x:Q", "y:Q", "color:N", "is_target:N"],
                            )
                        )
                        labels = (
                            alt.Chart(stones_df)
                            .mark_text(fontSize=10)
                            .encode(
                                x="x:Q",
                                y=alt.Y("y:Q", scale=alt.Scale(domain=[size, 1])),
                                text="move:Q",
                                color=alt.condition(alt.datum.color == "black", alt.value("white"), alt.value("black")),
                            )
                        )
                        chart = base + stones + labels
                    else:
                        chart = base

                    st.altair_chart(chart, use_container_width=True)
                    st.caption("展示前10手；若指定手不在前10手，也会额外高亮该手。")

        finally:
            if uploaded is not None and sgf_path and os.path.exists(sgf_path):
                os.unlink(sgf_path)

st.divider()
st.subheader("历史评测结果面板")
eval_path = "docs/eval_log.json"
if os.path.exists(eval_path):
    try:
        with open(eval_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        st.write({
            "timestamp": data.get("timestamp"),
            "model": data.get("model"),
            "all_pass": data.get("all_pass"),
        })
        cases = data.get("cases", [])
        if cases:
            st.table(pd.DataFrame(cases))
        else:
            st.info("评测日志存在，但未包含 case 数据。")
    except Exception as e:
        st.error(f"读取评测日志失败: {e}")
else:
    st.info("未找到历史评测日志。先运行 `python3 run_eval.py > docs/eval_log.json`。")
