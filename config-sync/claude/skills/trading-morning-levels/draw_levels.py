#!/usr/bin/env python3
"""
Draw D / 4H / 1H VP + S/R levels on active TradingView chart.

Color scheme:
  Daily  : VAH/VAL = dark blue (#00008B) w=3 solid
           POC     = dark red  (#8B0000) w=3 solid
           S/R     = mustard   (#D4A017) w=2 solid
  4H     : VAH/VAL = dark blue (#00008B) w=2 solid
           POC     = dark red  (#8B0000) w=2 solid
           S/R     = mustard   (#D4A017) w=2 dashed
  1H     : VAH/VAL = med blue  (#5B8DB8) w=1 solid
           POC     = med red   (#C05050) w=1 solid
           S/R     = lt mustard(#FFD050) w=1 dashed

Usage: python3 draw_levels.py <levels.json>
"""

import os, sys, json, subprocess, time

T      = int(time.time())
levels = json.load(open(sys.argv[1]))
TV     = ["node", os.path.expanduser("~/tradingview-mcp/src/cli/index.js")]

total_drawn = [0]

def draw(price, color, width, ls, label):
    if price is None:
        return False
    ov  = json.dumps({"linecolor": color, "linewidth": width, "linestyle": ls})
    cmd = TV + ["draw", "shape", "-t", "horizontal_line",
                "--time", str(T), "-p", str(price),
                "--overrides", ov, "--text", label]
    r   = subprocess.run(cmd, capture_output=True, text=True)
    out = json.loads(r.stdout) if r.stdout.strip() else {}
    if out.get("success"):
        total_drawn[0] += 1
        return True
    print(f"  WARN {label}@{price}: {r.stderr.strip()[:80]}", file=sys.stderr)
    return False

# Per-TF dedup (only skip true duplicates within same TF, tol=5)
# Cross-TF: each TF draws its own VP regardless of proximity
# S/R: dedup across all drawn levels (tol=15) to avoid clutter

drawn_d  = set()   # daily VP prices
drawn_fh = set()   # 4H VP prices
drawn_1h = set()   # 1H VP prices
drawn_sr = set()   # all S/R prices

INTRA    = 5   # within-TF VP dedup (true duplicates only)
SR_SELF  = 15  # S/R vs other S/R (same type)
SR_VP    = 8   # S/R vs VP lines (allow drawing if >8pts apart even if VP nearby)

def near(price, s, tol):
    return any(abs(price - p) < tol for p in s)

def draw_vp(price, color, w, ls, label, drawn_set):
    if price is None or near(price, drawn_set, INTRA):
        return
    if draw(price, color, w, ls, label):
        drawn_set.add(price)

def draw_sr(price, color, w, ls, label):
    if price is None:
        return
    # Skip if too close to another S/R line (prevents stacking same-type lines)
    if near(price, drawn_sr, SR_SELF):
        return
    # Skip if extremely close to a VP line (true duplicate, not just nearby)
    all_vp = drawn_d | drawn_fh | drawn_1h
    if near(price, all_vp, SR_VP):
        return
    if draw(price, color, w, ls, label):
        drawn_sr.add(price)

d  = levels["daily"]
fh = levels["four_h"]
h1 = levels["one_h"]

# ── Daily VP ──────────────────────────────────────────────────────────────────
draw_vp(d.get("vah"), "#00008B", 3, 0, "D VAH", drawn_d)
draw_vp(d.get("val"), "#00008B", 3, 0, "D VAL", drawn_d)
draw_vp(d.get("poc"), "#8B0000", 3, 0, "D POC", drawn_d)

# ── Daily S/R ─────────────────────────────────────────────────────────────────
for p in d.get("sr", []):
    draw_sr(p, "#D4A017", 2, 0, "D S/R")

# ── 4H VP ─────────────────────────────────────────────────────────────────────
draw_vp(fh.get("vah"), "#00008B", 2, 0, "4H VAH", drawn_fh)
draw_vp(fh.get("val"), "#00008B", 2, 0, "4H VAL", drawn_fh)
draw_vp(fh.get("poc"), "#8B0000", 2, 0, "4H POC", drawn_fh)

# ── 4H S/R ───────────────────────────────────────────────────────────────────
for p in fh.get("sr", []):
    draw_sr(p, "#D4A017", 2, 1, "4H S/R")

# ── 1H VP ─────────────────────────────────────────────────────────────────────
draw_vp(h1.get("vah"), "#5B8DB8", 1, 0, "1H VAH", drawn_1h)
draw_vp(h1.get("val"), "#5B8DB8", 1, 0, "1H VAL", drawn_1h)
draw_vp(h1.get("poc"), "#C05050", 1, 0, "1H POC", drawn_1h)

# ── 1H S/R ───────────────────────────────────────────────────────────────────
for p in h1.get("sr", []):
    draw_sr(p, "#FFD050", 1, 1, "1H S/R")

# ── HVN shelves (orange, dashed, width=2) ────────────────────────────────────
for p in levels.get("hvn", []):
    draw_sr(p, "#FF8C00", 2, 1, "HVN")

# ── Asia session range (purple, solid, width=2, no dedup) ────────────────────
# 18:00 ET prior day → 03:00 ET today. Anchors for overnight high/low.
asia = levels.get("asia", {})
draw(asia.get("hi"), "#800080", 2, 0, "Asia Hi")
draw(asia.get("lo"), "#800080", 2, 0, "Asia Lo")

# ── London session range (teal, solid, width=2, no dedup) ────────────────────
# 03:00 ET → 09:30 ET today. Partial when the run fires before 09:30.
lon = levels.get("london", {})
draw(lon.get("hi"), "#008080", 2, 0, "Lon Hi")
draw(lon.get("lo"), "#008080", 2, 0, "Lon Lo")

print(f"Drew {total_drawn[0]} levels.")
