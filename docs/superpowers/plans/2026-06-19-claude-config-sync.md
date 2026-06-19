# Claude Config Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `config-sync/` toolkit to the `agenticgeek` repo that backs up and restores the full personal Claude Code config (skills, agents, hooks, settings, memory, MCP, plugins) to any machine, portable across usernames, idempotent both ways.

**Architecture:** One bash entrypoint `config-sync/sync.sh` with `push` (machine→repo) and `pull` (repo→machine) subcommands, plus three small node helpers in `config-sync/lib/` for JSON-aware work (clean settings, merge settings, generate plugin list). Paths are tokenized to `__HOME__` in the repo and rendered to the live `$HOME` on pull. All operations are diff-based: missing→add, changed→update, identical→skip, local-only→never prune. The existing `install.sh` is untouched.

**Tech Stack:** bash, rsync (`-rci`, no `--delete` = idempotent + never prunes), node (JSON merge/clean — node already required by `install.sh`), git.

**Spec:** `docs/superpowers/specs/2026-06-19-claude-config-sync-design.md`

**Testing model:** These are infra shell scripts, not unit-testable functions. Each task verifies by *running* the script — `push` writes only into the git-tracked repo (safe; `git checkout` undoes), `pull` is tested against a sandbox `$HOME` via the `SYNC_HOME` / `CLAUDE_HOME` env overrides so the real `~/.claude` is never touched during tests.

---

### Task 1: Scaffold config-sync skeleton

**Files:**
- Create: `config-sync/.gitignore`
- Create: `config-sync/sync.sh`

- [ ] **Step 1: Create `config-sync/.gitignore`**

```gitignore
# Secrets — never commit
*.env
.env
token.json
credentials.json
*client_secret*.json
*.pem
*.key

# Local scratch
.tmp/
tmp/
```

- [ ] **Step 2: Create `config-sync/sync.sh` skeleton (arg parse + helpers, no push/pull bodies yet)**

```bash
#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_CLAUDE="$SCRIPT_DIR/claude"            # captured config lives here
LIB="$SCRIPT_DIR/lib"
SRC_CLAUDE="${CLAUDE_HOME:-$HOME/.claude}"  # live config (override in tests)
LIVE_HOME="${LIVE_HOME_OVERRIDE:-$HOME}"    # home to tokenize on push
TARGET_HOME="${SYNC_HOME:-$HOME}"           # home to render on pull
TOKEN="__HOME__"

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
ADDED=0; UPDATED=0; UNCHANGED=0; CHANGED=0

usage() { echo "Usage: $0 {push|pull}"; echo "  push  capture ~/.claude -> repo"; echo "  pull  restore repo -> ~/.claude"; exit 1; }

mem_dir_for_home() { echo "$1/projects" | sed 's#/#-#g'; }   # /Users/x/projects -> -Users-x-projects
tokenize_file()    { sed "s#$LIVE_HOME#$TOKEN#g" "$1"; }
render_file()      { sed "s#$TOKEN#$TARGET_HOME#g" "$1"; }

copy_if_changed() {
  local src="$1" dst="$2"
  mkdir -p "$(dirname "$dst")"
  if [ ! -f "$dst" ]; then cp "$src" "$dst"; ADDED=$((ADDED+1)); echo "  + $dst"
  elif ! cmp -s "$src" "$dst"; then cp "$src" "$dst"; UPDATED=$((UPDATED+1)); echo "  ~ $dst"
  else UNCHANGED=$((UNCHANGED+1)); fi
}

sync_dir_verbatim() {  # idempotent, checksum-based, NEVER deletes (no --delete)
  local src="$1" dst="$2" label="$3"
  [ -d "$src" ] || { echo "  $label: (no source, skip)"; return; }
  mkdir -p "$dst"
  local out; out="$(rsync -rci "$src/" "$dst/")"
  local n; n="$(printf '%s' "$out" | grep -c . || true)"
  if [ "$n" -eq 0 ]; then echo "  $label: unchanged"
  else echo "  $label: $n changed"; printf '%s\n' "$out" | sed 's/^/      /'; CHANGED=$((CHANGED+n)); fi
}

secret_scan() {  # abort if any staged file looks like it holds a secret
  local hits
  hits="$(grep -rEI \
    -e 'sk-[A-Za-z0-9]{20,}' \
    -e 'AIza[0-9A-Za-z_-]{30,}' \
    -e 'ghp_[A-Za-z0-9]{30,}' \
    -e 'xoxb-[A-Za-z0-9-]+' \
    -e '-----BEGIN [A-Z ]*PRIVATE KEY-----' \
    -e '"(api[_-]?key|secret|password|access[_-]?token)"[[:space:]]*:[[:space:]]*"[A-Za-z0-9/_+.=-]{16,}"' \
    "$@" 2>/dev/null || true)"
  if [ -n "$hits" ]; then
    echo "ABORT: potential secret(s) detected — nothing copied to repo:" >&2
    printf '%s\n' "$hits" | sed 's/^/  /' >&2
    exit 1
  fi
}

report() { echo ""; echo "Summary: added=$ADDED updated=$UPDATED unchanged=$UNCHANGED dir-changes=$CHANGED"; }

cmd_push() { echo "push not implemented yet"; }
cmd_pull() { echo "pull not implemented yet"; }

case "${1:-}" in
  push) cmd_push ;;
  pull) cmd_pull ;;
  *) usage ;;
esac
```

