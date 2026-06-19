#!/usr/bin/env python3
"""
VP + HVN + S/R levels for Daily, 4H, Session (1H) timeframes.
Replicates kv4coins VP indicator (68% VA, fixed lookback, dynamic buckets).

Key fixes:
- 1H VP = TODAY's session bars only (not 100-bar lookback which goes 4 days back)
- HVN detection = high-volume shelves > 1.5x mean bucket volume
- Smart dedup = priority-based (higher-priority level wins when too close)

Usage:
    python3 analyze_levels.py <current_price> <range_pts> \
        <1h_bars.json> <4h_bars.json> <daily_bars.json>
"""

import sys, json, datetime

try:
    from zoneinfo import ZoneInfo  # stdlib on Python 3.9+
except ImportError:
    ZoneInfo = None

current_price = float(sys.argv[1])
range_pts     = float(sys.argv[2])
range_low     = current_price - range_pts
range_high    = current_price + range_pts

bars_1h    = json.load(open(sys.argv[3]))
bars_4h    = json.load(open(sys.argv[4]))
bars_daily = json.load(open(sys.argv[5]))

# Sort ascending
bars_1h.sort(key=lambda b: b['time'])
bars_4h.sort(key=lambda b: b['time'])
bars_daily.sort(key=lambda b: b['time'])

# ── VP constants (matches kv4coins indicator) ─────────────────────────────────
VP_NUM_BARS    = 200
VP_PCT         = 0.68   # in_12 = 68%
LOOKBACK_4H    = 12     # ~2 trading days of 4H bars (keeps VAL inside ±1000 range)
LOOKBACK_DAILY = 10     # ~2 weeks of daily bars

# ── HVN threshold ─────────────────────────────────────────────────────────────
HVN_THRESHOLD  = 2.0    # bucket vol > 2.0x mean → significant HVN shelf

# ── Dedup / S/R ───────────────────────────────────────────────────────────────
SWING_LB = 2
DEDUP    = 40           # min distance between levels — keeps spacing clean

# ─────────────────────────────────────────────────────────────────────────────

def calculate_vp(bars, lookback, num_bars=VP_NUM_BARS, pct=VP_PCT):
    """Exact replication of kv4coins Pine Script VP algorithm."""
    bars = bars[-lookback:] if len(bars) > lookback else bars
    if not bars:
        return None, None, None, [], []
    highest = max(b['high'] for b in bars)
    lowest  = min(b['low']  for b in bars)
    if highest == lowest:
        return lowest, lowest, lowest, [], []
    pi   = (highest - lowest) / (num_bars - 1)
    vols = [0.0] * num_bars

    for b in bars:
        for j in range(num_bars):
            pl = lowest + pi * j
            if b['low'] <= pl < b['high']:
                vols[j] += b['volume']

    max_vol = max(vols)
    max_idx = vols.index(max_vol)
    poc     = round(lowest + pi * max_idx, 2)

    # Value area expansion from POC
    total  = sum(vols)
    target = total * pct
    va_up  = va_dn = max_idx
    va_sum = max_vol
    while va_sum < target:
        vu = vols[va_up + 1] if va_up < num_bars - 1 else 0
        vd = vols[va_dn - 1] if va_dn > 0            else 0
        if vu == 0 and vd == 0: break
        if vu >= vd: va_up  += 1; va_sum += vu
        else:        va_dn  -= 1; va_sum += vd

    vah = round(lowest + pi * va_up, 2)
    val = round(lowest + pi * va_dn, 2)

    # HVN detection: buckets significantly above average
    active = [v for v in vols if v > 0]
    mean_v = sum(active) / len(active) if active else 0
    hvns   = []
    if mean_v > 0:
        # Cluster adjacent high-vol buckets into single shelf price
        in_hvn = False
        hvn_prices, hvn_vols = [], []
        for j, v in enumerate(vols):
            price = lowest + pi * j
            if v >= HVN_THRESHOLD * mean_v:
                hvn_prices.append(price)
                hvn_vols.append(v)
                in_hvn = True
            else:
                if in_hvn and hvn_prices:
                    # Take volume-weighted center of cluster
                    total_v = sum(hvn_vols)
                    center  = sum(p * v for p, v in zip(hvn_prices, hvn_vols)) / total_v
                    hvns.append((round(center, 2), total_v))
                    hvn_prices, hvn_vols = [], []
                in_hvn = False
        if in_hvn and hvn_prices:
            total_v = sum(hvn_vols)
            center  = sum(p * v for p, v in zip(hvn_prices, hvn_vols)) / total_v
            hvns.append((round(center, 2), total_v))

    return poc, val, vah, hvns, vols

