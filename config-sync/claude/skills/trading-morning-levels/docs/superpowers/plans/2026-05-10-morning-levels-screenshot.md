# Morning Levels Screenshot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** After morning levels run succeeds for NQ1! and ES1!, auto-generate clean 1H candlestick PNG charts with level lines, save to `/tmp/`, and post to Discord webhook.

**Architecture:** `screenshot_levels.py` is a standalone script called per-symbol by `run_levels.py` immediately after `draw_levels()`. It reads the existing `levels.json`, fetches 20 1H bars via tradingview-mcp CLI (symbol already active on chart), renders a dark-theme mplfinance chart, saves PNG to `/tmp/`, and posts to Discord. `run_levels.py` gets a `_screenshot_and_post()` helper inserted after the draw call (NQ/ES only) and a success JSON write after the full loop.

**Tech Stack:** Python 3, mplfinance, matplotlib, urllib (stdlib), tradingview-mcp CLI

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `screenshot_levels.py` | Chart render + Discord post — standalone, callable by subprocess |
| Create | `tests/test_screenshot_levels.py` | Unit tests for pure functions |
| Modify | `run_levels.py` | Add `_screenshot_and_post()` helper + call after draw + success JSON write |

---

### Task 1: Create `screenshot_levels.py` — chart rendering core

**Files:**
- Create: `screenshot_levels.py`
- Create: `tests/test_screenshot_levels.py`

The script takes three CLI args: `symbol`, `levels_json_path`, `price`.
Pure functions `build_levels_from_json` and `compute_y_range` are at module level so tests can import them.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_screenshot_levels.py`:

```python
import sys, os, json, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from screenshot_levels import build_levels_from_json, compute_y_range

MOCK_LEVELS = {
    "daily": {"vah": 29400.0, "val": 29100.0, "poc": 29250.0, "sr": [29350.0]},
    "4h":    {"vah": 29300.0, "val": 29050.0, "poc": 29180.0, "sr": [29280.0]},
    "1h":    {"vah": 29200.0, "val": 28900.0, "poc": 29100.0, "sr": [29160.0]},
    "hvn":   [29220.0],
}

MOCK_BARS = [
    {"time": 1715000000 + i*3600, "open": 29100.0+i*5, "high": 29120.0+i*5,
     "low": 29080.0+i*5, "close": 29110.0+i*5, "volume": 40000}
    for i in range(20)
]


def test_build_levels_returns_all_present_levels():
    price = 29200.0
    result = build_levels_from_json(MOCK_LEVELS, price, range_pts=500)
    labels = [r[1] for r in result]
    assert "D VAH" in labels
    assert "D VAL" in labels
    assert "D POC" in labels
    assert "4H VAH" in labels
    assert "1H POC" in labels
    assert "HVN"   in labels
    assert "D S/R"  in labels


def test_build_levels_filters_by_range():
    price = 29200.0
    result = build_levels_from_json(MOCK_LEVELS, price, range_pts=50)
    for p, *_ in result:
        assert abs(p - price) <= 50


def test_build_levels_skips_none():
    data = {"daily": {"vah": None, "val": 29100.0, "poc": None, "sr": []},
            "4h": {}, "1h": {}, "hvn": []}
    result = build_levels_from_json(data, 29100.0, range_pts=500)
    labels = [r[1] for r in result]
    assert "D VAH" not in labels
    assert "D POC" not in labels
    assert "D VAL" in labels


def test_build_levels_correct_colors():
    result = build_levels_from_json(MOCK_LEVELS, 29200.0, range_pts=500)
    by_label = {r[1]: r for r in result}
    assert by_label["D POC"][2]  == "#FF4444"   # POC = red
    assert by_label["D VAH"][2]  == "#4488FF"   # VAH = blue
    assert by_label["D S/R"][2]  == "#FFD700"   # S/R = yellow
    assert by_label["HVN"][2]    == "#FFA500"   # HVN = orange