- [ ] **Step 3: Make executable and verify usage**

Run: `chmod +x config-sync/sync.sh && config-sync/sync.sh`
Expected: prints `Usage: ... {push|pull}` and exits non-zero.

Run: `config-sync/sync.sh push`
Expected: prints `push not implemented yet`.

- [ ] **Step 4: Commit**

```bash
git add config-sync/.gitignore config-sync/sync.sh
git commit -m "feat(config-sync): scaffold sync.sh skeleton + gitignore

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Node helpers — clean settings + generate plugin list

**Files:**
- Create: `config-sync/lib/clean-settings.js`
- Create: `config-sync/lib/gen-plugins.js`

- [ ] **Step 1: Create `config-sync/lib/clean-settings.js`** — recursively strip any string array entry containing the dead `astha.tarun@gmail.com` account, output cleaned JSON to stdout

```javascript
// Usage: node clean-settings.js <settings.json>  -> cleaned JSON on stdout
const fs = require('fs');
const [, , path] = process.argv;
const DEAD = 'astha.tarun@gmail.com';

function clean(node) {
  if (Array.isArray(node)) {
    return node
      .filter(v => !(typeof v === 'string' && v.includes(DEAD)))
      .map(clean);
  }
  if (node && typeof node === 'object') {
    const out = {};
    for (const [k, v] of Object.entries(node)) out[k] = clean(v);
    return out;
  }
  return node;
}

const data = JSON.parse(fs.readFileSync(path, 'utf8'));
process.stdout.write(JSON.stringify(clean(data), null, 2) + '\n');
```

- [ ] **Step 2: Create `config-sync/lib/gen-plugins.js`** — emit reinstall commands from the live plugin/marketplace json

```javascript
// Usage: node gen-plugins.js <~/.claude dir>  -> plugins.txt body on stdout
const fs = require('fs');
const path = require('path');
const [, , claudeDir] = process.argv;

const mk = JSON.parse(fs.readFileSync(path.join(claudeDir, 'plugins/known_marketplaces.json'), 'utf8'));
const inst = JSON.parse(fs.readFileSync(path.join(claudeDir, 'plugins/installed_plugins.json'), 'utf8'));

const out = ['# Reinstall after `pull`. Lines are idempotent — Claude skips already-installed.', '', '# Marketplaces'];
for (const [name, m] of Object.entries(mk)) {
  const s = m.source || {};
  const ref = s.repo || s.url || name;
  out.push(`claude plugin marketplace add ${ref}`);
}
out.push('', '# Plugins');
for (const key of Object.keys(inst.plugins || {})) {
  out.push(`claude plugin install ${key}`);
}
process.stdout.write(out.join('\n') + '\n');
```

- [ ] **Step 3: Verify clean-settings strips astha + leaves valid JSON**

Run: `node config-sync/lib/clean-settings.js ~/.claude/settings.json | grep -c astha.tarun`
Expected: `0`

Run: `node config-sync/lib/clean-settings.js ~/.claude/settings.json | node -e 'JSON.parse(require("fs").readFileSync(0));console.log("valid json")'`
Expected: `valid json`

- [ ] **Step 4: Verify gen-plugins output**

Run: `node config-sync/lib/gen-plugins.js ~/.claude`
Expected: lists 4 `marketplace add` lines (caveman, claude-plugins-official, claude-mem, context-mode sources) and 9 `plugin install` lines (caveman@caveman … discord@claude-plugins-official).

- [ ] **Step 5: Commit**

```bash
git add config-sync/lib/clean-settings.js config-sync/lib/gen-plugins.js
git commit -m "feat(config-sync): node helpers to clean settings + list plugins

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Implement `push` (machine → repo)

