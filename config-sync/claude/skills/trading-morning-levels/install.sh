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

# ── 1. Symlink skill dir → cloned repo ────────────────────────────────────────
# Single source of truth: edits in the repo take effect immediately, no
# copy step. Runtime artifacts (logs, levels_*.json, bars_*.json) get written
# into the repo and are .gitignored.
echo "[1] Linking skill dir → repo..."
mkdir -p "$(dirname "$SKILL_DIR")"
if [ -L "$SKILL_DIR" ]; then
    # Existing symlink — refresh target (handles repo move / renamed clone path)
    ln -sfn "$SCRIPT_DIR" "$SKILL_DIR"
    echo "    Updated symlink: $SKILL_DIR → $SCRIPT_DIR"
elif [ -d "$SKILL_DIR" ]; then
    # Real directory from a prior install — refuse to clobber, ask user to migrate
    echo "    ERROR: $SKILL_DIR is a real directory, not a symlink."
    echo "    Move any runtime artifacts (morning_levels.log, levels_*.json,"
    echo "    bars_*.json) into $SCRIPT_DIR, then 'rm -rf $SKILL_DIR' and re-run."
    exit 1
else
    ln -s "$SCRIPT_DIR" "$SKILL_DIR"
    echo "    Created symlink: $SKILL_DIR → $SCRIPT_DIR"
fi
chmod +x "$SCRIPT_DIR/morning_levels.sh"

# ── 2. Check secrets in macOS Keychain ────────────────────────────────────────
echo "[2] Checking secrets..."
_kc_has() {
    security find-generic-password -s trading-morning-levels -a "$1" -w >/dev/null 2>&1
}
for KEY in DISCORD_LEVELS_WEBHOOK DISCORD_STATUS_WEBHOOK; do
    if _kc_has "$KEY"; then
        echo "    Keychain $KEY: present"
    else
        echo "    ⚠ Keychain $KEY missing — add with:"
        echo "      security add-generic-password -U -s trading-morning-levels \\"
        echo "          -a $KEY -w '<url>' -T /usr/bin/security"
    fi
done

# ── 3. Generate plist with correct HOME ───────────────────────────────────────
echo "[3] Installing launchd plist..."
mkdir -p "$LAUNCH_AGENTS"
PLIST="$LAUNCH_AGENTS/com.trading.morninglevels.plist"

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
TVM_DIR="$HOME/tradingview-mcp"
TVM_DRAWING="$TVM_DIR/src/core/drawing.js"
if [ ! -f "$TVM_DIR/src/cli/index.js" ]; then
    echo "    ⚠ Clone tradingview-mcp to ~/tradingview-mcp/"
else
    echo "    OK"
    # Apply upstream-bug patch: listDrawings/clearAll/removeOne/getProperties
    # call bare getChartApi() which is imported as _getChartApi, so they all
    # throw 'getChartApi is not defined'. We patch them to use the _resolve()
    # helper that drawShape already uses. Idempotent — checks patch markers.
    PATCH="$SCRIPT_DIR/patches/tradingview-mcp-drawing-getChartApi.patch"
    if [ -f "$TVM_DRAWING" ] && [ -f "$PATCH" ]; then
        if grep -q "^export async function clearAll" "$TVM_DRAWING" && \
           ! grep -q "_resolve();" "$TVM_DRAWING"; then
            echo "    Patching $TVM_DRAWING (upstream getChartApi reference bug)..."
            ( cd "$TVM_DIR" && git apply "$PATCH" ) && \
                echo "    Patch applied." || \
                echo "    ⚠ Patch failed — apply manually: cd $TVM_DIR && git apply $PATCH"
        else
            echo "    Drawing-fix patch: already applied (or upstream fixed)."
        fi
    fi
fi

echo ""
echo "=== Done ==="
echo "Start TradingView with: /Applications/TradingView.app/Contents/MacOS/TradingView --remote-debugging-port=9222 &"