def test_compute_y_range_extends_below_bars_for_levels():
    # levels extend below bar range → y_min should be below bar_low
    bars = MOCK_BARS  # lows around 29080–29175
    level_prices = [28500.0, 29300.0]  # 28500 is well below bars
    y_min, y_max = compute_y_range(bars, level_prices, pad=50)
    assert y_min < 29080.0   # must go below bar lows
    assert y_min <= 28500.0 - 50


def test_compute_y_range_extends_above_bars_for_levels():
    bars = MOCK_BARS  # highs around 29120–29215
    level_prices = [29600.0, 29100.0]  # 29600 above bars
    y_min, y_max = compute_y_range(bars, level_prices, pad=50)
    assert y_max >= 29600.0 + 50


def test_compute_y_range_uses_bar_range_when_no_extreme_levels():
    bars = MOCK_BARS
    level_prices = [29150.0]  # within bar range
    y_min, y_max = compute_y_range(bars, level_prices, pad=50)
    bar_low  = min(b["low"]  for b in bars)
    bar_high = max(b["high"] for b in bars)
    assert y_min == bar_low  - 50
    assert y_max == bar_high + 50
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
cd "/Users/trp/Library/CloudStorage/GoogleDrive-astha.tarun@gmail.com/My Drive/FifiBot/Projects/trading-morning-levels"
python3 -m pytest tests/test_screenshot_levels.py -v 2>&1 | head -30
```

Expected: `ModuleNotFoundError: No module named 'screenshot_levels'`

- [ ] **Step 3: Create `screenshot_levels.py` with pure functions + full chart render**

Create `screenshot_levels.py`:

```python
#!/usr/bin/env python3
"""
screenshot_levels.py <symbol> <levels_json_path> <price>

Renders clean 1H candlestick chart + level lines. Saves PNG to /tmp/.
Posts PNG to Discord webhook (DISCORD_LEVELS_WEBHOOK in .env).
"""

import sys, os, json, subprocess, datetime, urllib.request
from pathlib import Path
import pandas as pd
import mplfinance as mpf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

TV    = ["node", os.path.expanduser("~/tradingview-mcp/src/cli/index.js")]
SKILL = os.path.dirname(os.path.abspath(__file__))

RANGE_PTS = 500
BAR_PAD   = 50


def load_env():
    env_path = Path(SKILL) / ".env"
    env = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def build_levels_from_json(data, current_price, range_pts=RANGE_PTS):
    """
    Returns list of (price, label, color, linewidth, linestyle).
    Skips None prices. Filters to within range_pts of current_price.
    """
    entries = []
    for key, prefix in [("daily", "D"), ("4h", "4H"), ("1h", "1H")]:
        tf = data.get(key, {})
        if tf.get("vah"):
            entries.append((tf["vah"], f"{prefix} VAH", "#4488FF", 2, "-"))
        if tf.get("val"):
            entries.append((tf["val"], f"{prefix} VAL", "#4488FF", 2, "-"))
        if tf.get("poc"):
            entries.append((tf["poc"], f"{prefix} POC", "#FF4444", 2, "-"))
        for p in tf.get("sr", []):
            if p:
                entries.append((p, f"{prefix} S/R", "#FFD700", 1, "--"))
    for p in data.get("hvn", []):
        if p:
            entries.append((p, "HVN", "#FFA500", 1, "--"))
    return [
        (price, label, color, lw, ls)
        for price, label, color, lw, ls in entries
        if abs(price - current_price) <= range_pts
    ]


def compute_y_range(bars, level_prices, pad=BAR_PAD):
    """
    Returns (y_min, y_max): union of bar price range and level prices + padding.
    """
    bar_low  = min(b["low"]  for b in bars)
    bar_high = max(b["high"] for b in bars)
    all_prices = list(level_prices) + [bar_low, bar_high]
    return min(all_prices) - pad, max(all_prices) + pad


def fetch_1h_bars():
    """Fetch last 20 1H bars from currently active TV chart."""
    r = subprocess.run(
        TV + ["ohlcv", "--resolution", "60", "--bars", "20"],
        capture_output=True, text=True, timeout=30
    )
    return json.loads(r.stdout).get("bars", [])


