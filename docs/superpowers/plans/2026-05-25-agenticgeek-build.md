# agenticgeek Build Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the agenticgeek multi-agent toolkit: four named agents, hooks, commands, and an idempotent install.sh that drops everything into a target project workspace.

**Architecture:** Skill files (SKILL.md) define agent behavior; agent-def.json files define tool restrictions merged into settings.json by install.sh. Atlas is skill-only (runs in main context); stark/oracle/reed are subagent types with enforced tool boundaries.

**Tech Stack:** Bash, JSON, Markdown, Node.js (for JSON merging in install.sh)

---

### Task 1: Git init + directory scaffold

**Files:**
- Create: `.claude/skills/atlas-orch/`
- Create: `.claude/skills/stark-dev/`
- Create: `.claude/skills/oracle-qa/`
- Create: `.claude/skills/reed-research/`
- Create: `hooks/`
- Create: `commands/`
- Create: `templates/`

- [ ] **Step 1: Create directory structure**

```bash
cd /Users/trp/projects/agenticgeek
mkdir -p .claude/skills/atlas-orch
mkdir -p .claude/skills/stark-dev
mkdir -p .claude/skills/oracle-qa
mkdir -p .claude/skills/reed-research
mkdir -p hooks commands templates
```

- [ ] **Step 2: Init git if not already done**

```bash
cd /Users/trp/projects/agenticgeek
git init
git add docs/
git commit -m "init: add design doc and plans"
```

Expected: `Initialized empty Git repository` or `Already initialized`, then commit confirmation.

---

### Task 2: Atlas orchestrator skill

**Files:**
- Create: `.claude/skills/atlas-orch/SKILL.md`

- [ ] **Step 1: Write atlas SKILL.md**

Create `.claude/skills/atlas-orch/SKILL.md`:

```markdown
# atlas-orch — Orchestrator

You are atlas. You orchestrate every task using a fixed 10-step workflow. You NEVER skip steps, even for "simple" tasks.

## Workflow (strict, ordered)

### Step 1: MEMORY PRIME
Search claude-mem for prior relevant context:
```
Use mcp__plugin_claude-mem_mcp-search__search(query: "<task keywords>", limit: 10)
```

### Step 2: CONTEXT GATHER
Batch-gather codebase state into context-mode sandbox:
```
ctx_batch_execute([
  {label: "repo structure", command: "find . -not -path '*/.git/*' -not -path '*/node_modules/*' | head -60"},
  {label: "recent commits", command: "git log --oneline -10 2>/dev/null || echo 'no git'"},
  {label: "task-relevant files", command: "grep -r '<keyword>' --include='*.py' --include='*.ts' -l 2>/dev/null | head -20"}
], queries: ["task context", "recent changes", "relevant files"])
```

### Step 3: RESEARCH GATE
If the task involves an unknown API, library, or domain:
```
Agent(subagent_type="reed-research", prompt="Research <topic>. Produce markdown report with: summary, key findings, code examples, gotchas, sources.")
```
Skip this step if the domain is well-known from memory/context.

### Step 4: BRAINSTORM
```
Invoke superpowers:brainstorming skill
```

### Step 5: PLAN
```
Invoke superpowers:writing-plans skill
```

### Step 6: IMPLEMENT
Spawn stark-dev with the full plan:
```
Agent(
  subagent_type="stark-dev",
  prompt="Implement the following plan. Report IMPLEMENTATION COMPLETE with a list of files changed when done.\n\n<plan>"
)
```

### Step 7: TEST
Spawn oracle-qa with implementation details from stark:
```
Agent(
  subagent_type="oracle-qa",
  prompt="Test the following implementation. Return PASS or FAIL with full details.\n\nFeature: <feature>\nFiles changed: <files from stark report>"
)
```

### Step 8: COMMIT
Atlas commits. Stark never commits. Only commit after oracle returns PASS:
```bash
git add <changed files>
git commit -m "<type>: <description>"
```

### Step 9: DOCUMENT
Write/append to docs/index.html:
- Task name + timestamp
- Agents spawned
- Plan file path
- Oracle result (PASS/FAIL)
- Commit hash
- Files changed

### Step 10: PRESENT
Surface the result to the user:
- What was built
- Commit hash
- Test result
- Any follow-up items

## Hard Constraints

- MUST NOT skip steps 1–5 even for "simple" tasks
- MUST NOT commit until oracle returns PASS
- MUST write to docs/index.html for every completed task
- MUST use ctx_batch_execute for all context gathering (never raw Bash for >20 lines output)
- If oracle returns FAIL, send fix details back to stark (step 6), re-test (step 7), then commit

## docs/index.html format

Append one `<section>` per task:

```html
<section>
  <h2><task name> — <timestamp></h2>
  <ul>
    <li>Plan: <path to plan file></li>
    <li>Agents: stark-dev, oracle-qa[, reed-research]</li>
    <li>Test: PASS</li>
    <li>Commit: <hash></li>
    <li>Files: <comma-separated list></li>
  </ul>
