---
name: tv-cdp-parity
description: "TV CDP automation — what works, what fails, lessons for parity collection"
metadata: 
  node_type: memory
  type: project
  originSessionId: a66e71a5-67a5-4ecf-aacf-16abd65faf99
---

# TV CDP Parity Automation — Lessons Learned

## What Works ✓
- **CDP connection**: `ws://localhost:9222` (TV Desktop Electron app, must launch with `--remote-debugging-port=9222`)
- **Tab detection**: `tradingview.com/chart` in URL
- **Pasting Pine script**: pbcopy + Ctrl+A + Ctrl+V into `.monaco-editor .inputarea`
- **"Update on chart" button**: Has EMPTY textContent but `title='Update on chart'` — must search by title, not textContent
- **Date range early exit**: Check if button text includes "Jan 1, 2024" and "Apr 30, 2026" — skip the whole flow
- **Report ready polling**: Check `document.body.innerText.includes('Updating report')` — polls until false
- **Metrics reading**: TreeWalker on body, leaf nodes, label+next-sibling pattern works well
- **CSV download**: `button[title='Download .csv']`, watch `~/Downloads/*.csv` for new file

## What Fails ✗ / Workarounds Needed

### Profile switching via Pine patching
- TV PRESERVES input values when "Update on chart" is clicked even if Pine default changes
- Fix needed: must either (a) remove+readd indicator OR (b) open Settings→Inputs and change dropdown
- Remove+readd was unreliable — the Remove button detection grabbed wrong elements

### Date dialog "Select" button
- In a FRESH date dialog (no prior dates), "Select" button text is there but at y≈703
- "Select first available date" is a DIFFERENT button (inside calendar area)
- After navigating calendar and clicking end date, "Select" button may disappear or change position
- Workaround: click at known coordinates (796, 703) or fallback to rightmost button in footer

### Calendar navigation direction
- `_navigate_to_month()` only handled NEXT month; needed PREV month too
- When fresh dialog opens at current month (May 2026), need to go BACKWARDS to Jan 2024
- Fixed: detect current header, compute direction, click prev/next accordingly

### "Trade with your broker" dialog
- Clicking Settings gear at wrong coordinates opens this broker dialog instead
- The correct Settings gear for TA-ORBV2 indicator is at y≈172 (depends on how many indicators are loaded)
- The TV settings icon at top-right (x≈1325) opens global settings, not indicator settings

### Pine Editor close vs Update
- Clicking "×" at (1433, 33) closes the Pine Editor panel entirely
- After closing, need to reopen via sidebar Pine icon

## Recommended Approach for StrB/StrC Collection

**Manual profile switch** (most reliable):
1. User: open TV → click gear on TA-ORBV2 → Inputs tab → change Strategy Profile to StrB → OK
2. Script: `python3 scripts/tv_parity_runner.py --skip-paste --profile StrB`
3. Repeat for StrC

**Automated profile switch** (if implementing):
- Open Settings dialog: double-click indicator NAME in legend (not gear icon)
- Or: find Settings button that is in same row as TA-ORBV2 text (same y-coordinate ±5px)
- Click "Inputs" tab
- Find button with textContent "StrA"/"StrB"/"StrC" — that's the profile dropdown
- Click it, then click the target profile option in the dropdown

## CDP Script Location
`~/projects/nq-es-backtester/scripts/tv_parity_runner.py`

Usage:
- Full run: `python3 scripts/tv_parity_runner.py --profile StrA`
- Skip paste: `python3 scripts/tv_parity_runner.py --skip-paste --profile StrA`

**Why:** CDP automation was built to collect TV strategy report metrics without manual interaction, to validate Python↔TV parity for the baseline.
**How to apply:** Use `--skip-paste` after manually setting the profile in TV to avoid the paste+profile-reset issue.
