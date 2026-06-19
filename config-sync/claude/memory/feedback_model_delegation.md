---
name: feedback-model-delegation
description: "Workflow — main-session model (Opus/Fable) plans/reviews ONLY; ALL execution delegated to Sonnet subagents"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 46054513-c169-4df2-9981-51ecfc228a39
---

For ALL work: main-session model (Opus or Fable — "the brain") does planning, design, and review ONLY; delegate ALL execution (coding, script runs, file ops, research legwork) to **Sonnet** subagents via the Agent tool with `model: "sonnet"`. Main session should not execute inline — not just code-writing, any execution. Broadened 2026-06-12 ("all executions in subagent via sonnet"); previously reaffirmed 2026-06-10.

**Why:** User wants the big model's reasoning for plans/specs/review but cheaper Sonnet execution for writing code. Set 2026-05-28.

**How to apply:** When a task reaches the implementation stage (after a plan/spec exists), spawn a Sonnet subagent with a tight self-contained brief (file paths, line numbers, exact changes) rather than editing directly. Opus then verifies the returned diff before reporting done. Manual `/model` switching is the user's job — I can only set the model on subagents I spawn. User mentioned an orchestrator concept named "atlas" but it is not yet defined in this environment (no agent file/SDK script found 2026-05-28).

**Orchestration bar (confirmed 2026-06-13):** User approved Opus judging the line. Opus may do directly: read-only checks (curl health, ls, git status), memory-file writes, MEMORY.md edits, launching a local preview server. Subagents do ALL: code/data edits, git commits/push, API calls, research legwork, script runs. When unsure → subagent. Fallback model when Fable unavailable = Opus 4.6.
