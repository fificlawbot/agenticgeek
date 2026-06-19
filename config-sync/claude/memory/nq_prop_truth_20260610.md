---
name: nq-prop-truth-20260610
description: "NQ PROP prop-firm state — TV-parity engine, BALANCED lock (qty 2/2/3, cap $1000, StrB nearest OFF, risk guard), PROP_HALF funded preset, ~36%/attempt eval"
metadata:
  type: project
  originSessionId: 2a72709f-6392-49f6-972f-c7728ff23939
---

# NQ Prop Truth State

**Branch/Context:** `fificlawbot/nq-es-backtester`, branch `exp/prop-truth-20260609` @ 2fcee4a (pushed). main @ e473efc has cherry-picked safe fixes (TradersPost JSON, exit_all→exit). Clone at `~/projects/nq-es-backtester`.
**Last updated:** 2026-06-12

## Current State
All technical work complete and committed. Waiting on user to confirm TradersPost parses fill webhooks as valid JSON on next live session → then merge branch to main.

## Completed (most recent first)
- 06-12: FINAL BALANCED lock (c1de797/e97ddbb/2fcee4a) — PROP preset: qty 2/2/3, all-out TP A=.75R/B=.50R/C=.75R, cap $1000, StrB skip_if_no_nearest_level OFF (16-combo ablation: all-filters-on ranked LAST), downsize risk guard (committed-open-risk; qty = floor(remaining_budget / per-contract entry→stop risk); blocks concurrency stacking). NEW PROP_HALF preset (funded): 1/1/2, cap $500 — budget must scale with size (half book on full budget = 44%-blown trap).
- 06-12: Pass-rate semantics correction (2fcee4a) — MC "Pass%" = within-5-attempts NOT per-attempt. True: ~36%/attempt, median 2 attempts, 89.6% within 5.
- 06-12: Pine zero-trades bug fixed (9c2d9a5) — `for 0 to strategy.opentrades-1` on empty book = silent runtime halt; gated + nz() stops. TV floors verified: −$1,030 full / −$556 half.
- 06-11: Two-phase MC under REAL Apex rules (e754047, docs/prop_playbook.md) — no DLL-fail exists; EOD-variant DLL only pauses. Day-triple bootstrap → eval sim + PA survival sim.
- 06-10: Engine parity −2.9% vs TV over 2.25yr (4 fixes: same-bar TP fill, intra-day re-entry, opposing gate, cap projection). Full-history TV exports reconciled.

## Key Data
- Final numbers (10k iters, exact frames, Apex EOD 50K): eval ~36%/attempt, 89.6% funded ≤5 attempts; funded 21.3% blown 120d, 80.4% ≥1 payout, E[$3,043]/120d.
- Day floors (TV-verified): −$1,030 full PROP / −$556 PROP_HALF. Python exact: −$996 / −$497.
- Sizing journey: eval PROP → funded PROP_HALF → trail locks +$100 (peak ≥ $52,600) → PROP. Dynamic sizing = downsize-only.
- Buy: EOD Drawdown 50K ($2k EOD-recalc, $1k DLL pauses not fails). NOT Intraday Trailing.
- PROP_HALF as eval config ≈5.5%/attempt — funded survival only, can't pass eval.
- Parquet: data/market_data/MNQ/1m/MNQ_1m.parquet — 814,075 rows, 2024-01-01→2026-06-10.

## Files Changed (recent)
- `pinescript/tradersarc_orb_v3.pine` — PROP/PROP_HALF presets, risk guard block, exit_all→exit, empty-book gate
- `scripts/run_orb_v2.py` — PROP_* constants, apply_risk_guard(committed), apply_opposing_gate, PROP_FILTER_OVERRIDES
- `scripts/mc_sim.py` — PROP leg = locked fixed-R all-out, risk guard default on, --filters truth/legacy
- `.tmp/day_equity_paths.py` + `.tmp/prop_two_phase_mc.py` — two-phase MC tooling; frames `.tmp/prop_day_paths_{full,half}.parquet`
- `docs/prop_playbook.md` — playbook v1 + v2 addendum + pass-semantics correction

## Known Issues / Decisions
- PA constants (30% consistency, $2.5k trail lock +$100, safety net +$2,600) UNVERIFIED — community-standard; re-verify before relying on payout mechanics.
- BASELINE pyramid fidelity gap (−13.7%) deferred — per-sub-position TP state needed.
- TV alerts: "Order fills only" + message box = `{{strategy.order.alert_message}}`; TradersPost rejects `exit_all` (use `exit`); recreate alert after EVERY script/preset change.
- Lesson: optimize for regime stability not single-corpus pass%; never pipe long python through head (SIGPIPE); always regenerate exact frames (scaled approximations underestimated PA risk twice).
- Stale untracked: scripts/compare_configs.py, strategies/tradersarc_orb_fade.py, tmp/strb_2024_bad_day_analysis.py — delete or commit.

## Next Work
1. User confirms TradersPost fills parse as JSON live → merge `exp/prop-truth-20260609` to main.
2. Verify PA constants (consistency/payout) via deep research when rate limits allow.
3. Optional: vol-target up-sizing experiment; BASELINE pyramid fidelity; 100K tier recalibration.

Related: [[nq-backtester-plan]], [[prop-consistency-goal]]