</section>
```
```

- [ ] **Step 2: Verify file exists**

```bash
cat /Users/trp/projects/agenticgeek/.claude/skills/atlas-orch/SKILL.md | head -5
```

Expected: first 5 lines of the skill file.

- [ ] **Step 3: Commit**

```bash
cd /Users/trp/projects/agenticgeek
git add .claude/skills/atlas-orch/SKILL.md
git commit -m "feat: add atlas-orch orchestrator skill"
```

---

### Task 3: Stark developer skill + agent definition

**Files:**
- Create: `.claude/skills/stark-dev/SKILL.md`
- Create: `.claude/skills/stark-dev/agent-def.json`

- [ ] **Step 1: Write stark SKILL.md**

Create `.claude/skills/stark-dev/SKILL.md`:

```markdown
# stark-dev — Developer

You are stark. You write and edit code. Nothing else.

## Your job

1. Receive a plan from atlas
2. Implement it exactly as specified — no deviations, no extras
3. Report completion with a precise list of files changed

## Hard Constraints

- NEVER run `git commit`, `git push`, or any git write command
- NEVER use WebSearch or WebFetch
- NEVER spawn sub-agents
- NEVER add features beyond what the plan specifies
- If blocked (missing dependency, unclear requirement), STOP and report the blocker — do not guess

## Tools Available

Read, Edit, Write, Bash (for running code/tests, NOT for git commits)

## Completion Report

When done, output exactly:

```
IMPLEMENTATION COMPLETE
Files changed:
- path/to/file.py (new)
- path/to/other.py (modified, lines 42–67)
Tests needed: <brief description of what oracle should verify>
```

## Style Rules

- Minimum code that solves the problem
- No abstractions for single-use code
- No error handling for impossible scenarios
- Match existing file style exactly
- Remove imports/variables your changes made unused
```

- [ ] **Step 2: Write stark agent-def.json**

Create `.claude/skills/stark-dev/agent-def.json`:

```json
{
  "name": "stark-dev",
  "description": "Developer — writes and edits source files. No git commits. No web access. No sub-agents.",
  "allowedTools": ["Read", "Edit", "Write", "Bash"]
}
```

- [ ] **Step 3: Commit**

```bash
cd /Users/trp/projects/agenticgeek
git add .claude/skills/stark-dev/
git commit -m "feat: add stark-dev developer agent"
```

---

### Task 4: Oracle QA skill + agent definition

**Files:**
- Create: `.claude/skills/oracle-qa/SKILL.md`
- Create: `.claude/skills/oracle-qa/agent-def.json`

- [ ] **Step 1: Write oracle SKILL.md**

Create `.claude/skills/oracle-qa/SKILL.md`:

