# agenticgeek

Multi-agent toolkit for Claude Code. Four named agents (atlas, stark, oracle, reed), a full skill/hook/command structure, and an idempotent `install.sh`.

## Agents

| Agent | Superhero | Role |
|-------|-----------|------|
| `atlas-orch` | Atlas | Orchestrator — plans, routes, commits, documents |
| `stark-dev` | Tony Stark | Developer — writes code only |
| `oracle-qa` | Oracle | QA — writes and runs tests, reports PASS/FAIL |
| `reed-research` | Reed Richards | Researcher — web research → markdown report |

## Install

```bash
./install.sh                         # → ~/projects/.claude (default)
./install.sh --target ~/myproject    # → ~/myproject/.claude
./install.sh --global                # → ~/.claude
```

Idempotent — safe to re-run. Requires Node.js and Bash.

## After install

1. Restart Claude Code
2. Copy `templates/CLAUDE.md` content into your project's `CLAUDE.md`
3. Use `/atlas <task>` to orchestrate work

## Atlas workflow

Atlas runs 10 steps for every task, no exceptions:

```
1. MEMORY PRIME     search claude-mem
2. CONTEXT GATHER   ctx_batch_execute
3. RESEARCH GATE    spawn reed if needed
4. BRAINSTORM       superpowers:brainstorming
5. PLAN             superpowers:writing-plans
6. IMPLEMENT        spawn stark-dev
7. TEST             spawn oracle-qa
8. COMMIT           atlas commits (stark never does)
9. DOCUMENT         write to docs/index.html
10. PRESENT         surface result to user
```

No commit ships without oracle PASS.

## Structure

```
.claude/skills/
├── atlas-orch/SKILL.md           orchestrator (skill only)
├── stark-dev/SKILL.md            developer agent
├── stark-dev/agent-def.json      tool restrictions
├── oracle-qa/SKILL.md            QA agent
├── oracle-qa/agent-def.json      tool restrictions
├── reed-research/SKILL.md        researcher agent
└── reed-research/agent-def.json  tool restrictions
.claude/settings.json             agent type definitions
hooks/
├── sessionstart.sh
├── pretooluse.sh
└── posttooluse.sh
commands/atlas.md                 /atlas slash command
templates/CLAUDE.md               starter project memory
install.sh
```
