# Reflection L12 - 2026-06-20

今天我把 Lesson12 的 student project agent 从“能跑的 baseline”推进到更可检查的版本。这个项目的核心不是让 Subagent 直接完成最终答案，而是让 MainAgent 记住用户目标、明确最终交付标准，再把资料整理这部分安全地委托给 ResearchSubagent。

## 今天完成了什么

第一步，我先梳理了整个项目，并写了 `AGENTS.md`。这让我更清楚地看到当前系统的流程：用户输入进入 MainAgentPlanner，MainAgent 决定是否委托 ResearchSubagent，Subagent 读取本地资料和受控 mock web_search，Validator 检查结果，最后 MainAgentExecutor 恢复任务并生成最终项目计划。这个过程已经可以在网页上通过 timeline 和 JSON payload 看到。

第二步，我完成了 Mission 1：让 MainAgent 记住任务。原来的 `main_agent_state` 太泛，只写了 TODO，无法约束后续输出。我修改了 `main_agent.py` 和 `prompts/main_agent_planner.md`，让状态里包含更具体的 `interpreted_task`、`final_deliverable`、`success_criteria` 和 `next_action_after_subagent`。同时我加入了后续三轮 AI Coding 都要遵守的护栏：ResearchSubagent 只能整理证据，不能写最终项目计划、完整报告，也不能编造搜索证据。一旦越权，预期 failure_type 是 `permission_denied`。

第三步，我完成了 Mission 2：让 Subagent 返回可验收证据。我在 `prompts/research_subagent_executor.md` 里定义了 `subagent_result` schema，并要求每条 evidence 都包含 `claim`、`support`、`source_id` 或 `web_source_id`、`credibility`、`uncertainty_note`。然后我修改了 `validators.py`，让 validator 检查 citations 是否非空、source_id 是否能在 `source_index.json` 中找到、web evidence 是否有 `title/url/credibility`、有没有越权写 final_plan/project_plan/final_report，以及是否包含 uncertainty 和 missing_info。

## 验证结果

我运行了 `case_03` 来验证 Mission 1。结果显示 `main_agent_state` 已经能保留用户的真实目标，并生成更明确的 delegation_request。虽然本地 Ollama 当前不可达，系统走了 offline fallback，但 fallback 下仍然能看到 MainAgent 的状态和护栏字段。

我运行了 `case_04` 来验证 Mission 2。这个 case 要求 ResearchSubagent 直接写完整 800 字报告并引用 `source_99`，属于越权和潜在编造来源。新的 validator 已经能拒绝它，并记录：

```json
{
  "ok": false,
  "failure_type": "permission_denied",
  "failure_category": "指令违背"
}
```

网页端也已经启动在 `http://127.0.0.1:5012`，可以选择 case 并查看每一步的 payload。

## 今天的收获

今天最大的收获是：Agent 的能力不只来自 prompt，也来自清楚的职责边界和可执行的 validator。之前 Subagent 只要返回一段自然语言，系统就很难判断它是否真的完成了任务；现在每条证据都必须能追溯来源，坏结果也会留下明确 failure_type。

另一个收获是 MainAgent 的状态很重要。如果 MainAgent 不先写清楚最终交付物和验收标准，Subagent 很容易把“整理证据”误解成“替用户完成最终报告”。把 `main_agent_state` 做具体以后，后续恢复任务和最终输出才有依据。

## 下一步

下一步应该进入 Mission 3：让 MainAgentExecutor 在 Subagent 返回后真正恢复原始目标，根据 validator 结果决定 accept、reject 或 fallback，并生成结构化、可执行的最终项目计划。同时也应该继续加强 `validate_final_output()`，避免最终输出只是空泛总结。
