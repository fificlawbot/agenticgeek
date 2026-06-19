#!/usr/bin/env python3
"""
trading-morning-levels runner
Draws D/4H/1H VP + S/R levels for all symbols in the "Levels" watchlist.
Micros (MNQ, MES, MGC) copy levels from their mini counterparts.

Usage: python3 run_levels.py [range_pts]
"""

import sys, os, json, subprocess, time, tempfile, datetime, signal, glob, shutil

SKILL  = os.path.expanduser("~/.claude/skills/trading-morning-levels")
TV     = ["node", os.path.expanduser("~/tradingview-mcp/src/cli/index.js")]
TV_APP = "/Applications/TradingView.app/Contents/MacOS/TradingView"
RANGE  = sys.argv[1] if len(sys.argv) > 1 else "1000"

# Weekday guard — skip weekends (launchd doesn't support day-of-week natively)
today = datetime.date.today()
if today.weekday() >= 5:  # 5=Sat, 6=Sun
    print(f"=== Skipping — {today.strftime('%A')} is a weekend. ===")
    sys.exit(0)

# TV restart is handled by morning_levels.sh before this script runs.
# run_levels.py assumes TV is already live with CDP on port 9222.

# Fallback symbol list when watchlist panel is closed
FALLBACK_SYMBOLS = [
    "CME_MINI:NQ1!",
    "CME_MINI:ES1!",
    "CME_MINI:MNQ1!",
    "CME_MINI:MES1!",
    "COMEX:GC1!",
    "COMEX_MINI:MGC1!",
]

# Mini → Micro map
MICRO_OF = {
    "CME_MINI:NQ1!":  "CME_MINI:MNQ1!",
    "CME_MINI:ES1!":  "CME_MINI:MES1!",
    "COMEX:GC1!":     "COMEX_MINI:MGC1!",
}

# NewYork layout tab index for each mini symbol
# Use these tabs for bar fetching — they're live and have all indicators
# Tab 0 = b9YsTOVW (NQ1! 1m, NewYork layout)
NEWYORK_TAB = {
    "CME_MINI:NQ1!": 0,   # always use NewYork tab for NQ bar data
}
MINI_OF = {v: k for k, v in MICRO_OF.items()}

def tv(*args, check=False):
    cmd = TV + list(args)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(r.stderr.strip())
    try:
        return json.loads(r.stdout)
    except Exception:
        return {}

def set_symbol(sym):
    tv("symbol", "--set", sym)
    time.sleep(3)

def set_tf(tf):
    tv("timeframe", "--set", str(tf))
    time.sleep(2)

def fetch_bars(outfile):
    r = tv("ohlcv", "--resolution", "60", "--bars", "200")
    bars = r.get("bars", [])
    with open(outfile, "w") as f:
        json.dump(bars, f)
    return len(bars)

def fetch_bars_tf(tf, outfile):
    """Fetch bars at given TF, return bar count."""
    set_tf(tf)
    r = tv("ohlcv", "--resolution", str(tf), "--bars", "200")
    bars = r.get("bars", [])
    with open(outfile, "w") as f:
        json.dump(bars, f)
    return len(bars)

def get_price():
    r = tv("quote")
    raw = str(r.get("last", r.get("close", 0)))
    return raw.replace(",", "")

def analyze(price, f1h, f4h, fdaily, outfile):
    cmd = ["python3", f"{SKILL}/analyze_levels.py",
           price, RANGE, f1h, f4h, fdaily]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"analyze failed: {r.stderr.strip()}")
    with open(outfile, "w") as f:
        f.write(r.stdout)
    d = json.loads(r.stdout)
    print(f"    D   VAH={d['daily']['vah']}  POC={d['daily']['poc']}  VAL={d['daily']['val']}")
    print(f"    4H  VAH={d['four_h']['vah']}  POC={d['four_h']['poc']}  VAL={d['four_h']['val']}")
    print(f"    1H  VAH={d['one_h']['vah']}  POC={d['one_h']['poc']}  VAL={d['one_h']['val']}")
    print(f"    D S/R:  {d['daily']['sr']}")
    print(f"    4H S/R: {d['four_h']['sr']}")
    print(f"    1H S/R: {d['one_h']['sr']}")

def draw_levels(sym, levels_json):
    print(f"  → {sym}: switching chart...")
    set_symbol(sym)
    set_tf(60)
    tv("draw", "clear")
    time.sleep(0.5)
    r = subprocess.run(
        ["python3", f"{SKILL}/draw_levels.py", levels_json],
        capture_output=True, text=True
    )
    print(f"    {r.stdout.strip()}")
    if r.stderr.strip():
        print(f"    WARN: {r.stderr.strip()[:120]}")
    count = tv("draw", "list").get("count", "?")
    print(f"    ✓ {count} drawings on {sym}")

SUCCESS_FLAG = "/tmp/morning_levels_success.json"

# Symbols for which to generate screenshots after levels are drawn
SCREENSHOT_SYMS = {"CME_MINI:NQ1!", "CME_MINI:ES1!"}

def _mark_symbol_success(sym):
    """Write per-symbol success entry. screenshot_levels.py checks this before Discord post."""
    try:
        data = json.loads(open(SUCCESS_FLAG).read()) if os.path.exists(SUCCESS_FLAG) else {}
    except Exception:
        data = {}
    data[sym] = {"status": "ok", "timestamp": datetime.datetime.now().isoformat()}
    with open(SUCCESS_FLAG, "w") as f:
        json.dump(data, f, indent=2)

