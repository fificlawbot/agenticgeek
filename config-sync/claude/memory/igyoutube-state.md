---
name: igyoutube-state
description: "IGYouTube trading video pipeline — active state, completed tools, next actions"
metadata: 
  node_type: memory
  type: project
  originSessionId: 05b4a494-ca3d-4492-bec3-85642a6e703b
---

# IGYouTube State

**Branch/Context:** main, `~/projects/IGYouTube`
**Last updated:** 2026-06-12

## Session Dump (2026-06-08 → 2026-06-09)

### Content Machine — COMPLETE

5 new trading video scripts generated via subagents and saved:
- `idea-research-how-i-passed-topstep-in-8-days-using-orb`
- `idea-research-orb-position-sizing-for-prop-firm-evalua`
- `idea-research-how-to-never-hit-your-daily-loss-limit-a`
- `idea-research-what-is-the-opening-range-breakout-compl`
- `idea-research-volt-strategy-explained-volume-orb-levels`

Saved to:
- Local sidecars: `docs/data/trading/videos/{id}/script.js`
- `docs/data/trading/videos.js` — `has_script: true`, `status: "scripted"` for all 5
- Drive: `$IGYOUTUBE_DRIVE/{id}/script.txt` (plain text, readable on mobile)
- Commit: `5d5067d`

Workflow updated: `workflows/video_production.md` — per-video Drive folder convention documented.

### Pipeline tools (Flow 1) — all green

- `tools/research_topics.py` — YouTube Data API v3 topic research
- `tools/rank_topics.py` — Claude API scoring (engagement_score, alignment score capped 25)
- `tools/generate_scripts.py` — Claude API script gen + `save_script()` / `write_sidecar()` / `upsert_video()`
- `tools/write_draft.py` — engagement_score + yt_research passthrough to drafts.js
- `tools/content_machine.py` — orchestrator for Flow 1

### Dashboard

- `docs/ideas.html` — engagement score badges + YT metrics columns wired
- Research nav link added to sidebar

## ORB Video (orb-prop-eval) — BUILD COMPLETE (2026-06-08)

ALL sections built as custom compositions and rendered (Jun 8 19:01–19:22): hook (HookV2), what_is_prop_eval (PropEvalExplainer), volt_intro/detail, entry_and_patterns, stop_placement (StopPlacement.tsx, 816 lines), risk_rules (RiskRules.tsx), news_avoidance, common_mistakes, outro, plus chart_walkthrough, why_orb, title_card, callouts.

`final.mp4` assembled Jun 8 21:30 — 86MB, 572s (9:32). `thumbnail.png` Jun 8 21:31. Both at Drive `Projects/IGYouTube/orb-prop-eval/`.

## Key Data

- Script: `.tmp/script_orb.json` (id: `2026-06-05-how-i-pass-50k-prop-firm-evals-using-orb`)
- Renders: Drive `Projects/IGYouTube/orb-prop-eval/renders/` (account: fificlawbot@gmail.com)
- Audio: Drive `Projects/IGYouTube/orb-prop-eval/audio/` (account: fificlawbot@gmail.com)
- Timing JSONs: same audio dir, `{sid}_timing.json` (30fps word-level)
- Pipeline: `.venv/bin/python3 tools/run_pipeline.py .tmp/script_orb.json --preview-section <sid>`

## Critical Gotchas

- `fw()` = `frameForWord()` returns FIRST occurrence — use unique words per scene. "FLAG" at frame 50 not 2400 was a bug.
- Non-overlapping sceneOp: endF of scene N = startF of scene N+1.
- `audioSrc: ""` in headless Remotion — FFmpeg handles audio post-render.
- Drive folder per video: `$IGYOUTUBE_DRIVE/{video-id}/` — never flat `scripts/` dir.
- pytest: `.venv/bin/python3 -m pytest tests/` — system python3 missing deps.

## Drive Migration — COMPLETE (2026-06-12)

All paths migrated from `astha.tarun@gmail.com` → `fificlawbot@gmail.com`. `FifiBot/` intermediate folder dropped from Drive path. Files updated:
- `IGYouTube/.env` (4 vars)
- `IGShorts/.env` (IMAGE_FOLDER_PATH)
- `IGYouTube/tools/upload_to_transfer.py` (hardcoded VIDEO path)
- `projects/.claude/settings.local.json` (allow list + additionalDirectories)
- `.claude/settings.json` (allow list + additionalDirectories)
- `IGYouTube/workflows/video_production.md` (example export command)

New base: `/Users/trp/Library/CloudStorage/GoogleDrive-fificlawbot@gmail.com/My Drive/Projects/`

## PUBLISHED (2026-06-12) — video LIVE

- YouTube: https://www.youtube.com/watch?v=-d0eoBY-Tco (Blotato post 4586204, public, IncomeGeek channel)
- Dupe cleanup done 2026-06-12: scheduled Blotato post 1638455 deleted via `DELETE /v2/schedules/{id}` (was set to re-publish Jun 13); YouTube dupe WcCLvpqE-xw deleted by user in Studio. Dead Blotato record 4657789 remains — no API endpoint to delete published records, harmless.
- Blotato API notes: `GET /v2/posts` lists all, scheduled posts cancel via `/v2/schedules/{id}`, published records undeletable.
- SRT captions never generated — optional follow-up if user wants.
