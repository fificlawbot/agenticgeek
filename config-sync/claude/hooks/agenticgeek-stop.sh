#!/bin/bash
# Stop hook: trigger session-handoff if work is done and not waiting for user input.
# Logic:
#   - AskUserQuestion in last assistant turn → user needs to respond → allow stop (no handoff)
#   - Work complete, no pending question → inject session-handoff request
#   - Lockfile (session-keyed) prevents double-trigger after handoff runs

INPUT=$(cat)

SESSION_ID=$(echo "$INPUT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('session_id',''))" 2>/dev/null || echo "")
TRANSCRIPT_PATH=$(echo "$INPUT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('transcript_path',''))" 2>/dev/null || echo "")

LOCKFILE="/tmp/agenticgeek_handoff_${SESSION_ID:-unknown}"

# Lockfile set means we just triggered handoff last turn — allow clean stop now
if [[ -f "$LOCKFILE" ]]; then
  rm -f "$LOCKFILE"
  echo '{"continue": true}'
  exit 0
fi

# No transcript — allow stop
if [[ -z "$TRANSCRIPT_PATH" || ! -f "$TRANSCRIPT_PATH" ]]; then
  echo '{"continue": true}'
  exit 0
fi

# Inspect last assistant turn
DECISION=$(python3 - "$TRANSCRIPT_PATH" <<'PYEOF'
import json, sys

try:
    lines = []
    with open(sys.argv[1]) as f:
        for line in f:
            s = line.strip()
            if s:
                try:
                    lines.append(json.loads(s))
                except Exception:
                    pass

    # Find last assistant entry
    last = None
    for entry in reversed(lines):
        if entry.get('type') == 'assistant':
            last = entry
            break

    if not last:
        print("allow")
        sys.exit()

    content = last.get('message', {}).get('content', [])
    if not isinstance(content, list):
        print("allow")
        sys.exit()

    # AskUserQuestion in last turn = Claude is waiting for user response
    for block in content:
        if isinstance(block, dict) and block.get('type') == 'tool_use':
            if block.get('name') == 'AskUserQuestion':
                print("waiting")
                sys.exit()

    print("handoff")

except Exception:
    print("allow")
PYEOF
)

case "$DECISION" in
  waiting)
    # Claude asked a question — user must respond first, skip handoff
    echo '{"continue": true}'
    ;;
  handoff)
    # Work complete, not waiting for input — trigger session-handoff
    touch "$LOCKFILE"
    echo '{"continue": false, "reason": "Session work complete. Invoke the session-handoff skill now to save current session state before stopping."}'
    ;;
  *)
    echo '{"continue": true}'
    ;;
esac
