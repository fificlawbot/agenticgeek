# /atlas

Invoke atlas orchestrator for any non-trivial task.

## Usage

```
/atlas <task description>
```

## What atlas does

Atlas runs a strict 10-step workflow for every task:

1. **MEMORY PRIME** — search claude-mem for prior relevant context
2. **CONTEXT GATHER** — batch-gather codebase state via context-mode
3. **RESEARCH GATE** — spawn reed-research if domain is unknown
4. **BRAINSTORM** — invoke superpowers:brainstorming skill
5. **PLAN** — invoke superpowers:writing-plans skill
6. **IMPLEMENT** — spawn stark-dev with the plan
7. **TEST** — spawn oracle-qa to verify correctness
8. **COMMIT** — atlas commits atomically (stark never commits)
9. **DOCUMENT** — append task summary to docs/index.html
10. **PRESENT** — surface result + commit hash to user

## When to use

Use `/atlas` for any task that involves writing or changing code. For quick lookups or one-line answers, you don't need atlas. For everything else, use it — the workflow overhead pays back in correctness.

## Hard guarantees

- No commit ships without oracle PASS
- No implementation starts without a written plan
- Every completed task gets a docs/index.html entry
