---
name: nq-backtester-plan
description: "NQ/ES backtester — MC-optimized PROP locked, viz cleaned, merged to main 2026-06-03"
metadata: 
  node_type: memory
  type: project
  originSessionId: 380234a3-bfbd-4a66-bb03-61942f2c0cd9
---

# NQ/ES Backtester State

**Repo:** ~/projects/nq-es-backtester
**Branch:** exp/adaptive-tp1-20260525 (merged to main at de7b963 on 2026-06-03)
**Last updated:** 2026-06-03

## Current State
PROP preset locked to MC-optimized config (71% Apex pass rate). Pine + Python parity verified on V10 (TV $72,323 vs Python $75,154). Chart viz cleaned up. Main branch up to date.

## Completed (recent)
- 2026-06-03: Merged exp/adaptive-tp1-20260525 → main (de7b963). Pushed.
- 2026-06-03: Pine v3 viz cleanup — removed OR fill boxes/ORM, added directional pos box (green/red), TP1A/TP2A/StopA labels + per-strat exit comments (11016a0, de7b963)
- 2026-06-03: Locked PROP preset (234ea86): qty 2/2/3, per-strat singleTpR (A=0.75, B=0.50, C=0.75), cap $1000, no Mon skip
- 2026-06-03: MC optimizer (scripts/optimize_prop.py, /tmp/mc_prop.py, /tmp/mc_per_strat_tp.py) — grid search 125 per-strat TP combos, 10K MC sims each
- 2026-06-02: Added intrabar daily cap (apply_daily_cap_intrabar, 7444c5c). Default bar-close projection matches Pine strategy.openprofit. V10 Python=$75,154 vs TV=$72,323 (3.9% gap).
- 2026-06-02: Ingested May 23 – Jun 1 2026 data into MNQ parquet (811,240 rows total)

## Key Data
**PROP preset (locked):** qty 2/2/3, all-out, per-strat TP A=0.75 / B=0.50 / C=0.75, cap $1000, no skip-Mon, opposingMode=SKIP.

**MC Apex 50K sim (10K trials, 60 day max, target $3k, trail $2k):**
- New PROP: **71.2% pass / 28.6% breach / median 17 days / worst -$1,141**
- Old PROP (2/2/2, $150 cap, skip Mon): 34.2% pass / 60.1% breach / median 25 days
- 344 alt: 54.9% pass / median 8 days / worst -$1,464
- 433 alt: 49.1% pass / worst -$1,812

**Recent regime Mar 16 – Jun 1, 2026:** PROP (new) +$3,770 / WR 59% / PF 1.20 / worst -$1,162
**Full 2024-2026 PROP (new):** +$66,567 / WR 63% / PF 1.47
**V10 parity:** TV $72,323 vs Python intrabar(close) $75,154

## Files Changed (recent)
- pinescript/tradersarc_orb_v3.pine — PROP locked, per-strat singleTpR inputs, viz cleanup, per-strat TP/Stop exit comments
- scripts/run_orb_v2.py — apply_daily_cap_intrabar() + --cap-mode / --cap-projection-price flags
- scripts/optimize_prop.py — grid search runner (NEW, uncommitted)
- scripts/compare_configs.py — multi-config comparison runner (NEW, uncommitted)
- /tmp/mc_prop.py, /tmp/mc_per_strat_tp.py, /tmp/mc_tp_sweep.py — MC simulators
- data/market_data/MNQ/1m/MNQ_1m.parquet — ingested through 2026-06-01

## Known Issues / Decisions
- Intrabar cap defaults to projection_price=close to match Pine bar-close strategy.openprofit. Use --cap-projection-price low for realistic prop-firm tick-trail (stricter).
- V10/PROP/BASELINE share opposingMode input (not preset-locked) — user must keep on SKIP for parity.
- StrA orMinutes=30, StrB=15, StrC=5 (ORH/ORL labels show duration suffix).
- Per-strat asymmetric qty + per-strat TP gives ~1-2pp MC pass-rate improvement over uniform — locked into PROP.

## Next Work
1. User verifying locked PROP on TV after pulling main (commit de7b963). Expect ~71% MC pass.
2. If TV PROP diverges from Python, debug per-strat singleTpR wiring (lines ~65-73 + entry blocks ~806-923 in tradersarc_orb_v3.pine).
3. Consider per-strategy daily cap (each strat $333 instead of shared $1000) — not yet implemented.
4. Decide whether to commit scripts/compare_configs.py, scripts/optimize_prop.py, strategies/tradersarc_orb_fade.py (currently untracked).
