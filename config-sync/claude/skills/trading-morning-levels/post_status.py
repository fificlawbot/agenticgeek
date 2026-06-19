#!/usr/bin/env python3
"""
post_status.py [start_epoch]

Posts a compact run summary to DISCORD_STATUS_WEBHOOK after morning_levels.sh
completes. Reads /tmp/morning_levels_success.json + tail of morning_levels.log
to build the message. Always posts (success or failure) so silence means the
job never ran.

If DISCORD_STATUS_WEBHOOK is unset/empty, prints the message to stdout and exits 0.
Pass a unix epoch as argv[1] for runtime measurement; otherwise runtime is omitted.
"""

import os, sys, json, datetime, re, urllib.request

SKILL = os.path.dirname(os.path.abspath(__file__))
SUCCESS_FLAG = "/tmp/morning_levels_success.json"
LOG_PATH = f"{SKILL}/morning_levels.log"

EXPECTED_MINIS  = ["CME_MINI:NQ1!", "CME_MINI:ES1!", "COMEX:GC1!"]
EXPECTED_MICROS = ["CME_MINI:MNQ1!", "CME_MINI:MES1!", "COMEX_MINI:MGC1!"]
SCREENSHOT_SYMS = {"CME_MINI:NQ1!", "CME_MINI:ES1!"}
MICRO_OF = {
    "CME_MINI:NQ1!": "CME_MINI:MNQ1!",
    "CME_MINI:ES1!": "CME_MINI:MES1!",
    "COMEX:GC1!":    "COMEX_MINI:MGC1!",
}


def short(sym):
    return sym.split(":")[-1] if ":" in sym else sym


def parse_run_tail(log_path, max_lines=400):
    """Return only the lines belonging to the most recent run (since the last header banner)."""
    try:
        with open(log_path, "r", errors="replace") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return []
    tail = lines[-max_lines:] if len(lines) > max_lines else lines
    last_header = 0
    for i, ln in enumerate(tail):
        if ln.startswith("Morning Levels —"):
            last_header = i
    return tail[last_header:]


def extract_drew_counts(run_lines):
    """Parse 'Drew N levels.' lines per symbol. Returns {symbol: int}."""
    counts = {}
    current = None
    sym_re = re.compile(r"^\[\d+/\d+\]\s+(\S+)")
    drew_re = re.compile(r"Drew\s+(\d+)\s+levels")
    for ln in run_lines:
        m = sym_re.match(ln)
        if m:
            current = m.group(1)
            continue
        m = drew_re.search(ln)
        if m and current:
            counts[current] = int(m.group(1))
    return counts


def extract_screenshot_status(run_lines):
    """Returns {symbol: 'posted'|'failed'} for symbols that attempted screenshot."""
    result = {}
    current = None
    sym_re = re.compile(r"^\[\d+/\d+\]\s+(\S+)")
    for ln in run_lines:
        m = sym_re.match(ln)
        if m:
            current = m.group(1)
            continue
        if current and current in SCREENSHOT_SYMS:
            if "Discord: HTTP 200" in ln:
                result[current] = "posted"
            elif "Discord: HTTP" in ln or "screenshot exited" in ln or "Discord post failed" in ln:
                result[current] = "failed"
    return result


def fmt_runtime(seconds):
    if seconds is None:
        return None
    m, s = divmod(int(seconds), 60)
    return f"{m}m {s:02d}s"


def build_message():
    success = {}
    if os.path.exists(SUCCESS_FLAG):
        try:
            success = json.loads(open(SUCCESS_FLAG).read())
        except Exception:
            success = {}

    run_lines = parse_run_tail(LOG_PATH)
    drew      = extract_drew_counts(run_lines)
    posted    = extract_screenshot_status(run_lines)

    today = datetime.date.today().strftime("%a %b %-d, %Y")
    fatal = any("Aborting" in ln or "ERROR:" in ln for ln in run_lines)

    drew_ok    = sum(1 for s in EXPECTED_MINIS + EXPECTED_MICROS if s in drew)
    expected   = len(EXPECTED_MINIS) + len(EXPECTED_MICROS)
    minis_ok   = sum(1 for s in EXPECTED_MINIS  if success.get(s, {}).get("status") == "ok")
    done_flag  = success.get("__done__", {}).get("status") == "ok"
    overall_ok = (minis_ok == len(EXPECTED_MINIS)) and done_flag and drew_ok == expected and not fatal

    icon = "🟢" if overall_ok else "🔴"
    header = f"{icon} Morning Levels — {today}"
    counts_line = f"{drew_ok}/{expected} symbols drew"

    body = []
    for mini in EXPECTED_MINIS:
        n = drew.get(mini)
        line = f"{short(mini):<4} {f'{n} levels' if n is not None else '✗ not drawn'}"
        if mini in SCREENSHOT_SYMS:
            tag = posted.get(mini)
            if tag == "posted":
                line += "  📤 posted"
            elif tag == "failed":
                line += "  ⚠️ post failed"
            else:
                line += "  ⚠️ no screenshot"
        body.append(line)
        micro = MICRO_OF.get(mini)
        mn = drew.get(micro)
        body.append(f"{short(micro):<4} {f'{mn} (copy)' if mn is not None else '✗ not drawn'}")

    runtime = None
    if len(sys.argv) > 1:
        try:
            runtime = fmt_runtime(int(sys.argv[1]))
        except ValueError:
            runtime = None
    if runtime:
        body.append(f"Runtime: {runtime}")

    return "\n".join([header, counts_line, *body])


def post_to_discord(webhook_url, content):
    body = json.dumps({"content": content}).encode()
    req = urllib.request.Request(
        webhook_url, data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "DiscordBot (morning-levels-status, 1.0)",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.status


def main():
    msg = build_message()
    webhook = os.environ.get("DISCORD_STATUS_WEBHOOK", "").strip()
    if not webhook:
        print("DISCORD_STATUS_WEBHOOK not set — skipping post. Message would have been:")
        print(msg)
        return 0
    try:
        status = post_to_discord(webhook, msg)
        print(f"Status posted to Discord: HTTP {status}")
    except Exception as e:
        print(f"WARNING: status post failed: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