```markdown
# oracle-qa — QA Agent

You are oracle. You verify correctness. Nothing else.

## Your job

1. Receive implementation details from atlas
2. Write tests if none exist for the changed code
3. Run all tests
4. Return explicit PASS or FAIL

## Hard Constraints

- NEVER edit source files (Read is OK; Edit/Write on source files is NOT)
- NEVER run `git commit`
- NEVER use WebSearch or WebFetch
- Write test files to `tests/` directory only

## Tools Available

Read, Write (test files only), Bash (for running tests)

## Pass Report

```
PASS
Tests run: <count>
Test file: <path>
Duration: <seconds>
Output:
<last 20 lines of test run output>
```

## Fail Report

```
FAIL
Failed test: <test name>
Error: <exact error message, quoted>
Root cause: <your diagnosis>
Fix needed in: <file:line>
Suggested fix: <one-sentence description>
```

## Test Writing

When writing tests:
- Test behavior, not implementation
- Cover the happy path first
- Cover the most likely failure modes (bad input, missing data)
- Keep tests small and focused — one concept per test
- Name tests descriptively: `test_<what>_<when>_<expected>`
```

- [ ] **Step 2: Write oracle agent-def.json**

Create `.claude/skills/oracle-qa/agent-def.json`:

```json
{
  "name": "oracle-qa",
  "description": "QA — writes and runs tests. Read-only on source files. No commits. No web access.",
  "allowedTools": ["Read", "Write", "Bash"]
}
```

- [ ] **Step 3: Commit**

```bash
cd /Users/trp/projects/agenticgeek
git add .claude/skills/oracle-qa/
git commit -m "feat: add oracle-qa QA agent"
```

---

### Task 5: Reed research skill + agent definition

**Files:**
- Create: `.claude/skills/reed-research/SKILL.md`
- Create: `.claude/skills/reed-research/agent-def.json`

- [ ] **Step 1: Write reed SKILL.md**

Create `.claude/skills/reed-research/SKILL.md`:

```markdown
# reed-research — Researcher

You are reed. You research. Nothing else.

## Your job

1. Receive a research topic from atlas
2. Search the web and read docs
3. Return a structured markdown report

## Hard Constraints

- NEVER edit source files
- NEVER run `git commit`
- NEVER write to the project source directories
- Write your report as your return value — do not save to files unless atlas asks

## Tools Available

Read, Bash (read-only commands), WebSearch, WebFetch

## Report Format

Return this exact structure:

```markdown
# Research: <topic>

## Summary
<2–3 sentences covering what you found>

## Key Findings
- <finding>
- <finding>

## Code Examples
<relevant snippets with source URLs>

## Gotchas
<pitfalls, rate limits, version quirks, undocumented behavior>

## Sources
- [<title>](<url>)
```

Be specific. Atlas uses your report to make architectural decisions — vague findings waste cycles.
```

- [ ] **Step 2: Write reed agent-def.json**

Create `.claude/skills/reed-research/agent-def.json`:

```json
{
  "name": "reed-research",
  "description": "Researcher — web research to markdown report. No code edits. No commits.",
  "allowedTools": ["Read", "Bash", "WebSearch", "WebFetch"]
}
```

- [ ] **Step 3: Commit**

```bash
cd /Users/trp/projects/agenticgeek
git add .claude/skills/reed-research/
git commit -m "feat: add reed-research researcher agent"
```

---

### Task 6: .claude/settings.json

**Files:**
- Create: `.claude/settings.json`

- [ ] **Step 1: Write settings.json with all three agent types**

Create `.claude/settings.json`:

```json
{
  "agents": [
    {
      "name": "stark-dev",
      "description": "Developer — writes and edits source files. No git commits. No web access. No sub-agents.",
      "allowedTools": ["Read", "Edit", "Write", "Bash"]
    },
    {
      "name": "oracle-qa",
      "description": "QA — writes and runs tests. Read-only on source files. No commits. No web access.",
      "allowedTools": ["Read", "Write", "Bash"]
    },
    {
      "name": "reed-research",
      "description": "Researcher — web research to markdown report. No code edits. No commits.",
      "allowedTools": ["Read", "Bash", "WebSearch", "WebFetch"]
    }
  ]
}
```

