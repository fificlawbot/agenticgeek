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
  local out; out="$(rsync -rcti "$src/" "$dst/")"
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
  if [ -f "$SRC_CLAUDE/settings.json" ]; then
    node "$LIB/clean-settings.js" "$SRC_CLAUDE/settings.json" | sed "s#$LIVE_HOME#$TOKEN#g" > "$TMP/settings.json"
    copy_if_changed "$TMP/settings.json" "$REPO_CLAUDE/settings.json"
  else echo "  settings.json: (no source, skip)"; fi

  # 4. .mcp.json — tokenize, diff-copy
  if [ -f "$SRC_CLAUDE/.mcp.json" ]; then
    tokenize_file "$SRC_CLAUDE/.mcp.json" > "$TMP/.mcp.json"
    copy_if_changed "$TMP/.mcp.json" "$REPO_CLAUDE/.mcp.json"
  else echo "  .mcp.json: (no source, skip)"; fi

  # 5. memory — verbatim
  sync_dir_verbatim "$memsrc" "$REPO_CLAUDE/memory" "memory"

  # 6. plugins.txt — regenerate from live state (skip if plugin metadata absent)
  if [ -f "$SRC_CLAUDE/plugins/known_marketplaces.json" ] && [ -f "$SRC_CLAUDE/plugins/installed_plugins.json" ]; then
    node "$LIB/gen-plugins.js" "$SRC_CLAUDE" > "$TMP/plugins.txt"
    copy_if_changed "$TMP/plugins.txt" "$SCRIPT_DIR/plugins.txt"
  else echo "  plugins.txt: (no plugin metadata, skip)"; fi

  report
  echo "Review 'git diff', then commit + push."
}
cmd_pull() { echo "pull not implemented yet"; }

case "${1:-}" in
  push) cmd_push ;;
  pull) cmd_pull ;;
  *) usage ;;
esac
