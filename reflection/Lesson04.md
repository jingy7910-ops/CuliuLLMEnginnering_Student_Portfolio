今天主要完成了 Lesson 04 这个“唐诗写作 Agent”项目，从讲义理解一直做到系统落地和格式修正。

今天做的核心事情有这些：
    读了 student_handout4.md，明确这节课要做的是一个最小可用的唐诗写作 RAG 系统。
        1.确认数据源固定使用 300.json。
        2.搭好了完整项目 poem_rag_agent：
        3.建库脚本 build_index.py
        4.后端服务 app.py
    RAG 核心逻辑 rag_engine.py
    前端页面 index.html
    把系统从“离线降级版”改成了真正接入本机 Ollama 的版本：
        embedding 用 bge-m3
        generation 用 qwen3.5:0.8b
    实际验证了真 RAG 已经能跑通：
        api/rag/health 返回 embedding_mode=ollama
        /api/rag/ask 能返回 poem、citations、retrieved、query_vector
    还补齐了课堂作业要交的文档：
        rag_lesson04_plan.md
        qa_eval_lesson04.csv
        failure_cases_lesson04.md
后面我又连续发现并修正了几个格式问题：

    诗有时不是 4 行
    每一行末尾没有句号
    七言绝句会生成成五言
    没有标题
    所以现在后端已经按更严格的格式约束去处理了：

有标题，第一行是 《题目》
    五言绝句：4 行，每行 5 字，句末 。
    五言律诗：8 行，每行 5 字，句末 。
    七言绝句：4 行，每行 7 字，句末 。
    七言律诗：8 行，每行 7 字，句末 。

今天我们（我和AI）把 Lesson 04 从“看讲义”推进到了“一个可运行、接入 Ollama、并且能按体裁格式约束输出的唐诗写作 RAG 系统”。