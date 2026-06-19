# trading-morning-levels

Draws Daily / 4H / 1H Volume Profile (VP) + key S/R levels on every symbol in a TradingView watchlist. Runs via Claude Code skill or as a daily scheduled job (macOS launchd at 8:30 AM).

## What it does

For each symbol in the **"Levels"** watchlist:
1. Fetches OHLCV bars at 1H, 4H, and Daily timeframes
2. Calculates VP (POC, VAH, VAL) matching the kv4coins TradingView indicator (68% value area, fixed-range lookback)
3. Identifies swing S/R levels per timeframe
4. Draws all levels on the TradingView chart with the color scheme below
5. **Micros** (MNQ, MES, MGC) copy levels from their mini counterparts (NQ, ES, GC) — no duplicate computation

## Color scheme

| Timeframe | VAH / VAL | POC | S/R |
|-----------|-----------|-----|-----|
| Daily | Dark Blue `#00008B` w=3 | Dark Red `#8B0000` w=3 | Mustard `#D4A017` w=2 solid |
| 4H | Dark Blue `#00008B` w=2 | Dark Red `#8B0000` w=2 | Mustard `#D4A017` w=2 dashed |
| 1H | Med Blue `#5B8DB8` w=1 | Med Red `#C05050` w=1 | Lt Mustard `#FFD050` w=1 dashed |

## Prerequisites

- **TradingView Desktop** running with `--remote-debugging-port=9222`
- **[tradingview-mcp](https://github.com/tradesdontlie/tradingview-mcp)** installed at `~/tradingview-mcp/`
- **Python 3** and **Node.js**
- "Levels" watchlist in TradingView sidebar

## Files

| File | Purpose |
|------|---------|
| `run_levels.py` | Main entry point — processes all watchlist symbols |
| `analyze_levels.py` | VP + S/R calculation (exact Pine Script replication) |
| `draw_levels.py` | Draws levels on active TradingView chart via CLI |
| `morning_levels.sh` | Wrapper: relaunches TV with CDP if needed, then runs |
| `SKILL.md` | Claude Code skill definition |

## Usage

```bash
# Run manually
python3 run_levels.py [range_pts]   # default ±1000 points

# Run via wrapper (auto-relaunches TradingView if needed)
bash morning_levels.sh
```

## Scheduling (macOS launchd)

Fires daily at 8:30 AM local time:

```bash
# Install
cp com.trading.morninglevels.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.trading.morninglevels.plist

# Disable
launchctl unload ~/Library/LaunchAgents/com.trading.morninglevels.plist

# Check logs
tail -f ~/.claude/skills/trading-morning-levels/morning_levels.log
```

## VP Algorithm

Replicates the [kv4coins Volume Profile](https://www.tradingview.com/script/X0dKLxdL/) Pine Script indicator:
- 200 price buckets (dynamic bucket size = price range / 199)
- Full bar volume added to every bucket in `[low, high)`
- 68% value area expansion from POC outward
- Lookback: 100 bars (1H), 30 bars (4H), 10 bars (Daily)

## Mini → Micro map

| Mini | Micro |
|------|-------|
| CME_MINI:NQ1! | CME_MINI:MNQ1! |
| CME_MINI:ES1! | CME_MINI:MES1! |
| COMEX:GC1! | COMEX_MINI:MGC1! |
