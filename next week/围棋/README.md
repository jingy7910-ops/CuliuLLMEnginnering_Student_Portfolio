# 围棋 SGF 复盘网页

## 运行

```bash
cd "/Users/albertyan/Desktop/CuliuLLMEnginnering_Student_Portfolio/next week"
python3 -m pip install -r requirements.txt
streamlit run app.py
```

## 功能

- 上传 SGF 文件或选择内置样本
- 输入指定手数
- 调用 Ollama/Qwen 生成复盘
- 展示前10手、指定手信息、Prompt 和复盘结果
