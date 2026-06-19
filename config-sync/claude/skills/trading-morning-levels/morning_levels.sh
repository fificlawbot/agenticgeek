#!/bin/bash
# trading-morning-levels daily runner
# Called by launchd at 8:30 AM local time.
# Relaunches TradingView with CDP debug port, waits for connection, runs levels.

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

# Load .env — try local override first, then Google Drive project folder
# On a new machine: create ~/.trading-morning-levels.env with DISCORD_LEVELS_WEBHOOK=...
_load_env() {
    local f="$1"
    [ -f "$f" ] || return 1
    while IFS='=' read -r key val; do
        [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
        export "$key=$val"
    done < "$f"
    return 0
}

_load_env "$HOME/.trading-morning-levels.env" || \
_load_env "$(find "$HOME/Library/CloudStorage" -name ".env" -path "*/trading-morning-levels/.env" 2>/dev/null | head -1)" || \
true

LOG="$HOME/.claude/skills/trading-morning-levels/morning_levels.log"
SKILL="$HOME/.claude/skills/trading-morning-levels"
TV_APP="/Applications/TradingView.app/Contents/MacOS/TradingView"
CDP_PORT=9222

exec >> "$LOG" 2>&1
echo ""
echo "========================================="
echo "Morning Levels — $(date)"
echo "========================================="

# ── Force kill + restart TradingView (fresh bar data every morning) ───────────
TV_CLI="node /Users/trp/tradingview-mcp/src/cli/index.js"

launch_tv() {
    echo "  Killing TradingView..."
    pkill -9 -f "TradingView" 2>/dev/null || true
    sleep 10   # extra time for full OS cleanup + avoid Electron recovery mode

    echo "  Launching with --remote-debugging-port=$CDP_PORT ..."
    "$TV_APP" --remote-debugging-port=$CDP_PORT &
    echo "  PID: $!"

    echo "  Waiting for CDP..."
    for i in $(seq 1 40); do
        if curl -s "http://localhost:$CDP_PORT/json/version" > /dev/null 2>&1; then
            echo "  CDP ready after ${i}s"
            break
        fi
        sleep 1
    done

    echo "  Waiting for charts to load..."
    for i in $(seq 1 60); do
        PRICE=$($TV_CLI quote 2>/dev/null | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('last',0))" 2>/dev/null || echo "0")
        if [ "$PRICE" != "0" ] && [ "$PRICE" != "" ]; then
            echo "  Chart live after ${i}s — price: $PRICE"
            return 0
        fi
        sleep 2
    done
    echo "  WARNING: chart did not load (white screen?)"
    return 1
}

echo "[1] Force restarting TradingView for fresh bar data..."
if ! launch_tv; then
    echo "  Retrying launch (attempt 2)..."
    if ! launch_tv; then
        echo "  ERROR: TradingView failed to load after 2 attempts. Aborting."
        exit 1
    fi
fi

# ── Verify connection via CLI ─────────────────────────────────────────────────
echo "[2] Verifying tradingview-mcp connection..."
STATUS=$(node /Users/trp/tradingview-mcp/src/cli/index.js status 2>&1)
echo "  $STATUS"

if echo "$STATUS" | grep -q '"cdp_connected": true'; then
    echo "  Connected OK"
else
    echo "  ERROR: Could not connect to TradingView. Aborting."
    exit 1
fi

# ── Run morning levels ────────────────────────────────────────────────────────
echo "[3] Running morning levels (±1000 pts)..."
/usr/bin/python3 "$SKILL/run_levels.py" 1000

echo "[4] Done — $(date)"