def save_chart(symbol, bars, levels, current_price, date_str):
    """
    Render dark-theme mplfinance chart with level lines.
    Returns path to saved PNG at /tmp/{safe}_{date_str}.png.
    """
    df = pd.DataFrame(bars)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df = df.set_index("time").rename(columns={
        "open": "Open", "high": "High", "low": "Low",
        "close": "Close", "volume": "Volume"
    })

    level_prices = [p for p, *_ in levels]
    y_min, y_max = compute_y_range(bars, level_prices)

    hlines = dict(
        hlines=[p for p, *_ in levels],
        colors=[c for _, _, c, *_ in levels],
        linewidths=[lw for _, _, _, lw, _ in levels],
        linestyle=[ls for _, _, _, _, ls in levels],
    )

    mc = mpf.make_marketcolors(
        up="#F0C040", down="#4A90D9",
        edge={"up": "#F0C040", "down": "#4A90D9"},
        wick={"up": "#F0C040", "down": "#4A90D9"},
    )
    style = mpf.make_mpf_style(
        base_mpf_style="nightclouds",
        marketcolors=mc,
        facecolor="#131722", figcolor="#131722",
        gridstyle="--", gridcolor="#222b3a", gridaxis="horizontal",
    )

    fig, axes = mpf.plot(
        df, type="candle", style=style, hlines=hlines, volume=False,
        ylabel="", returnfig=True, figsize=(14, 9), tight_layout=False,
        datetime_format="%m/%d %H:%M", xrotation=30, ylim=(y_min, y_max),
    )
    ax = axes[0]
    ax.yaxis.set_visible(False)

    for price, label, color, lw, ls in levels:
        ax.annotate(
            f"{price:,.2f}",
            xy=(1, price), xycoords=("axes fraction", "data"),
            xytext=(8, 0), textcoords="offset points",
            va="center", ha="left", fontsize=8.5, color="white", fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.3", facecolor=color, alpha=0.92, edgecolor="none"),
            annotation_clip=False,
        )
        ax.annotate(
            label,
            xy=(0, price), xycoords=("axes fraction", "data"),
            xytext=(-8, 0), textcoords="offset points",
            va="center", ha="right", fontsize=8.5, color=color, fontweight="bold",
            annotation_clip=False,
        )

    ax.axhline(current_price, color="#888888", linewidth=0.8, linestyle=":", alpha=0.7, zorder=0)
    ax.annotate(
        f"{current_price:,.2f}",
        xy=(1, current_price), xycoords=("axes fraction", "data"),
        xytext=(8, 0), textcoords="offset points",
        va="center", ha="left", fontsize=8.5, color="white",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#444455", alpha=0.92, edgecolor="none"),
        annotation_clip=False,
    )

    safe = symbol.replace(":", "_").replace("/", "_")
    # Extract just the root symbol for the title (CME_MINI:NQ1! → NQ1!)
    display = symbol.split(":")[-1] if ":" in symbol else symbol
    ax.set_title(f"{display}  ·  1H  ·  Morning Levels  ·  {date_str}",
                 color="#cccccc", fontsize=12, pad=10, loc="left")

    fig.subplots_adjust(left=0.06, right=0.84, top=0.93, bottom=0.1)

    out_path = f"/tmp/{safe}_levels_{date_str}.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="#131722")
    plt.close(fig)
    return out_path


def discord_post(webhook_url, png_path, symbol, date_str):
    """
    POST PNG as file attachment to Discord webhook.
    Returns HTTP status code. Raises on network error.
    """
    display = symbol.split(":")[-1] if ":" in symbol else symbol
    content = f"{display} Morning Levels — {date_str}"

    with open(png_path, "rb") as f:
        png_data = f.read()

    boundary = "----MorningLevelsBoundary1234"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="content"\r\n\r\n'
        f"{content}\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="levels.png"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode() + png_data + f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        webhook_url, data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status