- [ ] **Step 2: Verify valid JSON**

```bash
node -e "JSON.parse(require('fs').readFileSync('/Users/trp/projects/agenticgeek/.claude/settings.json', 'utf8')); console.log('valid')"
```

Expected: `valid`

- [ ] **Step 3: Commit**

```bash
cd /Users/trp/projects/agenticgeek
git add .claude/settings.json
git commit -m "feat: add settings.json with agent type definitions"
```

---

### Task 7: Hooks

**Files:**
- Create: `hooks/sessionstart.sh`
- Create: `hooks/pretooluse.sh`
- Create: `hooks/posttooluse.sh`

- [ ] **Step 1: Write sessionstart.sh**

Create `hooks/sessionstart.sh`:

```bash
#!/bin/bash
# agenticgeek session start hook
# Signals ready and injects agent availability note into session context
cat <<'EOF'
{"continue":true,"suppressOutput":false,"status":"agenticgeek-ready","contextNote":"agenticgeek agents available: atlas-orch (skill), stark-dev, oracle-qa, reed-research. Use /atlas to orchestrate tasks."}
EOF
```

- [ ] **Step 2: Write pretooluse.sh**

Create `hooks/pretooluse.sh`:

```bash
#!/bin/bash
# agenticgeek pre-tool hook
# Pass-through — tool guardrails enforced at agent-def level
echo '{"continue":true}'
```

- [ ] **Step 3: Write posttooluse.sh**

Create `hooks/posttooluse.sh`:

```bash
#!/bin/bash
# agenticgeek post-tool hook
# Pass-through — atlas handles documentation in step 9
echo '{"continue":true}'
```

- [ ] **Step 4: Make hooks executable**

```bash
chmod +x /Users/trp/projects/agenticgeek/hooks/sessionstart.sh
chmod +x /Users/trp/projects/agenticgeek/hooks/pretooluse.sh
chmod +x /Users/trp/projects/agenticgeek/hooks/posttooluse.sh
```

- [ ] **Step 5: Verify sessionstart hook produces valid JSON**

```bash
bash /Users/trp/projects/agenticgeek/hooks/sessionstart.sh | node -e "let d=''; process.stdin.on('data',c=>d+=c); process.stdin.on('end',()=>{JSON.parse(d); console.log('valid JSON');})"
```

Expected: `valid JSON`

- [ ] **Step 6: Commit**

```bash
cd /Users/trp/projects/agenticgeek
git add hooks/
git commit -m "feat: add session/pre/post-tool hooks"
```

---

### Task 8: /atlas slash command

**Files:**
- Create: `commands/atlas.md`

- [ ] **Step 1: Write commands/atlas.md**

Create `commands/atlas.md`:

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
cd /Users/trp/projects/agenticgeek
git add commands/atlas.md
git commit -m "feat: add /atlas slash command"
```

---

### Task 9: Project template

**Files:**
- Create: `templates/CLAUDE.md`

- [ ] **Step 1: Write templates/CLAUDE.md**

Create `templates/CLAUDE.md`:

```markdown
# Agent Instructions

This project uses agenticgeek — a multi-agent toolkit for Claude Code.

## Available Agents

| Agent | Role | How to invoke |
|-------|------|--------------|
| atlas-orch | Orchestrator | `/atlas <task>` (skill, runs in main context) |
| stark-dev | Developer | Spawned by atlas |
| oracle-qa | QA | Spawned by atlas |
| reed-research | Researcher | Spawned by atlas |

## How to use

For any non-trivial task:

```
/atlas <describe what you want to build>
```

Atlas handles: memory prime → context gather → research → brainstorm → plan → implement → test → commit → document.

**Do not** spawn stark, oracle, or reed directly — they are designed to receive structured inputs from atlas.

## Project Notes

