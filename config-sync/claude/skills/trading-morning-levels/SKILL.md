---
name: trading-morning-levels
description: Use when asked to draw morning key levels, refresh daily levels, set up support/resistance zones on TradingView charts, or run the morning levels routine for any watchlist. Triggers on "draw levels", "morning levels", "refresh levels", "set up levels".
---

# Trading Morning Levels

## Overview

Draws D/4H/1H VP + S/R + HVN levels on all watchlist symbols. Minis analyzed from scratch; micros copy from their mini. Runs top-down: Daily → 4H → 1H.

**Watchlist**: NQ1!, ES1!, GC1! (minis) + MNQ1!, MES1!, MGC1! (micros — copy only).

---

## Entry Point

```bash
python3 ~/.claude/skills/trading-morning-levels/run_levels.py [range_pts]
# Default range: ±1000 points
```

Scheduled daily at **8:30 AM ET Mon–Fri** via launchd (`com.trading.morninglevels`).

---

## Prerequisites

- TradingView Desktop with CDP on port 9222
- `tradingview-mcp` at `~/tradingview-mcp/`
- Python 3

**CRITICAL**: Always **force-kill and restart TradingView** before fetching bars. The Desktop app's bar buffer goes stale — a fresh launch loads today's bars correctly.

```bash
pkill -9 -f TradingView && sleep 5
/Applications/TradingView.app/Contents/MacOS/TradingView --remote-debugging-port=9222 &
sleep 20   # wait for charts + bar data to fully load
```

---

## Mini → Micro Map

| Mini | Micro | Notes |
|------|-------|-------|
| CME_MINI:NQ1! | CME_MINI:MNQ1! | NQ uses NewYork tab 0 for bars |
| CME_MINI:ES1! | CME_MINI:MES1! | |
| COMEX:GC1! | COMEX_MINI:MGC1! | |

Micros are **never analyzed independently** — only cleared and redrawn with the mini's levels JSON.

---

## Bar Fetching Order (per mini)

Fetch top-down — Daily first, then 4H, then 1H:

```bash
# For NQ: switch to NewYork tab 0 (live data, has all indicators)
node src/cli/index.js tab switch --index 0
sleep 2

# For ES/GC: switch symbol
node src/cli/index.js symbol --set "CME_MINI:ES1!"
sleep 3

# Fetch Daily → 4H → 1H
node src/cli/index.js timeframe --set D   && sleep 2
node src/cli/index.js ohlcv --resolution D --bars 100 > /tmp/daily.json

node src/cli/index.js timeframe --set 240 && sleep 2
node src/cli/index.js ohlcv --resolution 240 --bars 100 > /tmp/4h.json

node src/cli/index.js timeframe --set 60  && sleep 2
node src/cli/index.js ohlcv --resolution 60 --bars 100 > /tmp/1h.json
```

---

## VP Algorithm

Replicates **kv4coins Volume Profile** Pine Script (PUB;X0dKLxdLh46AZbqGl3Bgxb83fo9oWlDe):
- **68% value area** (not 70%)
- **200 price buckets**, dynamic bucket size = `(high - low) / 199`
- Full bar volume added to every bucket in bar's range (not divided)
- VAH/VAL expand from POC until 68% of total volume covered

**Lookback per TF:**
- Daily VP: last 10 daily bars (~2 weeks)
- 4H VP: last 12 4H bars (~2 trading days)
- 1H VP: today's session bars (futures session start = 22:00 UTC prev day); fallback to last 20 bars if < 4 session bars

---

## S/R Detection

Per-TF swing S/R (separate, not shared):
- **D S/R**: swing lb=1 on daily bars
- **4H S/R**: swing lb=2 on 4H bars + wide-bar lows/highs (last 12 4H bars)
- **1H S/R**: swing lb=5 on 1H bars + wide-bar lows/highs (last 20 1H bars)

**Wide-bar detection**: bars where range > **median** range AND volume > 1.3x mean volume. The HIGH and LOW of these bars become S/R. Uses median (not mean) so outlier wide bars don't inflate threshold.

**DEDUP**: 40pt minimum between levels in same TF list.

S/R levels bypass the priority resolve() — they always draw. Only deduped in `draw_levels.py`:
- S/R vs S/R: skip if within 15pt
- S/R vs VP: skip if within 8pt (true overlap only)

---

## HVN Detection

High Volume Nodes from VP: price buckets with volume > **2.0x mean** bucket volume. Adjacent qualifying buckets merged into one volume-weighted level.

Color: **Orange `#FF8C00`**, width=2, dashed.

---

## Level Priority (resolve conflicts)

When VP levels within 40pt of each other:

| Priority | Type |
|----------|------|
| 5 | Daily VP (VAH/VAL/POC) |
| 4 | 4H VP, 1H Session VP |
| 3 | HVN shelves |

Higher priority wins. S/R not in resolve() — always drawn separately.

---

## Color Scheme (D → 4H → 1H order)

