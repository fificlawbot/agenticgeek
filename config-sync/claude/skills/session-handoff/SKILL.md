# session-handoff

Triggered automatically by the Stop hook when a session ends with completed work.
Save current session state so the next session can resume without losing context.

## Steps (execute in order)

### 1. Summarize session
Write a concise summary of what was accomplished this session:
- What task(s) were completed
- Files changed (with paths)
- Decisions made and why
- Any open items or blockers

### 2. Save to claude-mem
```
mcp__plugin_claude-mem_mcp-search__memory_add(
  content: "<session summary>",
  tags: ["session-handoff", "<project-name>", "<date>"]
)
```

### 3. Update docs/index.html (if in a project with one)
If the current project has a `docs/index.html`, append a session entry:
```html
<section>
  <h2>Session handoff — <timestamp></h2>
  <ul>
    <li>Completed: <summary></li>
    <li>Files changed: <list></li>
    <li>Open items: <list or "none"></li>
  </ul>
</section>
```

### 4. Report to user
Output a one-paragraph handoff note:
- What was done
- What's next
- Any important context for the next session

## Constraints
- Keep summary factual and brief — next session reads this cold
- Do NOT include raw file contents in the handoff — just paths and descriptions
- If nothing was accomplished (user just asked questions), skip docs update
