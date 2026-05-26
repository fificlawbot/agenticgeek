# agenticgeek — Multi-Agent Toolkit Design

**Date:** 2026-05-22  
**Status:** Approved  
**Scope:** Private GitHub repo with installable Claude Code agents, skills, hooks, commands

---

## Overview

`agenticgeek` is a personal multi-agent toolkit for Claude Code. It ships four named agents (atlas, stark, oracle, reed), a full repo structure for skills/hooks/commands, and an `install.sh` that drops everything into a target project workspace.

The core philosophy: atlas orchestrates, stark builds, oracle verifies, reed researches. Atlas never skips planning. Stark never commits. oracle never ships without a green test run.

---

## Architecture

### Agent Roles

| Agent | Superhero | Role | Type |
|-------|-----------|------|------|
| `atlas-orch` | Atlas | Orchestrator — plans, routes, commits, documents | Skill only (main context) |
| `stark-dev` | Tony Stark | Developer — writes code only | Agent type + Skill |
| `oracle-qa` | Oracle | QA — writes and runs tests, reports PASS/FAIL | Agent type + Skill |
| `reed-research` | Reed Richards | Researcher — web research → markdown report | Agent type + Skill |

**Why atlas is skill-only:** Orchestrators need full tool access and shared context to route decisions. Spawning atlas as a subagent would create unnecessary isolation.

**Why stark/oracle/reed are agent types:** Isolation enforces role boundaries. stark cannot run tests. oracle cannot edit source files. reed cannot commit. Tool permissions enforced at the agent type level in `settings.json`.

---

## Atlas Workflow (strict, ordered)

Atlas must follow this sequence for every task:

```
1. MEMORY PRIME     → claude-mem search for prior relevant context
2. CONTEXT GATHER   → ctx_batch_execute (codebase state, task context, recent commits)
3. RESEARCH GATE    → if unknown domain/API → spawn reed-research Agent
4. BRAINSTORM       → invoke superpowers:brainstorming skill
5. PLAN             → invoke superpowers:writing-plans skill
6. IMPLEMENT        → spawn stark-dev Agent with plan
7. TEST             → spawn oracle-qa Agent with implementation
8. COMMIT           → atlas commits atomically (stark never commits)
9. DOCUMENT         → write HTML summary to docs/index.html
10. PRESENT         → surface result to user
```

**Hard constraints:**
- Atlas MUST NOT skip steps 1–5 even for "simple" tasks
- Atlas MUST NOT commit until oracle returns PASS
- Atlas MUST write HTML doc for every completed task

---

## Agent Tool Permissions

### stark-dev
```json
{
  "tools": ["Read", "Edit", "Write", "Bash"],
  "restrictions": "No WebSearch, No Agent spawn, No git commit"
}
```

### oracle-qa
```json
{
  "tools": ["Read", "Write", "Bash"],
  "restrictions": "No Edit on source files, No git commit, No WebSearch"
}
```

### reed-research
```json
{
  "tools": ["Read", "Bash", "WebSearch", "WebFetch"],
  "restrictions": "No Edit, No Write to source, No git commit"
}
```

---

## Repo Structure

```
agenticgeek/
├── .claude/
│   ├── skills/
│   │   ├── atlas-orch/
│   │   │   └── SKILL.md
│   │   ├── stark-dev/
│   │   │   ├── SKILL.md
│   │   │   └── agent-def.json
│   │   ├── oracle-qa/
│   │   │   ├── SKILL.md
│   │   │   └── agent-def.json
│   │   └── reed-research/
│   │       ├── SKILL.md
│   │       └── agent-def.json
│   └── settings.json
├── hooks/
│   ├── sessionstart.sh       # auto-prime memory + context on session start
│   ├── pretooluse.sh         # pre-tool guardrails
│   └── posttooluse.sh        # post-tool logging
├── commands/
│   └── atlas.md              # /atlas slash command definition
├── templates/
│   └── CLAUDE.md             # starter project memory template
├── docs/
│   ├── superpowers/
│   │   └── specs/            # design docs (this file lives here)
│   └── index.html            # results dashboard (atlas writes here per task)
├── install.sh
└── README.md
```

---

## install.sh Behavior

```
Usage: ./install.sh [--target <path>] [--global]

Default target: ~/projects/.claude/

Steps:
1. Copy .claude/skills/* → <target>/skills/
2. Read each agent-def.json → merge agent type defs into <target>/settings.json
3. Copy hooks/* → ~/.claude/hooks/
4. Register hooks in ~/.claude/settings.json SessionStart/PreToolUse/PostToolUse
5. Print install summary: which agents installed, where
```

Idempotent — re-running overwrites without duplicating settings entries.

---

## Memory & Context Strategy (Atlas)

Before every task atlas runs:

```bash
# 1. Search claude-mem for relevant prior work
mcp claude-mem search "<task keywords>"

# 2. Batch-gather context into context-mode sandbox
ctx_batch_execute([
  {label: "repo structure", command: "find . -type f | head -50"},
  {label: "recent commits", command: "git log --oneline -10"},
  {label: "task-relevant files", command: "grep -r '<keyword>' --include='*.py' -l"}
])
```

This pattern keeps raw output out of context window while giving atlas the intelligence it needs to plan.

---

## HTML Documentation

After every completed task, atlas writes/appends to `docs/index.html`:

- Task name + timestamp
- Agents spawned
- Plan summary (link to spec)
- Test result (oracle PASS/FAIL)
- Commit hash
- Key files changed

Format: clean HTML, no framework dependency, readable in any browser.

---

## Success Criteria

- `install.sh` runs cleanly on a fresh `~/projects/` workspace
- All four agents appear in `settings.json` after install
- Atlas skill file triggers correctly via `/atlas` command
- stark-dev cannot run git commit (tool restriction enforced)
- oracle-qa cannot edit source files (tool restriction enforced)
- reed-research produces markdown report atlas can consume
- HTML doc generated after a test task run
