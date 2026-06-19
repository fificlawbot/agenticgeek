---
name: project-prop-consistency-goal
description: "NQ/ES backtester real goal — deterministic consistency to survive prop eval, not peak profit"
metadata: 
  node_type: memory
  type: project
  originSessionId: 46054513-c169-4df2-9981-51ecfc228a39
---

The objective for the nq-es-backtester / ORB work is **deterministic consistency for prop-firm automation**, NOT maximum profit.

**Why:** User's framing (2026-05-29): "would not make much sense to automate if we pass an eval in 7 days and then blow it in next 2 days. there has to be some determinism." Prop firms kill accounts via daily loss limit + trailing drawdown, so survival/consistency beats home-run PnL.

**How to apply:**
- Judge configs on drawdown, worst-day, daily-green%, and stability across regimes — not just net PnL. A lower-PnL config with bounded losses and no blow-up days is preferred.
- Prop-survival tools (hard daily loss cap, flat-after-target) are first-class, even if PnL-neutral.
- User is open to scaling INTO a trade to recover intra-trade drawdown — a technique to explore for the high-consistency design (not yet built/validated as of 2026-05-29).
- Be honest about WR ceilings: ~70-78% is realistic for automatable index-futures; 90%+ with positive EV is marketing. See [[feedback-model-delegation]] for how builds are split.

**Critical caveat learned 2026-05-29:** the single-profile `run_orb_v2.py` path historically did NOT apply `CANONICAL_PROFILE_OVERRIDES` (poc_skew filter for StrA/B), while the `--all-profiles`/apex/mfe paths DID. So `--canonical` meant two different things by path, and single-profile dollar figures were non-canonical (poc off → inflated drawdowns, understated PnL, Mar-May looked worse than reality). Always validate on the parity path or after the paths are unified. Verify current code state before trusting any historical single-profile number.
