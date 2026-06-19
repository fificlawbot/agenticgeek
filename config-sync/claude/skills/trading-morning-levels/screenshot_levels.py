#!/usr/bin/env python3
"""
screenshot_levels.py <symbol> <levels_json_path> <price>

Renders clean 1H candlestick chart + level lines via mplfinance, saves PNG
to /tmp/, and posts to Discord (DISCORD_LEVELS_WEBHOOK in .env).

Reads 1H bars from bars_<safe_symbol>_1h.json cached by run_levels.py.
No TradingView / tradingview-mcp connection required at screenshot time.
"""

import sys, os, json, datetime, urllib.request
from pathlib import Path
import pandas as pd
import mplfinance as mpf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SKILL = os.path.dirname(os.path.abspath(__file__))

RANGE_PTS = 500
BAR_PAD   = 50


def load_env():
    """Read config from os.environ (set by morning_levels.sh from project .env)."""
    return os.environ


def build_levels_from_json(data, current_price, range_pts=RANGE_PTS):
    """
    Returns list of (price, label, color, linewidth, linestyle).
    Skips None prices. Filters to within range_pts of current_price.
    """
    entries = []
    for key, prefix in [("daily", "D"), ("four_h", "4H"), ("one_h", "1H")]:
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
    # Asia / London session high-low — brighter shades for the dark PNG bg.
    asia = data.get("asia", {})
    if asia.get("hi") is not None:
        entries.append((asia["hi"], "Asia Hi", "#C766FF", 2, "-"))
    if asia.get("lo") is not None:
        entries.append((asia["lo"], "Asia Lo", "#C766FF", 2, "-"))
    lon = data.get("london", {})
    if lon.get("hi") is not None:
        entries.append((lon["hi"], "Lon Hi",  "#33D4D4", 2, "-"))
    if lon.get("lo") is not None:
        entries.append((lon["lo"], "Lon Lo",  "#33D4D4", 2, "-"))
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


def check_success_flag(symbol):
    """Return True if run_levels.py marked this symbol as successfully drawn."""
    path = "/tmp/morning_levels_success.json"
    try:
        data = json.loads(open(path).read())
        return data.get(symbol, {}).get("status") == "ok"
    except Exception:
        return False


def load_1h_bars(symbol):
    """Load 1H bars cached by run_levels.py. No TradingView connection needed."""
    safe = symbol.replace(":", "_").replace("/", "_")
    path = f"{SKILL}/bars_{safe}_1h.json"
    with open(path) as f:
        bars = json.load(f)
    return bars[-30:]  # last 30 bars ≈ 1.5 trading days


def dedup_display_levels(levels, min_gap=25):
    """
    Remove levels too close together for clear chart display.
    When two levels within min_gap pts, keep higher linewidth (VP > S/R).
    """
    sorted_levels = sorted(levels, key=lambda x: x[0])
    result = []
    for level in sorted_levels:
        price, label, color, lw, ls = level
        if not result:
            result.append(level)
            continue
        prev = result[-1]
        if abs(price - prev[0]) < min_gap:
            if lw > prev[3]:
                result[-1] = level
        else:
            result.append(level)
    return result


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

    levels = dedup_display_levels(levels)
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
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "DiscordBot (morning-levels, 1.0)",
        },
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

    try:
        bars = load_1h_bars(symbol)
    except FileNotFoundError as e:
        print(f"ERROR: cached 1H bars missing for {symbol} — was run_levels.py run today? ({e})", file=sys.stderr)
        sys.exit(1)
    if not bars:
        print(f"ERROR: cached 1H bars file is empty for {symbol}", file=sys.stderr)
        sys.exit(1)

    png_path = save_chart(symbol, bars, levels, price, date_str)
    print(f"Screenshot saved: {png_path}")

    env = load_env()
    webhook = env.get("DISCORD_LEVELS_WEBHOOK")
    if not webhook:
        print("WARNING: DISCORD_LEVELS_WEBHOOK not set in .env — skipping Discord post")
    elif not check_success_flag(symbol):
        print(f"WARNING: no success flag for {symbol} in /tmp/morning_levels_success.json — skipping Discord post")
    else:
        try:
            status = discord_post(webhook, png_path, symbol, date_str)
            print(f"Discord: HTTP {status}")
        except Exception as e:
            print(f"WARNING: Discord post failed: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