**Files:**
- Modify: `config-sync/sync.sh` (replace `cmd_push` body)

- [ ] **Step 1: Replace the `cmd_push` stub with the full implementation**

```bash
cmd_push() {
  echo "PUSH  $SRC_CLAUDE -> $REPO_CLAUDE"
  local memsrc="$SRC_CLAUDE/projects/$(mem_dir_for_home "$LIVE_HOME")/memory"

  # 0. Secret scan sources FIRST — abort before writing anything to the repo
  secret_scan \
    "$SRC_CLAUDE/skills" "$SRC_CLAUDE/agents" "$SRC_CLAUDE/hooks" \
    "$SRC_CLAUDE/settings.json" "$SRC_CLAUDE/.mcp.json" "$memsrc"

  # 1. skills + agents — verbatim, idempotent, no prune
  sync_dir_verbatim "$SRC_CLAUDE/skills" "$REPO_CLAUDE/skills" "skills"
  sync_dir_verbatim "$SRC_CLAUDE/agents" "$REPO_CLAUDE/agents" "agents"

  # 2. hooks — tokenize each file, diff-copy
  mkdir -p "$REPO_CLAUDE/hooks"
  for f in "$SRC_CLAUDE/hooks"/*; do
    [ -f "$f" ] || continue
    tokenize_file "$f" > "$TMP/$(basename "$f")"
    copy_if_changed "$TMP/$(basename "$f")" "$REPO_CLAUDE/hooks/$(basename "$f")"
  done

  # 3. settings.json — astha purge (node) then tokenize (sed), diff-copy
  node "$LIB/clean-settings.js" "$SRC_CLAUDE/settings.json" | sed "s#$LIVE_HOME#$TOKEN#g" > "$TMP/settings.json"
  copy_if_changed "$TMP/settings.json" "$REPO_CLAUDE/settings.json"

  # 4. .mcp.json — tokenize, diff-copy
  tokenize_file "$SRC_CLAUDE/.mcp.json" > "$TMP/.mcp.json"
  copy_if_changed "$TMP/.mcp.json" "$REPO_CLAUDE/.mcp.json"

  # 5. memory — verbatim
  sync_dir_verbatim "$memsrc" "$REPO_CLAUDE/memory" "memory"

  # 6. plugins.txt — regenerate from live state
  node "$LIB/gen-plugins.js" "$SRC_CLAUDE" > "$TMP/plugins.txt"
  copy_if_changed "$TMP/plugins.txt" "$SCRIPT_DIR/plugins.txt"

  report
  echo "Review 'git diff', then commit + push."
}
```

- [ ] **Step 2: Run push for real (writes only into git-tracked repo)**

Run: `config-sync/sync.sh push`
Expected: prints per-section changes and a `Summary:` line; exits 0 (no secret abort).

- [ ] **Step 3: Verify zero leaked literals in captured files**

Run: `grep -rl "$HOME" config-sync/claude/ 2>/dev/null | grep -v memory || echo "NONE"`
Expected: `NONE` — no live home path literals in settings/mcp/hooks (memory files may legitimately reference paths and are not tokenized; that is acceptable).

Run: `grep -rc astha.tarun config-sync/claude/settings.json`
Expected: `0`

- [ ] **Step 4: Verify idempotency — second push is a no-op**

Run: `config-sync/sync.sh push`
Expected: every section `unchanged`; `Summary: added=0 updated=0 ... dir-changes=0`.

- [ ] **Step 5: Commit**

```bash
git add config-sync/sync.sh config-sync/claude config-sync/plugins.txt
git commit -m "feat(config-sync): implement push (machine -> repo)

Captures skills/agents/hooks/settings/mcp/memory with path tokenizing,
astha.tarun purge, secret-scan abort, and plugins.txt regen. Idempotent.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Implement `pull` (repo → machine) + JSON merge

**Files:**
- Create: `config-sync/lib/merge-json.js`
- Modify: `config-sync/sync.sh` (replace `cmd_pull` body)

- [ ] **Step 1: Create `config-sync/lib/merge-json.js`** — add-missing deep merge; arrays unioned by identity; existing scalars preserved (never clobber)

```javascript
// Usage: node merge-json.js <target.json> <source.json>
// Merges source INTO target: add missing keys, union arrays by identity,
// recurse objects, keep existing scalars. Idempotent.
const fs = require('fs');
const [, , targetPath, sourcePath] = process.argv;

