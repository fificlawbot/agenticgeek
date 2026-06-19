# Morning Levels Screenshot — Design Spec
**Date:** 2026-05-10  
**Status:** Approved

## Goal

After morning levels run successfully, auto-generate clean PNG screenshots of NQ and ES charts showing all drawn levels. No TradingView indicators visible — pure candlestick chart with horizontal level lines only. Screenshots saved to `/tmp/` for later social posting.

## Approach

Custom Python chart via `mplfinance`. Reads existing `levels.json` output + fetches last 20 1H OHLCV bars via tradingview-mcp CLI. No TradingView state touched.

## New Files

| File | Purpose |
|------|---------|
| `screenshot_levels.py` | Standalone script — takes symbol + levels JSON path, renders PNG |

## Modified Files

| File | Change |
|------|--------|
| `run_levels.py` | Write success JSON after all symbols complete; call `screenshot_levels.py` for NQ + ES |

## Data Flow

```
run_levels.py
  1. Existing: draw levels for all watchlist symbols
     └── per mini (NQ1!, ES1!): after successful draw
           New: call screenshot_levels.py immediately (not end-of-loop)
  2. New: write /tmp/morning_levels_success.json after full loop completes
     { "timestamp": "...", "symbols": {"NQ1!": "/tmp/nq_levels.json", ...}, "status": "ok" }

  Per-symbol call (not end-of-loop) means NQ screenshot is captured even if ES fails.

screenshot_levels.py <symbol> <levels_json_path>
  1. Read levels.json (VP POC/VAH/VAL + S/R + HVN levels with prices + colors)
  2. Fetch last 20 1H bars: node ~/tradingview-mcp/... ohlcv --resolution 60 --bars 20
  3. Get current price: node ~/tradingview-mcp/... quote
  4. Render chart → save /tmp/{symbol_slug}_levels_{YYYYMMDD}.png
  5. Print output path to stdout
```

## Chart Spec

- **Theme:** dark (`#131722` background)
- **Candles:** last 20 1H bars, yellow=up / blue=down
- **Y-range:** union of bar data range + all levels within ±500 pts of current price + 50pt padding. Extends below bars to show all levels.
- **Levels shown:** all levels from levels.json that fall within computed y-range
- **Labels:** level name left-side (colored), price box right-side (colored background)
- **Current price:** dotted grey line + grey price box
- **No volume panel**, no indicators, no TV overlays
- **Output filename:** `/tmp/{nq|es}_levels_YYYYMMDD.png`
- **Resolution:** 150 DPI, 14×9 inches

## Success Flag

`run_levels.py` writes `/tmp/morning_levels_success.json` only after all symbols complete without fatal error. `screenshot_levels.py` does not depend on this file at runtime (called directly by `run_levels.py`), but the file exists for future consumers (social posting, monitoring).

## Error Handling

- Screenshot failure does NOT abort or affect the main levels draw — errors are logged but `run_levels.py` continues
- If bars fetch fails, screenshot is skipped for that symbol with a warning
- If levels.json is empty or malformed, screenshot is skipped

## Dependencies

- `mplfinance` — already installed
- `tradingview-mcp` CLI — already used by existing flow
- No new dependencies

## Discord Delivery

After each screenshot is saved to `/tmp/`, post it to Discord via webhook.

- Webhook URL stored in `.env` as `DISCORD_LEVELS_WEBHOOK`
- `screenshot_levels.py` posts the PNG as a file attachment via `multipart/form-data` (no external libs — uses `urllib` or `requests` if available)
- Message content: `NQ1! Morning Levels — 2026-05-10` (symbol + date)
- Post happens per-symbol immediately after PNG saved
- Discord failure does NOT abort screenshot or levels draw — logged as warning

## Out of Scope

- Other social media posting (future phase)
- Symbols other than NQ1! and ES1!
- Interactive/HTML output
