#!/bin/bash
# trading-morning-levels — draw D/4H/1H VP + S/R levels for all watchlist symbols.
# Micros (MNQ, MES, MGC) copy levels from their corresponding minis (NQ, ES, GC).
#
# Usage: bash run_levels.sh [range_pts]
#   range_pts: ±points filter for S/R lines (default 1000)

set -e
TV="node /Users/trp/tradingview-mcp/src/cli/index.js"
SKILL="$HOME/.claude/skills/trading-morning-levels"
RANGE="${1:-1000}"
TMP="/tmp/tv_levels_$$"
mkdir -p "$TMP"

# ── Mini → Micro symbol map ───────────────────────────────────────────────────
declare -A MICRO_OF
MICRO_OF["CME_MINI:NQ1!"]="CME_MINI:MNQ1!"
MICRO_OF["CME_MINI:ES1!"]="CME_MINI:MES1!"
MICRO_OF["COMEX:GC1!"]="COMEX_MINI:MGC1!"

# Reverse map: micro → mini
declare -A MINI_OF
for mini in "${!MICRO_OF[@]}"; do
    micro="${MICRO_OF[$mini]}"
    MINI_OF["$micro"]="$mini"
done

# ── Helper: check CDP connection ──────────────────────────────────────────────
check_connection() {
    $TV status > /dev/null 2>&1 || {
        echo "ERROR: TradingView not connected."
        echo "Launch: pkill -9 -f TradingView && /Applications/TradingView.app/Contents/MacOS/TradingView --remote-debugging-port=9222 &"
        exit 1
    }
}

# ── Helper: fetch bars for symbol at given TF ─────────────────────────────────
fetch_bars() {
    local sym="$1" tf="$2" outfile="$3"
    $TV symbol --set "$sym" > /dev/null 2>&1
    sleep 2
    $TV timeframe --set "$tf" > /dev/null 2>&1
    sleep 2
    $TV ohlcv --resolution "$tf" --bars 200 \
        | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d['bars']))" \
        > "$outfile"
}

# ── Helper: draw levels for a symbol using pre-computed levels JSON ───────────
draw_for_symbol() {
    local sym="$1" levels_json="$2"
    echo "  Switching to $sym..."
    $TV symbol --set "$sym" > /dev/null 2>&1
    sleep 2
    $TV timeframe --set 60 > /dev/null 2>&1
    sleep 1
    echo "  Clearing drawings..."
    $TV draw clear > /dev/null 2>&1 || true
    echo "  Drawing levels..."
    python3 "$SKILL/draw_levels.py" "$levels_json"
    COUNT=$($TV draw list 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['count'])" 2>/dev/null || echo "?")
    echo "  ✓ $COUNT drawings on $sym"
}

# ── Main ──────────────────────────────────────────────────────────────────────
echo "=== Trading Morning Levels ==="
echo "Range: ±$RANGE points"
check_connection

echo ""
echo "[1] Fetching watchlist..."
SYMBOLS=$($TV watchlist get | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(' '.join(s['symbol'] for s in d['symbols']))
")
echo "  Symbols: $SYMBOLS"

# Separate minis from micros
MINIS=()
MICROS=()
for sym in $SYMBOLS; do
    if [[ -n "${MINI_OF[$sym]+x}" ]]; then
        MICROS+=("$sym")
    else
        MINIS+=("$sym")
    fi
done

echo "  Minis:  ${MINIS[*]}"
echo "  Micros: ${MICROS[*]} (will copy from minis)"

TOTAL=${#SYMBOLS[@]}
IDX=0

# ── Process minis ─────────────────────────────────────────────────────────────
for SYM in "${MINIS[@]}"; do
    IDX=$((IDX + 1))
    echo ""
    echo "[$IDX/$TOTAL] $SYM"

    SAFE="${SYM//[:\/]/_}"

    echo "  Fetching 1H bars..."
    fetch_bars "$SYM" 60 "$TMP/${SAFE}_1h.json"

    echo "  Fetching 4H bars..."
    fetch_bars "$SYM" 240 "$TMP/${SAFE}_4h.json"

    echo "  Fetching Daily bars..."
    fetch_bars "$SYM" D "$TMP/${SAFE}_daily.json"

    # Get current price (switch back to 1H first)
    $TV timeframe --set 60 > /dev/null 2>&1; sleep 1
    PRICE=$($TV quote | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['last'])" | tr -d ',')
    echo "  Price: $PRICE"

    echo "  Analyzing VP levels..."
    python3 "$SKILL/analyze_levels.py" "$PRICE" "$RANGE" \
        "$TMP/${SAFE}_1h.json" \
        "$TMP/${SAFE}_4h.json" \
        "$TMP/${SAFE}_daily.json" \
        > "$TMP/${SAFE}_levels.json"

    python3 -c "
import json
d = json.load(open('$TMP/${SAFE}_levels.json'))
print(f'  D   VAH={d[\"daily\"][\"vah\"]}  POC={d[\"daily\"][\"poc\"]}  VAL={d[\"daily\"][\"val\"]}')
print(f'  4H  VAH={d[\"four_h\"][\"vah\"]}  POC={d[\"four_h\"][\"poc\"]}  VAL={d[\"four_h\"][\"val\"]}')
print(f'  1H  VAH={d[\"one_h\"][\"vah\"]}  POC={d[\"one_h\"][\"poc\"]}  VAL={d[\"one_h\"][\"val\"]}')
"

    # Draw on mini
    draw_for_symbol "$SYM" "$TMP/${SAFE}_levels.json"

    # Draw same levels on corresponding micro (if in watchlist)
    MICRO="${MICRO_OF[$SYM]}"
    if [[ -n "$MICRO" ]] && [[ " ${MICROS[*]} " == *" $MICRO "* ]]; then
        IDX=$((IDX + 1))
        echo ""
        echo "[$IDX/$TOTAL] $MICRO (copying from $SYM)"
        draw_for_symbol "$MICRO" "$TMP/${SAFE}_levels.json"
    fi
done

echo ""
echo "=== Done. Levels drawn for all ${#SYMBOLS[@]} symbols. ==="

# Cleanup
rm -rf "$TMP"