const source = JSON.parse(fs.readFileSync(sourcePath, 'utf8'));
const target = fs.existsSync(targetPath)
  ? JSON.parse(fs.readFileSync(targetPath, 'utf8'))
  : {};

function ident(v) {
  if (v && typeof v === 'object' && typeof v.name === 'string') return 'name:' + v.name;
  return JSON.stringify(v);
}

function mergeArray(tArr, sArr) {
  const seen = new Set(tArr.map(ident));
  for (const item of sArr) {
    if (!seen.has(ident(item))) { tArr.push(item); seen.add(ident(item)); }
  }
  return tArr;
}

function merge(t, s) {
  for (const [k, sv] of Object.entries(s)) {
    if (!(k in t)) { t[k] = sv; continue; }
    const tv = t[k];
    if (Array.isArray(tv) && Array.isArray(sv)) mergeArray(tv, sv);
    else if (tv && sv && typeof tv === 'object' && typeof sv === 'object'
             && !Array.isArray(tv) && !Array.isArray(sv)) merge(tv, sv);
    // else: scalar/type-mismatch -> keep existing target value
  }
  return t;
}

fs.mkdirSync(require('path').dirname(targetPath), { recursive: true });
fs.writeFileSync(targetPath, JSON.stringify(merge(target, source), null, 2) + '\n');
console.log('  merged -> ' + targetPath);
```

- [ ] **Step 2: Replace the `cmd_pull` stub with the full implementation**

```bash
cmd_pull() {
  local tgt="$TARGET_HOME/.claude"
  echo "PULL  $REPO_CLAUDE -> $tgt"

  # 1. skills + agents — verbatim, no prune
  sync_dir_verbatim "$REPO_CLAUDE/skills" "$tgt/skills" "skills"
  sync_dir_verbatim "$REPO_CLAUDE/agents" "$tgt/agents" "agents"

  # 2. hooks — render tokens, diff-copy, mark executable
  mkdir -p "$tgt/hooks"
  for f in "$REPO_CLAUDE/hooks"/*; do
    [ -f "$f" ] || continue
    render_file "$f" > "$TMP/$(basename "$f")"
    copy_if_changed "$TMP/$(basename "$f")" "$tgt/hooks/$(basename "$f")"
    chmod +x "$tgt/hooks/$(basename "$f")" 2>/dev/null || true
  done

  # 3. settings.json + .mcp.json — render then MERGE (never clobber)
  render_file "$REPO_CLAUDE/settings.json" > "$TMP/settings.json"
  node "$LIB/merge-json.js" "$tgt/settings.json" "$TMP/settings.json"
  render_file "$REPO_CLAUDE/.mcp.json" > "$TMP/.mcp.json"
  node "$LIB/merge-json.js" "$tgt/.mcp.json" "$TMP/.mcp.json"

  # 4. memory — placed under the username-derived path (assumes projects at $HOME/projects)
  local memtgt="$tgt/projects/$(mem_dir_for_home "$TARGET_HOME")/memory"
  sync_dir_verbatim "$REPO_CLAUDE/memory" "$memtgt" "memory"

  report
  echo ""
  echo "Next steps (see config-sync/RESTORE.md):"
  echo "  1. Reinstall plugins:  bash -c 'while read -r l; do [ \"\${l#\\#}\" = \"\$l\" ] && [ -n \"\$l\" ] && eval \"\$l\"; done < config-sync/plugins.txt'"
  echo "  2. ./install.sh --global   (re-merge agenticgeek hooks/agents)"
  echo "  3. git clone github.com/tradesdontlie/tradingview-mcp ~/tradingview-mcp"
  echo "  4. Restart Claude Code"
}
```

- [ ] **Step 3: Test pull into a sandbox HOME (real config untouched)**

Run:
```bash
SB="$(mktemp -d)"
SYNC_HOME="$SB" config-sync/sync.sh pull
echo "--- rendered home check ---"
grep -rl "$SB" "$SB/.claude/settings.json" "$SB/.claude/.mcp.json" && echo "TOKENS RENDERED OK"
echo "--- token leak check ---"
grep -rc "__HOME__" "$SB/.claude/settings.json" || echo "no tokens left (good)"
echo "--- memory placed ---"
ls "$SB/.claude/projects/$(echo "$SB/projects" | sed 's#/#-#g')/memory/" | head
```
Expected: settings/mcp contain the sandbox path (`TOKENS RENDERED OK`), zero `__HOME__` left, memory files listed (incl `MEMORY.md`).

- [ ] **Step 4: Verify pull idempotency — second pull is a no-op**

Run: `SYNC_HOME="$SB" config-sync/sync.sh pull`
Expected: skills/agents/hooks/memory `unchanged`; merge prints `merged` but adds nothing; `Summary: added=0 updated=0 ...`. Clean up: `rm -rf "$SB"`.

- [ ] **Step 5: Commit**

```bash
git add config-sync/lib/merge-json.js config-sync/sync.sh
git commit -m "feat(config-sync): implement pull (repo -> machine) + idempotent JSON merge

Renders __HOME__ to live \$HOME, merges settings/mcp by entry identity
(no clobber), places memory under username-derived path. Sandbox-testable
via SYNC_HOME. Idempotent.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: RESTORE.md

**Files:**
- Create: `config-sync/RESTORE.md`

- [ ] **Step 1: Create `config-sync/RESTORE.md`**

```markdown
# Restore Claude Code config on a new machine

Brings back skills, agents, hooks, settings, memory, MCP, and plugins.
Portable across usernames — paths render to the new machine's `$HOME` automatically.

## Steps

1. **Clone this repo**
   ```bash
   git clone https://github.com/fificlawbot/agenticgeek.git ~/projects/agenticgeek
   cd ~/projects/agenticgeek
   ```

2. **Restore config into `~/.claude`** (idempotent — re-runnable)
   ```bash
   config-sync/sync.sh pull
   ```

3. **Reinstall plugins** (skips any already installed)
   ```bash
   while read -r l; do
     [ -n "$l" ] && [ "${l#\#}" = "$l" ] && eval "$l"
   done < config-sync/plugins.txt
   ```

4. **Re-merge agenticgeek's own toolkit** (idempotent)
   ```bash
   ./install.sh --global
   ```

5. **Clone the external MCP server** (referenced by `.mcp.json`)
   ```bash
   git clone https://github.com/tradesdontlie/tradingview-mcp ~/tradingview-mcp
   ```

6. **Restart Claude Code.**

## Ongoing sync

- After changing skills/hooks/settings on any machine:
  ```bash
  config-sync/sync.sh push   # capture into repo
  git add -A && git commit -m "config: sync" && git push
  ```
- On the other machine:
  ```bash
  git pull && config-sync/sync.sh pull
  ```

## Not included (by design)

- Secrets (`.env`, `token.json`, OAuth json) — gitignored. Copy manually + securely.
- claude-mem observation DB — auto-memory files only.
- Plugin caches — regenerated by reinstall (latest versions).
```

- [ ] **Step 2: Verify the plugin-reinstall loop parses cleanly (dry, no eval)**

Run: `while read -r l; do [ -n "$l" ] && [ "${l#\#}" = "$l" ] && echo "WOULD RUN: $l"; done < config-sync/plugins.txt`
Expected: prints `WOULD RUN: claude plugin marketplace add ...` / `install ...` lines, no comment lines.

- [ ] **Step 3: Commit**

```bash
git add config-sync/RESTORE.md
git commit -m "docs(config-sync): add RESTORE.md new-machine guide

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Capture live config + push agenticgeek to GitHub

**Files:** none (operational)

- [ ] **Step 1: Run a fresh push to capture current live config**

Run: `config-sync/sync.sh push`
Expected: completes; `Summary:` shows whatever changed since Task 3 (likely 0 if nothing edited).

- [ ] **Step 2: Final secret + literal sweep on everything staged**

Run:
```bash
git add -A
git diff --cached --name-only | xargs grep -lI -e 'sk-[A-Za-z0-9]\{20,\}' -e 'AIza' -e 'ghp_' 2>/dev/null || echo "NO SECRETS"
git diff --cached --name-only | grep '^config-sync/claude/' | grep -v memory | xargs grep -l "/Users/$(whoami)" 2>/dev/null || echo "NO HOME LITERALS"
```
Expected: `NO SECRETS` and `NO HOME LITERALS`.

- [ ] **Step 3: Commit the captured config (if Step 1 changed anything) and push the branch incl. the stale ECC commit**

```bash
git commit -m "chore(config-sync): capture current ~/.claude state" || echo "nothing to commit"
git push origin main
```
Expected: push succeeds; `origin/main` now ahead by the new commits + the prior unpushed `2fbc99c` ECC commit.

- [ ] **Step 4: Verify remote is current**

Run: `git rev-list origin/main..HEAD --count`
Expected: `0` (everything pushed).

---

### Task 7: Final round-trip verification + memory note

**Files:**
- Create: `/Users/trp/.claude/projects/-Users-trp-projects/memory/claude_config_sync.md`
- Modify: `/Users/trp/.claude/projects/-Users-trp-projects/memory/MEMORY.md`

- [ ] **Step 1: Full round-trip into a clean sandbox**

Run:
```bash
SB="$(mktemp -d)"
SYNC_HOME="$SB" config-sync/sync.sh pull >/dev/null
test -f "$SB/.claude/settings.json" && echo "settings OK"
test -d "$SB/.claude/skills/hyperframes" && echo "skills OK"
test -f "$SB/.claude/projects/$(echo "$SB/projects" | sed 's#/#-#g')/memory/MEMORY.md" && echo "memory OK"
SYNC_HOME="$SB" config-sync/sync.sh pull | grep -q "added=0 updated=0" && echo "IDEMPOTENT OK"
rm -rf "$SB"
```
Expected: `settings OK`, `skills OK`, `memory OK`, `IDEMPOTENT OK`.

- [ ] **Step 2: Write memory file `claude_config_sync.md`**

```markdown
---
name: claude-config-sync
description: How the full Claude Code config is backed up / restored across machines
metadata:
  type: project
---

Personal `~/.claude` config (skills, agents, hooks, settings, .mcp.json, auto-memory, plugin list) is backed up in the `agenticgeek` repo under `config-sync/`.

- `config-sync/sync.sh push` — capture live `~/.claude` → repo (tokenizes `$HOME`→`__HOME__`, strips dead astha.tarun paths, secret-scan aborts, regens `plugins.txt`).
- `config-sync/sync.sh pull` — restore repo → `~/.claude` (renders `__HOME__`→live `$HOME`, merges settings/mcp by entry identity, never clobbers local).
- Idempotent both ways; never prunes local-only files. New-machine steps in `config-sync/RESTORE.md`.
- NOT included: secrets, claude-mem observation DB (auto-memory only), plugin caches (reinstalled latest). External `~/tradingview-mcp` is its own repo, cloned in RESTORE.

Related: [[hyperframes-setup]]
```

- [ ] **Step 3: Add MEMORY.md index line**

Append under the index list in `MEMORY.md`:
```markdown
- [Claude Config Sync](claude_config_sync.md) — ~/.claude backup/restore via agenticgeek config-sync/, idempotent push/pull
```

- [ ] **Step 4: Done — report to user**

No commit needed for memory files (outside repo). Summarize: config-sync shipped to agenticgeek, pushed to GitHub, round-trip verified idempotent.

---

## Self-Review

**Spec coverage:**
- Idempotency (add/update/skip, no prune) → Tasks 1 (`copy_if_changed`, `sync_dir_verbatim` no `--delete`), 3/4 idempotency steps. ✓
- Path tokenization portable across usernames → `tokenize_file`/`render_file`, Task 4 sandbox test. ✓
- astha.tarun purge → `clean-settings.js` (Task 2), verified Task 3 Step 3. ✓
- Secret guard aborts → `secret_scan` runs first in `cmd_push` (Task 3). ✓
- settings/mcp merge by identity, no clobber → `merge-json.js` (Task 4). ✓
- Auto-memory only, username-derived placement → `mem_dir_for_home`, Tasks 3/4. ✓
- Plugins reinstall, skip installed → `gen-plugins.js` + RESTORE loop (Tasks 2/5). ✓
- tradingview-mcp cloned not bundled → RESTORE Step 5. ✓
- install.sh untouched → no task modifies it. ✓
- Push agenticgeek incl stale commit → Task 6. ✓

**Placeholder scan:** No TBD/TODO; all code blocks complete. ✓

**Type/name consistency:** `cmd_push`/`cmd_pull`, `copy_if_changed`, `sync_dir_verbatim`, `mem_dir_for_home`, `tokenize_file`/`render_file`, `secret_scan`, `merge-json.js`/`clean-settings.js`/`gen-plugins.js` — names consistent across all tasks. Env overrides `CLAUDE_HOME`/`SYNC_HOME`/`LIVE_HOME_OVERRIDE` used consistently. ✓