def main():
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} <symbol> <levels_json> <price>", file=sys.stderr)
        sys.exit(1)

    symbol      = sys.argv[1]
    levels_path = sys.argv[2]
    price       = float(sys.argv[3])
    date_str    = datetime.date.today().strftime("%Y%m%d")

    with open(levels_path) as f:
        levels_data = json.load(f)

    levels = build_levels_from_json(levels_data, price)
    if not levels:
        print(f"WARNING: no levels within {RANGE_PTS} pts of {price} — skipping screenshot")
        sys.exit(0)

    bars = fetch_1h_bars()
    if not bars:
        print("ERROR: no bars returned from tradingview-mcp", file=sys.stderr)
        sys.exit(1)

    png_path = save_chart(symbol, bars, levels, price, date_str)
    print(f"Screenshot saved: {png_path}")

    env = load_env()
    webhook = env.get("DISCORD_LEVELS_WEBHOOK")
    if webhook:
        try:
            status = discord_post(webhook, png_path, symbol, date_str)
            print(f"Discord: HTTP {status}")
        except Exception as e:
            print(f"WARNING: Discord post failed: {e}", file=sys.stderr)
    else:
        print("WARNING: DISCORD_LEVELS_WEBHOOK not set in .env — skipping Discord post")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests — confirm they pass**

```bash
cd "/Users/trp/Library/CloudStorage/GoogleDrive-astha.tarun@gmail.com/My Drive/FifiBot/Projects/trading-morning-levels"
python3 -m pytest tests/test_screenshot_levels.py -v
```

Expected output:
```
tests/test_screenshot_levels.py::test_build_levels_returns_all_present_levels PASSED
tests/test_screenshot_levels.py::test_build_levels_filters_by_range PASSED
tests/test_screenshot_levels.py::test_build_levels_skips_none PASSED
tests/test_screenshot_levels.py::test_build_levels_correct_colors PASSED
tests/test_screenshot_levels.py::test_compute_y_range_extends_below_bars_for_levels PASSED
tests/test_screenshot_levels.py::test_compute_y_range_extends_above_bars_for_levels PASSED
tests/test_screenshot_levels.py::test_compute_y_range_uses_bar_range_when_no_extreme_levels PASSED
7 passed
```

- [ ] **Step 5: Smoke test chart render with mock data (no TV needed)**

```bash
cd "/Users/trp/Library/CloudStorage/GoogleDrive-astha.tarun@gmail.com/My Drive/FifiBot/Projects/trading-morning-levels"
python3 - <<'EOF'
import json, sys
sys.path.insert(0, ".")
from screenshot_levels import build_levels_from_json, save_chart

levels_data = {
    "daily": {"vah": 29400.0, "val": 29100.0, "poc": 29250.0, "sr": [29350.0]},
    "4h":    {"vah": 29300.0, "val": 29050.0, "poc": 29180.0, "sr": [29280.0]},
    "1h":    {"vah": 29200.0, "val": 28900.0, "poc": 29100.0, "sr": [29160.0]},
    "hvn":   [29220.0],
}
bars = [
    {"time": 1715000000 + i*3600, "open": 29100.0+i*5, "high": 29120.0+i*5,
     "low": 29080.0+i*5, "close": 29110.0+i*5, "volume": 40000}
    for i in range(20)
]
price = 29133.0
levels = build_levels_from_json(levels_data, price)
path = save_chart("CME_MINI:NQ1!", bars, levels, price, "20260510")
print("Saved:", path)
EOF
open /tmp/CME_MINI_NQ1__levels_20260510.png
```

Expected: Preview opens showing dark chart with level lines.

- [ ] **Step 6: Commit**

```bash
cd "/Users/trp/Library/CloudStorage/GoogleDrive-astha.tarun@gmail.com/My Drive/FifiBot/Projects/trading-morning-levels"
git add screenshot_levels.py tests/test_screenshot_levels.py
git commit -m "feat: add screenshot_levels.py — chart render + discord post"
```

---

### Task 2: Add Discord test + verify end-to-end

