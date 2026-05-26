#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR=""
GLOBAL=false
WITH_ECC=false

usage() {
  echo "Usage: $0 [--target <path>] [--global] [--with-ecc]"
  echo ""
  echo "  --target <path>   Install skills to <path> (default: ~/projects/.claude)"
  echo "  --global          Install to ~/.claude instead"
  echo "  --with-ecc        Also install ECC agents, rules, and skills from github.com/affaan-m/ECC"
  echo ""
  echo "Examples:"
  echo "  $0                          # installs to ~/projects/.claude"
  echo "  $0 --target ~/myproject     # installs to ~/myproject/.claude"
  echo "  $0 --global                 # installs to ~/.claude"
  echo "  $0 --with-ecc               # installs agenticgeek + ECC"
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target) TARGET_DIR="$2"; shift 2 ;;
    --global) GLOBAL=true; shift ;;
    --with-ecc) WITH_ECC=true; shift ;;
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
  Stop:         'agenticgeek-stop.sh',
};

for (const [event, hookFile] of Object.entries(eventMap)) {
  const hookPath = `${hooksDir}/${hookFile}`;
  if (!fs.existsSync(hookPath)) continue;
  if (!settings.hooks[event]) settings.hooks[event] = [];

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

# ── 5. ECC (optional) ─────────────────────────────────────────────────────
if [[ "$WITH_ECC" == true ]]; then
  echo "Installing ECC..."
  ECC_TMP="$(mktemp -d)"
  if ! command -v git &>/dev/null; then
    echo "  ✗ git required for --with-ecc. Skipping ECC install."
  else
    git clone --depth 1 https://github.com/affaan-m/ECC.git "$ECC_TMP/ecc" 2>/dev/null
    ECC_DIR="$ECC_TMP/ecc"

    # agents → ~/.claude/agents/
    mkdir -p "$HOME/.claude/agents"
    cp "$ECC_DIR"/agents/*.md "$HOME/.claude/agents/" 2>/dev/null && echo "  ✓ ECC agents installed"

    # rules: common + python → ~/.claude/rules/ecc/
    mkdir -p "$HOME/.claude/rules/ecc"
    cp -r "$ECC_DIR/rules/common" "$HOME/.claude/rules/ecc/" 2>/dev/null && echo "  ✓ ECC rules/common installed"
    [[ -d "$ECC_DIR/rules/python" ]] && cp -r "$ECC_DIR/rules/python" "$HOME/.claude/rules/ecc/" && echo "  ✓ ECC rules/python installed"

    # core skills → ~/.claude/skills/ecc/
    mkdir -p "$HOME/.claude/skills/ecc"
    cp -r "$ECC_DIR/.agents/skills/"* "$HOME/.claude/skills/ecc/" 2>/dev/null || true
    [[ -d "$ECC_DIR/skills/search-first" ]] && cp -r "$ECC_DIR/skills/search-first" "$HOME/.claude/skills/ecc/" && echo "  ✓ ECC skills installed"

    rm -rf "$ECC_TMP"
    echo "  ✓ ECC install complete"
  fi
fi

echo ""
echo "Done. Agents installed:"
for agent_def in "$SCRIPT_DIR/.claude/skills"/*/agent-def.json; do
  [[ -f "$agent_def" ]] || continue
  node -e "
    const d = JSON.parse(require('fs').readFileSync('$agent_def', 'utf8'));
    console.log('  • ' + d.name + ' — ' + d.description);
  "
done
echo ""
echo "Atlas skill available via /atlas"
[[ "$WITH_ECC" == true ]] && echo "ECC agents, rules, and skills installed to ~/.claude/"
echo "Restart Claude Code to load agent types and hooks."
