#!/bin/bash
# install.sh — set up trading-morning-levels on a new machine
# Run once after cloning: bash install.sh

set -e

SKILL_DIR="$HOME/.claude/skills/trading-morning-levels"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== trading-morning-levels installer ==="
echo "Script dir: $SCRIPT_DIR"
echo "Skill dir:  $SKILL_DIR"
echo ""

# ── 1. Copy scripts to skill dir ──────────────────────────────────────────────
echo "[1] Installing skill files..."
mkdir -p "$SKILL_DIR"
for f in run_levels.py analyze_levels.py draw_levels.py screenshot_levels.py \
          morning_levels.sh SKILL.md com.trading.morninglevels.plist; do
    cp "$SCRIPT_DIR/$f" "$SKILL_DIR/$f"
done
chmod +x "$SKILL_DIR/morning_levels.sh"
echo "    Done."

# ── 2. Create .env if missing ─────────────────────────────────────────────────
echo "[2] Checking secrets..."
LOCAL_ENV="$HOME/.trading-morning-levels.env"
if [ ! -f "$LOCAL_ENV" ]; then
    echo "    Creating $LOCAL_ENV — fill in your webhook URL"
    cat > "$LOCAL_ENV" <<'EOF'
DISCORD_LEVELS_WEBHOOK=
EOF
    echo "    ⚠ Edit $LOCAL_ENV and add DISCORD_LEVELS_WEBHOOK=<url>"
else
    echo "    $LOCAL_ENV already exists."
fi

# ── 3. Generate plist with correct HOME ───────────────────────────────────────
echo "[3] Installing launchd plist..."
mkdir -p "$LAUNCH_AGENTS"
PLIST="$LAUNCH_AGENTS/com.trading.morninglevels.plist"

# Read webhook from local env
WEBHOOK=$(grep DISCORD_LEVELS_WEBHOOK "$LOCAL_ENV" 2>/dev/null | cut -d= -f2 || echo "")

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.trading.morninglevels</string>

    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$SKILL_DIR/morning_levels.sh</string>
    </array>

    <!-- Run Mon–Fri at 8:30 AM local time -->
    <key>StartCalendarInterval</key>
    <array>
        <dict><key>Weekday</key><integer>1</integer><key>Hour</key><integer>8</integer><key>Minute</key><integer>30</integer></dict>
        <dict><key>Weekday</key><integer>2</integer><key>Hour</key><integer>8</integer><key>Minute</key><integer>30</integer></dict>
        <dict><key>Weekday</key><integer>3</integer><key>Hour</key><integer>8</integer><key>Minute</key><integer>30</integer></dict>
        <dict><key>Weekday</key><integer>4</integer><key>Hour</key><integer>8</integer><key>Minute</key><integer>30</integer></dict>
        <dict><key>Weekday</key><integer>5</integer><key>Hour</key><integer>8</integer><key>Minute</key><integer>30</integer></dict>
    </array>

    <key>RunAtLoad</key>
    <false/>

    <key>StandardOutPath</key>
    <string>$SKILL_DIR/morning_levels.log</string>

    <key>StandardErrorPath</key>
    <string>$SKILL_DIR/morning_levels.log</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
        <key>HOME</key>
        <string>$HOME</string>
        <key>DISCORD_LEVELS_WEBHOOK</key>
        <string>$WEBHOOK</string>
    </dict>
</dict>
</plist>
EOF

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "    Plist installed and loaded."

# ── 4. Check deps ─────────────────────────────────────────────────────────────
echo "[4] Checking Python deps..."
python3 -c "import mplfinance, pandas, matplotlib" 2>/dev/null && echo "    OK" || \
    echo "    ⚠ Run: pip3 install mplfinance pandas matplotlib"

echo "[5] Checking tradingview-mcp..."
[ -f "$HOME/tradingview-mcp/src/cli/index.js" ] && echo "    OK" || \
    echo "    ⚠ Clone tradingview-mcp to ~/tradingview-mcp/"

echo ""
echo "=== Done ==="
echo "Start TradingView with: /Applications/TradingView.app/Contents/MacOS/TradingView --remote-debugging-port=9222 &"
