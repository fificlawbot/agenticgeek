import sys, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from screenshot_levels import build_levels_from_json, compute_y_range

MOCK_LEVELS = {
    "daily":  {"vah": 29400.0, "val": 29100.0, "poc": 29250.0, "sr": [29350.0]},
    "four_h": {"vah": 29300.0, "val": 29050.0, "poc": 29180.0, "sr": [29280.0]},
    "one_h":  {"vah": 29200.0, "val": 28900.0, "poc": 29100.0, "sr": [29160.0]},
    "hvn":    [29220.0],
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
    assert "D VAH"  in labels
    assert "D VAL"  in labels
    assert "D POC"  in labels
    assert "4H VAH" in labels
    assert "1H POC" in labels
    assert "HVN"    in labels
    assert "D S/R"  in labels


def test_build_levels_filters_by_range():
    price = 29200.0
    result = build_levels_from_json(MOCK_LEVELS, price, range_pts=50)
    for p, *_ in result:
        assert abs(p - price) <= 50


def test_build_levels_skips_none():
    data = {"daily": {"vah": None, "val": 29100.0, "poc": None, "sr": []},
            "four_h": {}, "one_h": {}, "hvn": []}
    result = build_levels_from_json(data, 29100.0, range_pts=500)
    labels = [r[1] for r in result]
    assert "D VAH" not in labels
    assert "D POC" not in labels
    assert "D VAL" in labels


def test_build_levels_correct_colors():
    result = build_levels_from_json(MOCK_LEVELS, 29200.0, range_pts=500)
    by_label = {r[1]: r for r in result}
    assert by_label["D POC"][2] == "#FF4444"
    assert by_label["D VAH"][2] == "#4488FF"
    assert by_label["D S/R"][2] == "#FFD700"
    assert by_label["HVN"][2]   == "#FFA500"


def test_compute_y_range_extends_below_bars_for_levels():
    bars = MOCK_BARS
    level_prices = [28500.0, 29300.0]
    y_min, y_max = compute_y_range(bars, level_prices, pad=50)
    assert y_min < 29080.0
    assert y_min <= 28500.0 - 50


def test_compute_y_range_extends_above_bars_for_levels():
    bars = MOCK_BARS
    level_prices = [29600.0, 29100.0]
    y_min, y_max = compute_y_range(bars, level_prices, pad=50)
    assert y_max >= 29600.0 + 50


def test_compute_y_range_uses_bar_range_when_no_extreme_levels():
    bars = MOCK_BARS
    level_prices = [29150.0]
    y_min, y_max = compute_y_range(bars, level_prices, pad=50)
    bar_low  = min(b["low"]  for b in bars)
    bar_high = max(b["high"] for b in bars)
    assert y_min == bar_low  - 50
    assert y_max == bar_high + 50


# ── Discord ───────────────────────────────────────────────────────────────────

from unittest.mock import patch
from screenshot_levels import discord_post


def test_discord_post_sends_correct_multipart():
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

    os.unlink(png_path)