[Add project-specific context here: tech stack, key files, env setup, etc.]
```

- [ ] **Step 2: Commit**

```bash
cd /Users/trp/projects/agenticgeek
git add templates/CLAUDE.md
git commit -m "feat: add CLAUDE.md project template"
```

---

### Task 10: install.sh

**Files:**
- Create: `install.sh`

- [ ] **Step 1: Write install.sh**

Create `install.sh`:

```bash
#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR=""
GLOBAL=false

usage() {
  echo "Usage: $0 [--target <path>] [--global]"
  echo ""
  echo "  --target <path>   Install skills to <path> (default: ~/projects/.claude)"
  echo "  --global          Install to ~/.claude instead"
  echo ""
  echo "Examples:"
  echo "  $0                          # installs to ~/projects/.claude"
  echo "  $0 --target ~/myproject     # installs to ~/myproject/.claude"
  echo "  $0 --global                 # installs to ~/.claude"
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target) TARGET_DIR="$2"; shift 2 ;;
    --global) GLOBAL=true; shift ;;
    -h|--help) usage ;;
    *) echo "Unknown option: $1"; usage ;;
  esac
done

if [[ "$GLOBAL" == true ]]; then
  SKILLS_TARGET="$HOME/.claude/skills"
  SETTINGS_TARGET="$HOME/.claude/settings.json"
elif [[ -n "$TARGET_DIR" ]]; then
  SKILLS_TARGET="$TARGET_DIR/.claude/skills"
  SETTINGS_TARGET="$TARGET_DIR/.claude/settings.json"
else
  SKILLS_TARGET="$HOME/projects/.claude/skills"
  SETTINGS_TARGET="$HOME/projects/.claude/settings.json"
fi

HOOKS_TARGET="$HOME/.claude/hooks"
GLOBAL_SETTINGS="$HOME/.claude/settings.json"

echo "agenticgeek installer"
echo "====================="
echo "Skills    → $SKILLS_TARGET"
echo "Settings  → $SETTINGS_TARGET"
echo "Hooks     → $HOOKS_TARGET"
echo ""

# Require node for JSON merging
if ! command -v node &>/dev/null; then
  echo "Error: node is required for JSON merging. Install Node.js and retry."
  exit 1
fi

# ── 1. Skills ──────────────────────────────────────────────────────────────
echo "Installing skills..."
mkdir -p "$SKILLS_TARGET"

for skill_dir in "$SCRIPT_DIR/.claude/skills"/*/; do
  [[ -d "$skill_dir" ]] || continue
  skill_name=$(basename "$skill_dir")
  dest="$SKILLS_TARGET/$skill_name"
  mkdir -p "$dest"
  cp -r "$skill_dir"* "$dest/" 2>/dev/null || true
  echo "  ✓ skill: $skill_name"
done

# ── 2. Agent types → target settings.json ─────────────────────────────────
echo "Registering agent types..."
mkdir -p "$(dirname "$SETTINGS_TARGET")"
[[ -f "$SETTINGS_TARGET" ]] || echo '{}' > "$SETTINGS_TARGET"

for agent_def in "$SCRIPT_DIR/.claude/skills"/*/agent-def.json; do
  [[ -f "$agent_def" ]] || continue
  node - "$SETTINGS_TARGET" "$agent_def" <<'NODEEOF'
const fs = require('fs');
const [,, settingsPath, defPath] = process.argv;
const settings = JSON.parse(fs.readFileSync(settingsPath, 'utf8'));
const def = JSON.parse(fs.readFileSync(defPath, 'utf8'));
if (!settings.agents) settings.agents = [];
const idx = settings.agents.findIndex(a => a.name === def.name);
if (idx >= 0) settings.agents[idx] = def;
else settings.agents.push(def);
fs.writeFileSync(settingsPath, JSON.stringify(settings, null, 2) + '\n');
console.log('  ✓ agent: ' + def.name);
NODEEOF
done

# ── 3. Hooks ───────────────────────────────────────────────────────────────
echo "Installing hooks..."
mkdir -p "$HOOKS_TARGET"