# ── Today's session bars for 1H VP ───────────────────────────────────────────
# NQ futures session: Sunday 6 PM ET = Monday 22:00 UTC
# Use current session start (22:00 UTC of previous day, or today if past 22:00)
now_utc = datetime.datetime.now(datetime.timezone.utc)
session_start = now_utc.replace(hour=22, minute=0, second=0, microsecond=0)
if now_utc.hour < 22:
    session_start -= datetime.timedelta(days=1)
session_ts = int(session_start.timestamp())

session_bars = [b for b in bars_1h if b['time'] >= session_ts]

# Fallback: if today's session has < 4 bars (pre-market early run),
# use last 20 1H bars (overnight + prev day close) as session proxy
if len(session_bars) < 4:
    session_bars = bars_1h[-20:] if len(bars_1h) >= 20 else bars_1h

# ── Calculate VP ──────────────────────────────────────────────────────────────
d_poc,  d_val,  d_vah,  d_hvns,  _  = calculate_vp(bars_daily, LOOKBACK_DAILY)
fh_poc, fh_val, fh_vah, fh_hvns, _  = calculate_vp(bars_4h,    LOOKBACK_4H)
s_poc,  s_val,  s_vah,  s_hvns,  _  = calculate_vp(session_bars, len(session_bars))
# HVN: run on full 1H dataset for broader shelf detection (not just session)
_, _, _, h1_hvns, _                  = calculate_vp(bars_1h, min(100, len(bars_1h)))

print(f"  Session bars used for 1H VP: {len(session_bars)} bars "
      f"(from {datetime.datetime.fromtimestamp(session_bars[0]['time'], tz=datetime.timezone.utc).strftime('%m/%d %H:%M')} UTC)",
      file=sys.stderr)

# ── Swing S/R ─────────────────────────────────────────────────────────────────
def swing_sr(bars, lb=SWING_LB):
    highs, lows = [], []
    for i in range(lb, len(bars) - lb):
        wh = [bars[j]['high'] for j in range(i - lb, i + lb + 1)]
        wl = [bars[j]['low']  for j in range(i - lb, i + lb + 1)]
        if bars[i]['high'] == max(wh): highs.append(round(bars[i]['high'], 2))
        if bars[i]['low']  == min(wl): lows.append(round(bars[i]['low'],  2))
    return highs, lows

def in_range(p):
    return p is not None and range_low <= p <= range_high

def dedup_list(levels, tol=DEDUP):
    result = []
    for lv in sorted(set(levels)):
        if in_range(lv) and (not result or abs(lv - result[-1]) > tol):
            result.append(lv)
    return result

# Per-TF swing S/R (each with own lookback for appropriate granularity)
d_sh,  d_sl  = swing_sr(bars_daily, lb=1)          # daily swing pivots
fh_sh, fh_sl = swing_sr(bars_4h,   lb=2)          # 4H swing pivots
h1_sh, h1_sl = swing_sr(bars_1h,   lb=5)          # 1H swing pivots (lb=5 = more selective)