def _screenshot_and_post(sym, levels_json, price):
    """Call screenshot_levels.py in a subprocess. Failure is non-fatal."""
    try:
        r = subprocess.run(
            ["python3", f"{SKILL}/screenshot_levels.py", sym, levels_json, str(price)],
            capture_output=True, text=True, timeout=60,
        )
        if r.stdout.strip():
            print(f"    Screenshot: {r.stdout.strip()}")
        if r.stderr.strip():
            print(f"    Screenshot stderr: {r.stderr.strip()[:200]}")
        if r.returncode != 0:
            print(f"    WARNING: screenshot exited {r.returncode}")
    except Exception as e:
        print(f"    WARNING: screenshot error: {e}")

# ── Main ──────────────────────────────────────────────────────────────────────
print("=== Trading Morning Levels ===")
print(f"Range: ±{RANGE} pts")
print()

# Cleanup screenshots from previous days
today_str = today.strftime("%Y%m%d")
for old_png in glob.glob("/tmp/*_levels_*.png"):
    if today_str not in os.path.basename(old_png):
        os.remove(old_png)
        print(f"Cleaned up old screenshot: {os.path.basename(old_png)}")

status = tv("status")
print(f"Connected: {status.get('chart_symbol')} on {status.get('target_url','')}")
print()

# Get watchlist — open panel first, retry if closed
print("Opening watchlist panel...")
tv("ui", "panel", "--name", "watchlist")
time.sleep(2)
wl = tv("watchlist", "get")
symbols = [s["symbol"] for s in wl.get("symbols", [])]

if not symbols:
    print(f"Watchlist panel closed or empty (source={wl.get('source')}). Using fallback symbol list.")
    symbols = FALLBACK_SYMBOLS
else:
    print(f"Watchlist ({len(symbols)}): {symbols}")
print()

# Separate minis and micros — micros ONLY drawn via copy, never independently
minis  = [s for s in symbols if s not in MINI_OF]
micros = [s for s in symbols if s in MINI_OF]
print(f"Minis  ({len(minis)}):  {minis}")
print(f"Micros ({len(micros)}): {micros} ← copy only, no independent analysis")
print()

step = 0
total_steps = len(minis) + len(micros)

with tempfile.TemporaryDirectory() as TMP:

    for sym in minis:
        step += 1
        print(f"[{step}/{total_steps}] {sym}  (Daily → 4H → 1H)")

        safe   = sym.replace(":", "_").replace("/", "_")
        f1h    = f"{TMP}/{safe}_1h.json"
        f4h    = f"{TMP}/{safe}_4h.json"
        fdaily = f"{TMP}/{safe}_daily.json"
        flvl   = f"{TMP}/{safe}_levels.json"

        # Fetch bars — NewYork tab for NQ (live data), else switch symbol
        ny_tab = NEWYORK_TAB.get(sym)
        if ny_tab is not None:
            print(f"  Bars via NewYork tab {ny_tab}...")
            tv("tab", "switch", "--index", str(ny_tab))
            time.sleep(2)
            # Verify tab has the right symbol — fall back to set_symbol if wrong
            actual = tv("quote").get("symbol", "")
            if actual != sym:
                print(f"  WARNING: tab {ny_tab} shows {actual}, expected {sym} — forcing symbol set")
                set_symbol(sym)
        else:
            set_symbol(sym)

        # Fetch Daily → 4H → 1H (top-down order)
        nd  = fetch_bars_tf("D",  fdaily); print(f"    Daily: {nd} bars")
        n4h = fetch_bars_tf(240,  f4h);    print(f"    4H:    {n4h} bars")
        n1h = fetch_bars_tf(60,   f1h);    print(f"    1H:    {n1h} bars")

        set_tf(60)
        price = get_price()
        print(f"  Price: {price}")

        # Sanity check — NQ/ES should never be < 1000
        if float(price) < 1000:
            print(f"  ERROR: price {price} is implausible for {sym} — aborting this symbol")
            continue

        print(f"  Analyzing (Daily → 4H → 1H)...")
        analyze(price, f1h, f4h, fdaily, flvl)
        shutil.copy(flvl, f"{SKILL}/levels_{safe}.json")

        draw_levels(sym, flvl)
        _mark_symbol_success(sym)

        # ── Screenshot + Discord post (NQ/ES only) ────────────────────────────
        if sym in SCREENSHOT_SYMS:
            _screenshot_and_post(sym, flvl, price)

        # ── Copy levels to corresponding micro (no re-analysis) ───────────────
        micro = MICRO_OF.get(sym)
        if micro and micro in micros:
            step += 1
            print(f"[{step}/{total_steps}] {micro}  (copy from {sym} — no re-analysis)")
            draw_levels(micro, flvl)
        print()

try:
    _data = json.loads(open(SUCCESS_FLAG).read()) if os.path.exists(SUCCESS_FLAG) else {}
except Exception:
    _data = {}
_data["__done__"] = {"status": "ok", "timestamp": datetime.datetime.now().isoformat()}
with open(SUCCESS_FLAG, "w") as _sf:
    json.dump(_data, _sf, indent=2)
print(f"Success flag: {SUCCESS_FLAG}")

# Leave chart on NQ1! 1H for trading
set_symbol("CME_MINI:NQ1!")
set_tf(60)
print("Chart set to NQ1! 1H")

print(f"=== Done — {step}/{total_steps} symbols ===")