**Files:**
- Modify: `tests/test_screenshot_levels.py` (add discord mock test)

- [ ] **Step 1: Add Discord unit test to test file**

Append to `tests/test_screenshot_levels.py`:

```python
import tempfile
from unittest.mock import patch, MagicMock
from screenshot_levels import discord_post


def test_discord_post_sends_correct_multipart():
    # Write a tiny fake PNG to temp file
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(b"\x89PNG\r\n\x1a\nFAKE")
        png_path = f.name

    captured = {}

    class MockResponse:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): pass

    def fake_urlopen(req, timeout=None):
        captured["url"]          = req.full_url
        captured["content_type"] = req.get_header("Content-type")
        captured["body"]         = req.data
        return MockResponse()

    with patch("screenshot_levels.urllib.request.urlopen", side_effect=fake_urlopen):
        status = discord_post("https://discord.com/api/webhooks/fake/token",
                              png_path, "CME_MINI:NQ1!", "20260510")

    assert status == 200
    assert "discord.com" in captured["url"]
    assert "multipart/form-data" in captured["content_type"]
    assert b"NQ1!" in captured["body"]
    assert b"Morning Levels" in captured["body"]
    assert b"\x89PNG" in captured["body"]

    import os; os.unlink(png_path)
```

- [ ] **Step 2: Run — confirm new test passes**

```bash
cd "/Users/trp/Library/CloudStorage/GoogleDrive-astha.tarun@gmail.com/My Drive/FifiBot/Projects/trading-morning-levels"
python3 -m pytest tests/test_screenshot_levels.py -v
```

Expected: 8 passed.

- [ ] **Step 3: Commit**

```bash
git add tests/test_screenshot_levels.py
git commit -m "test: add discord_post mock test for screenshot_levels"
```

---

### Task 3: Wire screenshot into `run_levels.py`

**Files:**
- Modify: `run_levels.py`

Two changes:
1. Add `_screenshot_and_post()` helper + call it after `draw_levels()` for NQ/ES
2. Write `/tmp/morning_levels_success.json` after the symbol loop

- [ ] **Step 1: Add `SCREENSHOT_SYMS` constant and `_screenshot_and_post` helper**

In `run_levels.py`, find the helpers section (after line ~145, before the main block). Add after the `draw_levels` function definition:

```python
# Symbols for which to generate screenshots
SCREENSHOT_SYMS = {"CME_MINI:NQ1!", "CME_MINI:ES1!"}

def _screenshot_and_post(sym, levels_json, price):
    """Call screenshot_levels.py in a subprocess. Failure is non-fatal."""
    try:
        r = subprocess.run(
            ["python3", f"{SKILL}/screenshot_levels.py", sym, levels_json, str(price)],
            capture_output=True, text=True, timeout=60,
        )
        if r.returncode == 0:
            print(f"    Screenshot: {r.stdout.strip()}")
        else:
            print(f"    WARNING: screenshot failed: {r.stderr.strip()[:120]}")
    except Exception as e:
        print(f"    WARNING: screenshot error: {e}")
```

- [ ] **Step 2: Call `_screenshot_and_post` after `draw_levels(sym, flvl)` in the mini loop**

Find this block in `run_levels.py` (around line 213):
```python
        draw_levels(sym, flvl)

        # ── Copy levels to corresponding micro (no re-analysis) ───────────────
```

Add the screenshot call between `draw_levels` and the micro copy comment:
```python
        draw_levels(sym, flvl)

        # ── Screenshot + Discord post (NQ/ES only) ────────────────────────────
        if sym in SCREENSHOT_SYMS:
            _screenshot_and_post(sym, flvl, price)

        # ── Copy levels to corresponding micro (no re-analysis) ───────────────
```

- [ ] **Step 3: Write success JSON after the symbol loop**

Find this line near the end of `run_levels.py`:
```python
print(f"=== Done — {step}/{total_steps} symbols ===")
```

