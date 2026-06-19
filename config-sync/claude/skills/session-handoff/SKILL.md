---
name: session-handoff
description: Captures current session state and saves it so the next session can resume without re-reading the conversation. Use this whenever the user says things like "save session", "wrap up", "capture state", "summarize for pickup", "I'm done for now", "end of session", "save my place", "let's pick this up later", "create a handoff", or "session summary". Also use proactively when the user asks to start a new conversation and there's meaningful in-progress work. Writes to the memory system AND outputs a paste-ready handoff note. Token-saving first principle: the next session should need zero context re-derivation.
---

# Session Handoff

## Goal
Capture everything needed to resume this session cold — no re-reading conversation, no re-running experiments, no re-deriving decisions. The output has two parts: a memory file update (persistent) and a printed handoff note (paste-ready for next session's first message).

## Step 1 — Extract session state

Scan the full conversation and extract:

- **Completed**: specific actions taken, experiments run, bugs fixed, features added — with concrete results (numbers, filenames, pass/fail)
- **Key findings**: data that cost time to produce (backtest results, benchmark numbers, API responses, config values discovered). Write these out explicitly — they'd cost tokens to re-derive.
- **Decisions made**: anything chosen between alternatives. Capture the decision AND the reason so the next session doesn't re-debate it.
- **Files changed**: exact paths + one-line description of what changed
- **Blockers / known issues**: anything that stopped progress or was flagged but not fixed
- **Next action**: the single most specific next thing to do — actionable without reading the conversation
- **Queue**: everything after that, in priority order

## Step 2 — Update memory

Find the memory directory: `~/.claude/projects/<project-hash>/memory/` where project-hash matches the current working directory. Check `MEMORY.md` for the index.

**If a relevant project memory file exists** (type: project): update it. Replace stale state with current state. Add completed work. Update "Next Work" section.

**If no project memory exists**: create one at `<memory-dir>/<project-name>-state.md` with frontmatter:
```
---
name: <project-name>-state
description: "<project> — active state, completed work, next actions"
metadata:
  type: project
---
```
Then add the new file as a line in `MEMORY.md`: `- [Title](filename.md) — one-line hook`

**Memory file structure** (update or create with this shape):
```markdown
# <Project> State

**Branch/Context:** <current branch or working context>
**Last updated:** <today's date>

## Current State
<1-2 sentences: where we are, what's in progress>

## Completed (most recent first)
- <date>: <what was done> → <result>
- <date>: <what was done> → <result>

## Key Data
<any numbers/findings that would cost tokens to re-derive — test results, benchmark numbers, config values, etc.>

## Files Changed (recent)
- `path/to/file` — what changed

## Known Issues / Decisions
- <decision or known issue with rationale>

## Next Work
1. <specific next action>
2. <after that>
3. <after that>
```

Keep the memory file focused and under 150 lines. Merge, don't duplicate. If there's prior completed work in the file, keep the 3-5 most recent entries and drop older ones.

## Step 3 — Print handoff note

After updating memory, print a compact handoff note the user can paste as the opening message of the next session. It should be fully self-contained — the next Claude should be able to orient and start immediately.

Format:
```
## HANDOFF — [project/task] — [date]

**Context:** [1-2 sentences: project, branch/location, what was being worked on]

**Done this session:**
- [specific action] → [result]
- [specific action] → [result]

**Key data:**
[any numbers, filenames, config values the next session needs without re-running]

**Files changed:**
- `exact/path.py` — what changed (one line)

**Next:** [THE specific next action — enough detail to start without reading anything else]

**Queue:**
1. [second priority]
2. [third priority]
```

Keep total under 400 tokens. Use exact paths, exact numbers — never vague phrases like "improved significantly" or "the strategy file".

## Announce

Start with: "Saving session state..."
End with: "Memory updated. Handoff note above — paste it as your first message in the next session."