for hook in "$SCRIPT_DIR/hooks"/*.sh; do
  [[ -f "$hook" ]] || continue
  hook_name="agenticgeek-$(basename "$hook")"
  cp "$hook" "$HOOKS_TARGET/$hook_name"
  chmod +x "$HOOKS_TARGET/$hook_name"
  echo "  ✓ hook: $hook_name"
done

# ── 4. Register hooks in ~/.claude/settings.json ───────────────────────────
echo "Registering hooks..."
[[ -f "$GLOBAL_SETTINGS" ]] || echo '{}' > "$GLOBAL_SETTINGS"

node - "$GLOBAL_SETTINGS" "$HOOKS_TARGET" <<'NODEEOF'
const fs = require('fs');
const [,, settingsPath, hooksDir] = process.argv;
const settings = JSON.parse(fs.readFileSync(settingsPath, 'utf8'));
if (!settings.hooks) settings.hooks = {};

const eventMap = {
  SessionStart: 'agenticgeek-sessionstart.sh',
  PreToolUse:   'agenticgeek-pretooluse.sh',
  PostToolUse:  'agenticgeek-posttooluse.sh',
};

for (const [event, hookFile] of Object.entries(eventMap)) {
  const hookPath = `${hooksDir}/${hookFile}`;
  if (!fs.existsSync(hookPath)) continue;
  if (!settings.hooks[event]) settings.hooks[event] = [];

  // Check if already registered
  const alreadyRegistered = settings.hooks[event].some(entry => {
    if (!entry.hooks) return false;
    return entry.hooks.some(h => h.command && h.command.includes('agenticgeek'));
  });

  if (!alreadyRegistered) {
    settings.hooks[event].push({
      hooks: [{ type: 'command', command: `bash "${hookPath}"`, timeout: 5000 }]
    });
    console.log(`  ✓ hook registered: ${event}`);
  } else {
    console.log(`  – hook already registered: ${event}`);
  }
}

fs.writeFileSync(settingsPath, JSON.stringify(settings, null, 2) + '\n');
NODEEOF

echo ""
echo "Done. Agents installed:"
for agent_def in "$SCRIPT_DIR/.claude/skills"/*/agent-def.json; do
  [[ -f "$agent_def" ]] || continue
  node -e "
    const d = JSON.parse(require('fs').readFileSync('$agent_def','utf8'));
    console.log('  • ' + d.name + ' — ' + d.description);
  "
done
echo ""
echo "Atlas skill available via /atlas"
echo "Restart Claude Code to load agent types and hooks."
```

- [ ] **Step 2: Make executable**

```bash
chmod +x /Users/trp/projects/agenticgeek/install.sh
```

- [ ] **Step 3: Dry-run verify (install to a temp dir)**

```bash
mkdir -p /tmp/agenticgeek-test/.claude
bash /Users/trp/projects/agenticgeek/install.sh --target /tmp/agenticgeek-test 2>&1
```

Expected output contains:
```
✓ skill: atlas-orch
✓ skill: stark-dev
✓ skill: oracle-qa
✓ skill: reed-research
✓ agent: stark-dev
✓ agent: oracle-qa
✓ agent: reed-research
✓ hook: agenticgeek-sessionstart.sh
```

- [ ] **Step 4: Verify target settings.json has all three agents**

```bash
node -e "
  const s = JSON.parse(require('fs').readFileSync('/tmp/agenticgeek-test/.claude/settings.json','utf8'));
  console.log('agents:', s.agents.map(a=>a.name));
"
```

Expected: `agents: [ 'stark-dev', 'oracle-qa', 'reed-research' ]`

- [ ] **Step 5: Verify idempotent (run again, no duplicates)**

```bash
bash /Users/trp/projects/agenticgeek/install.sh --target /tmp/agenticgeek-test 2>&1
node -e "
  const s = JSON.parse(require('fs').readFileSync('/tmp/agenticgeek-test/.claude/settings.json','utf8'));
  console.log('agent count:', s.agents.length);