| Type | VAH / VAL | POC | S/R |
|------|-----------|-----|-----|
| **Daily** | Dark Blue `#00008B` w=3 solid | Dark Red `#8B0000` w=3 solid | Mustard `#D4A017` w=2 solid |
| **4H** | Dark Blue `#00008B` w=2 solid | Dark Red `#8B0000` w=2 solid | Mustard `#D4A017` w=2 dashed |
| **1H** | Med Blue `#5B8DB8` w=1 solid | Med Red `#C05050` w=1 solid | Lt Mustard `#FFD050` w=1 dashed |
| **HVN** | — | — | Orange `#FF8C00` w=2 dashed |

---

## Analyze + Draw

```bash
SKILL=~/.claude/skills/trading-morning-levels
PRICE=$(node ~/tradingview-mcp/src/cli/index.js quote | python3 -c "import sys,json; print(json.load(sys.stdin)['last'])")

python3 $SKILL/analyze_levels.py "$PRICE" 1000 \
  /tmp/1h.json /tmp/4h.json /tmp/daily.json > /tmp/levels.json

node ~/tradingview-mcp/src/cli/index.js draw clear
python3 $SKILL/draw_levels.py /tmp/levels.json
```

---

## Screenshot + Discord

After levels are drawn for **NQ1! and ES1!**, `run_levels.py` automatically calls `screenshot_levels.py`.

**What it does:**
1. Reads `levels.json` for the symbol
2. Fetches last 20 1H bars from the active TV chart via tradingview-mcp
3. Renders a clean dark-theme mplfinance chart — candlesticks + level lines, no indicators
4. Saves PNG to `/tmp/{symbol}_levels_{YYYYMMDD}.png`
5. Checks `/tmp/morning_levels_success.json` for per-symbol success flag
6. If flag present → posts PNG to Discord webhook (`DISCORD_LEVELS_WEBHOOK` in `.env`)

**Manual run:**
```bash
python3 ~/.claude/skills/trading-morning-levels/screenshot_levels.py \
  CME_MINI:NQ1! /tmp/levels.json 29133.0
```

**Output files:**
- `/tmp/CME_MINI_NQ1__levels_YYYYMMDD.png` — chart PNG
- `/tmp/morning_levels_success.json` — per-symbol success flags written by `run_levels.py`

**Discord:** webhook URL stored in `~/.claude/skills/trading-morning-levels/.env` as `DISCORD_LEVELS_WEBHOOK`. Discord post is skipped (warning logged) if flag missing or webhook not set.

**Chart spec:** ±500pt range from current price, y-axis extends to show all levels, labels left + price boxes right, current price dotted line.

---

## NewYork Layout — Indicator Source

**For NQ bar fetching**: use NewYork tab index 0 (`b9YsTOVW`). This tab is always live on NQ1! 1m and has fresh bar data.

**If reading indicator values directly from chart**: use any NewYork tab. All 13 tabs show `CME_MINI:NQ1!` at 1m with:

| Indicator | Notes |
|-----------|-------|
| TradersArc Confluence 2.0 | |
| TradersArc (Prod) - Alerts | |
| TradersArc-ORB3.0 (×2) | |
| Price levels: Prior/current day/week, pre-market, after-hour H/L | |
| Bjorgum Key Levels | Different algo than our S/R — can mark 27,662 type levels |
| Volume Profile | kv4coins fixed-range (the one we replicate) |
| Session Volume Profile | Live session VAH/VAL/POC — 27,675 type levels |
| Visible Range Volume Profile | |
| BetterVolumeAvg | |

**Tab chart IDs**: `b9YsTOVW`, `6WRRMbum`, `PzSACA7u`, `1SaQYF3Y`, `dnhMEIDF`, `7BA5AtlP`, `LAeqIUg5`, `2GLu1z5r`, `FaOkfORw`, `GOEP91ZO`, `3kJhVYbi`, `DJy21XPv`

---

## Known Limitations

- **Session VP levels** (e.g., 27,675 = today's session VAH) cannot be read from the kv4coins indicator. The Session VP indicator uses Pine Script drawing objects not accessible via CDP. These levels only appear via Bjorgum Key Levels or manual observation.
- **Bar staleness**: if TV Desktop not force-killed/restarted, OHLCV buffer may be stale (ends days ago). Always restart before running.
- **OHLCV max 100 bars**: CDP reads chart's rendered bar buffer. Buffer limited to ~100 bars regardless of `--bars N`.

---

## Scheduling

launchd agent: `~/Library/LaunchAgents/com.trading.morninglevels.plist`
- Fires **Mon–Fri at 8:30 AM local time**
- Calls `morning_levels.sh` which force-kills TV, waits 20s, runs `run_levels.py`
- Logs to `~/.claude/skills/trading-morning-levels/morning_levels.log`

```bash
# Check logs
tail -50 ~/.claude/skills/trading-morning-levels/morning_levels.log

# Run manually
bash ~/.claude/skills/trading-morning-levels/morning_levels.sh

# Reload schedule after plist edit
launchctl unload ~/Library/LaunchAgents/com.trading.morninglevels.plist
launchctl load   ~/Library/LaunchAgents/com.trading.morninglevels.plist
```