Add the success JSON write immediately before it:
```python
with open("/tmp/morning_levels_success.json", "w") as _sf:
    json.dump({
        "timestamp": datetime.datetime.now().isoformat(),
        "symbols": {s: "ok" for s in minis},
        "status": "ok",
    }, _sf, indent=2)
print("Success flag: /tmp/morning_levels_success.json")

print(f"=== Done — {step}/{total_steps} symbols ===")
```

Note: `json` and `datetime` are already imported at the top of `run_levels.py`.

- [ ] **Step 4: Verify the modified file is syntactically correct**

```bash
python3 -m py_compile "/Users/trp/Library/CloudStorage/GoogleDrive-astha.tarun@gmail.com/My Drive/FifiBot/Projects/trading-morning-levels/run_levels.py" && echo "OK"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
cd "/Users/trp/Library/CloudStorage/GoogleDrive-astha.tarun@gmail.com/My Drive/FifiBot/Projects/trading-morning-levels"
git add run_levels.py
git commit -m "feat: call screenshot_levels after draw; write success JSON"
```

---

### Task 4: Deploy to skill directory

The launchd job runs from `~/.claude/skills/trading-morning-levels/`. The Google Drive folder is source of truth. Copy changed files there.

- [ ] **Step 1: Copy new and modified files to skill directory**

```bash
SKILL=~/.claude/skills/trading-morning-levels
PROJ="/Users/trp/Library/CloudStorage/GoogleDrive-astha.tarun@gmail.com/My Drive/FifiBot/Projects/trading-morning-levels"

cp "$PROJ/screenshot_levels.py" "$SKILL/screenshot_levels.py"
cp "$PROJ/run_levels.py"        "$SKILL/run_levels.py"
cp "$PROJ/.env"                 "$SKILL/.env"
```

- [ ] **Step 2: Verify skill directory has all expected files**

```bash
ls -la ~/.claude/skills/trading-morning-levels/
```

Expected files present: `run_levels.py`, `screenshot_levels.py`, `analyze_levels.py`, `draw_levels.py`, `morning_levels.sh`, `.env`, `SKILL.md`

- [ ] **Step 3: Smoke test screenshot_levels.py from skill directory (no TV needed)**

```bash
python3 - <<'EOF'
import json, sys, os
sys.path.insert(0, os.path.expanduser("~/.claude/skills/trading-morning-levels"))
from screenshot_levels import build_levels_from_json, save_chart

levels_data = {
    "daily": {"vah": 29400.0, "val": 29100.0, "poc": 29250.0, "sr": [29350.0]},
    "4h":    {"vah": 29300.0, "val": 29050.0, "poc": 29180.0, "sr": [29280.0]},
    "1h":    {"vah": 29200.0, "val": 28900.0, "poc": 29100.0, "sr": [29160.0]},
    "hvn":   [29220.0],
}
bars = [
    {"time": 1715000000 + i*3600, "open": 29100.0+i*5, "high": 29120.0+i*5,
     "low": 29080.0+i*5, "close": 29110.0+i*5, "volume": 40000}
    for i in range(20)
]
price = 29133.0
levels = build_levels_from_json(levels_data, price)
path = save_chart("CME_MINI:NQ1!", bars, levels, price, "20260510")
print("OK:", path)
EOF
```

Expected: `OK: /tmp/CME_MINI_NQ1__levels_20260510.png`

- [ ] **Step 4: Commit**

```bash
cd "/Users/trp/Library/CloudStorage/GoogleDrive-astha.tarun@gmail.com/My Drive/FifiBot/Projects/trading-morning-levels"
git add .
git commit -m "chore: add .env and tests to project; update README"
```

---

## Done Criteria

- [ ] `python3 -m pytest tests/` → 8 passed
- [ ] `python3 screenshot_levels.py CME_MINI:NQ1! <levels.json> 29133` → saves PNG + posts to Discord
- [ ] Morning levels run → NQ + ES screenshots appear in `/tmp/` and Discord channel
- [ ] `cat /tmp/morning_levels_success.json` → `{"status": "ok", ...}`