"
```

Expected: `agent count: 3` (same as before, not 6)

- [ ] **Step 6: Commit**

```bash
cd /Users/trp/projects/agenticgeek
git add install.sh
git commit -m "feat: add idempotent install.sh"
```

---

### Task 11: README.md

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README.md**

Create `README.md`:

```markdown
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

Idempotent — safe to re-run.

**Requires:** Node.js (for JSON merging), Bash

## After install

1. Restart Claude Code
2. Add `templates/CLAUDE.md` content to your project's `CLAUDE.md`
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
└── reed-research/SKILL.md        researcher agent
    reed-research/agent-def.json  tool restrictions
hooks/
├── sessionstart.sh
├── pretooluse.sh
└── posttooluse.sh
commands/atlas.md                 /atlas slash command
templates/CLAUDE.md               starter project memory
install.sh
```
```

- [ ] **Step 2: Commit**

```bash
cd /Users/trp/projects/agenticgeek
git add README.md
git commit -m "docs: add README"
```

---

### Task 12: End-to-end smoke test

**Files:** none (verification only)

- [ ] **Step 1: Verify all required files exist**

```bash
for f in \
  .claude/skills/atlas-orch/SKILL.md \
  .claude/skills/stark-dev/SKILL.md \
  .claude/skills/stark-dev/agent-def.json \
  .claude/skills/oracle-qa/SKILL.md \
  .claude/skills/oracle-qa/agent-def.json \
  .claude/skills/reed-research/SKILL.md \
  .claude/skills/reed-research/agent-def.json \
  .claude/settings.json \
  hooks/sessionstart.sh \
  hooks/pretooluse.sh \
  hooks/posttooluse.sh \
  commands/atlas.md \
  templates/CLAUDE.md \
  install.sh \
  README.md; do
  [[ -f "/Users/trp/projects/agenticgeek/$f" ]] && echo "✓ $f" || echo "✗ MISSING: $f"
done
```

Expected: all lines show `✓`

- [ ] **Step 2: All JSON files valid**

```bash
for f in \
  /Users/trp/projects/agenticgeek/.claude/settings.json \
  /Users/trp/projects/agenticgeek/.claude/skills/stark-dev/agent-def.json \
  /Users/trp/projects/agenticgeek/.claude/skills/oracle-qa/agent-def.json \
  /Users/trp/projects/agenticgeek/.claude/skills/reed-research/agent-def.json; do
  node -e "JSON.parse(require('fs').readFileSync('$f','utf8')); console.log('✓ $f')" 2>&1
done
```

Expected: all `✓`

- [ ] **Step 3: All hooks produce valid JSON**

```bash
for h in sessionstart pretooluse posttooluse; do
  output=$(bash /Users/trp/projects/agenticgeek/hooks/${h}.sh)
  node -e "JSON.parse('$output'); console.log('✓ hooks/${h}.sh')"
done
```

Expected: all `✓`

- [ ] **Step 4: install.sh idempotent on fresh test target**

```bash
rm -rf /tmp/agenticgeek-test2
mkdir -p /tmp/agenticgeek-test2
bash /Users/trp/projects/agenticgeek/install.sh --target /tmp/agenticgeek-test2
bash /Users/trp/projects/agenticgeek/install.sh --target /tmp/agenticgeek-test2
node -e "
  const s = JSON.parse(require('fs').readFileSync('/tmp/agenticgeek-test2/.claude/settings.json','utf8'));
  const count = s.agents.length;
  console.log(count === 3 ? '✓ idempotent: ' + count + ' agents' : '✗ FAIL: ' + count + ' agents (expected 3)');
"
```

Expected: `✓ idempotent: 3 agents`

- [ ] **Step 5: Final commit**

```bash
cd /Users/trp/projects/agenticgeek
git log --oneline
```

Expected: 9–10 commits showing the full build history.
