---
name: feedback-tv-cdp
description: "Feedback on TV CDP automation — avoid JS .click() mass-close, use targeted clicks"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: a66e71a5-67a5-4ecf-aacf-16abd65faf99
---

Do NOT use `querySelectorAll('button').forEach(b => b.click())` to close dialogs — it triggers unintended actions (opens broker dialog, fires buttons behind overlays).

**Why:** Caused "Trade with your broker" dialog to repeatedly open and TV layout to break. Hard to recover from.

**How to apply:** For dialog dismissal, always use: (1) targeted click on specific Cancel/Close button by text/aria-label, or (2) Escape key via `Input.dispatchKeyEvent`. Never batch-click all close buttons via JS.

---

Slippage=1 and scaleout defaults should be baked into the Pine script itself, not set via TV Properties/Settings dialogs.

**Why:** User explicitly requested this to avoid dialog manipulation ("just have all our defaults and the values that we change inside the pine script itself").

**How to apply:** Always add `slippage = 1` to the `strategy()` declaration in Pine. Keep `scaleOutEnabled = input.bool(false, ...)` for baseline (scaleout=OFF).