# Wide-bar detection: high-vol, wide-range bars — their lows/highs are key S/R
# A bar is "wide" if range > 1.5x avg AND volume > 1.5x avg
# These are missed by swing detector (no pivot shape) but act as VP shelves
def wide_bar_sr(bar_list, range_mult=1.5, vol_mult=1.5):
    if len(bar_list) < 5:
        return [], []
    ranges = sorted(b['high'] - b['low'] for b in bar_list)
    # Use MEDIAN range — robust against outlier wide bars inflating the average
    avg_range = ranges[len(ranges) // 2]
    avg_vol   = sum(b['volume'] for b in bar_list) / len(bar_list)
    highs, lows = [], []
    for b in bar_list:
        if (b['high'] - b['low']) > range_mult * avg_range and b['volume'] > vol_mult * avg_vol:
            highs.append(round(b['high'], 2))
            lows.append(round(b['low'], 2))
    return highs, lows

# Restrict wide-bar to recent 20 1H bars (last ~2 days) to avoid per-day RTH open noise
wb_h1_h, wb_h1_l = wide_bar_sr(bars_1h[-20:], range_mult=1.0, vol_mult=1.3)
wb_4h_h, wb_4h_l = wide_bar_sr(bars_4h[-12:], range_mult=1.0, vol_mult=1.3)

d_sr_raw  = dedup_list(d_sh  + d_sl)
fh_sr_raw = dedup_list(fh_sh + fh_sl + wb_4h_h + wb_4h_l)
h1_sr_raw = dedup_list(h1_sh + h1_sl + wb_h1_h + wb_h1_l)

# ── Priority-based dedup across ALL levels ────────────────────────────────────
# Priority: Daily VP=5, 4H VP=4, Session VP=4, HVN=3, S/R=2
# When two levels within DEDUP, keep higher priority

class Level:
    def __init__(self, price, priority, label, vol=0):
        self.price    = price
        self.priority = priority
        self.label    = label
        self.vol      = vol

    def __repr__(self):
        return f"Level({self.price}, p={self.priority}, {self.label})"

candidates = []
for p, label, pri in [
    (d_vah,  "D VAH",  5), (d_val,  "D VAL",  5), (d_poc,  "D POC",  5),
    (fh_vah, "4H VAH", 4), (fh_val, "4H VAL", 4), (fh_poc, "4H POC", 4),
    (s_vah,  "1H VAH", 4), (s_val,  "1H VAL", 4), (s_poc,  "1H POC", 4),
]:
    if p is not None:  # VP levels never range-filtered; draw_levels.py handles that
        candidates.append(Level(p, pri, label))

for price, vol in d_hvns + fh_hvns + s_hvns + h1_hvns:
    if in_range(price):
        candidates.append(Level(price, 3, "HVN", vol=vol))

# NOTE: S/R levels are NOT added to candidates / resolve()
# They're output directly per-TF and draw_levels.py handles their dedup
# This prevents VP levels from silently dropping S/R via priority resolution

# Sort by price, then resolve conflicts by priority
candidates.sort(key=lambda l: l.price)

def resolve(levels, tol=DEDUP):
    """Keep higher-priority level when two are within tol."""
    if not levels: return []
    result = [levels[0]]
    for lv in levels[1:]:
        prev = result[-1]
        if abs(lv.price - prev.price) < tol:
            # Keep higher priority; tie-break: keep lower price for support, higher for resistance
            if lv.priority > prev.priority:
                result[-1] = lv
            # else keep prev (already higher or equal priority)
        else:
            result.append(lv)
    return result

resolved = resolve(candidates, tol=DEDUP)

# Separate back into categories for drawing
def get_levels(resolved, labels):
    return [l for l in resolved if l.label in labels]

d_levels   = get_levels(resolved, {"D VAH", "D VAL", "D POC"})
fh_levels  = get_levels(resolved, {"4H VAH", "4H VAL", "4H POC"})
s_levels   = get_levels(resolved, {"1H VAH", "1H VAL", "1H POC"})
hvn_levels = get_levels(resolved, {"HVN"})
# S/R output directly from raw deduped lists (not filtered by resolve)
# draw_levels.py handles final dedup vs VP lines

def fmt(level_list):
    return {l.label: l.price for l in level_list}

def sr_prices(level_list):
    return [l.price for l in level_list]

# ── Output ────────────────────────────────────────────────────────────────────
output = {
    "current_price": current_price,
    "range": {"low": range_low, "high": range_high},
    "session_bars": len(session_bars),
    "daily": {
        "vah": next((l.price for l in d_levels if l.label == "D VAH"), None),
        "val": next((l.price for l in d_levels if l.label == "D VAL"), None),
        "poc": next((l.price for l in d_levels if l.label == "D POC"), None),
        "sr":  d_sr_raw,
    },
    "four_h": {
        "vah": next((l.price for l in fh_levels if l.label == "4H VAH"), None),
        "val": next((l.price for l in fh_levels if l.label == "4H VAL"), None),
        "poc": next((l.price for l in fh_levels if l.label == "4H POC"), None),
        "sr":  fh_sr_raw,
    },
    "one_h": {
        "vah": next((l.price for l in s_levels if l.label == "1H VAH"), None),
        "val": next((l.price for l in s_levels if l.label == "1H VAL"), None),
        "poc": next((l.price for l in s_levels if l.label == "1H POC"), None),
        "sr":  h1_sr_raw,
    },
    "hvn": sr_prices(hvn_levels),
}

# ── Session high/low (Asia 18:00–03:00 ET, London 03:00–09:30 ET) ────────────
def compute_session_levels(bars):
    empty = {"asia": {"hi": None, "lo": None}, "london": {"hi": None, "lo": None}}
    if not bars or ZoneInfo is None:
        return empty
    ET = ZoneInfo("America/New_York")
    now_et = datetime.datetime.now(ET)
    today = now_et.date()
    yday  = today - datetime.timedelta(days=1)

    def ts(d, h, m=0):
        return int(datetime.datetime(d.year, d.month, d.day, h, m, tzinfo=ET).timestamp())

    windows = {
        "asia":   (ts(yday, 18),  ts(today, 3)),
        "london": (ts(today, 3),  ts(today, 9, 30)),
    }
    out = {}
    for name, (start, end) in windows.items():
        in_win = [b for b in bars if start <= b["time"] < end]
        out[name] = ({"hi": max(b["high"] for b in in_win),
                      "lo": min(b["low"]  for b in in_win)}
                     if in_win else {"hi": None, "lo": None})
    return out

session_hl = compute_session_levels(bars_1h)
output["asia"]   = session_hl["asia"]
output["london"] = session_hl["london"]

print(json.dumps(output, indent=2))
