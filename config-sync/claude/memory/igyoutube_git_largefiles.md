---
name: igyoutube_git_largefiles
description: IGYouTube repo — never commit node_modules/media; history was rewritten once to strip a 136MB chrome blob
metadata: 
  node_type: memory
  type: project
  originSessionId: 937a896d-381c-4825-a6cf-a5a8ae418a72
---

IGYouTube repo (github.com/fificlawbot/IGYouTube, main) must keep large/generated files LOCAL only — never push to GitHub.

**What happened (2026-06-13):** A prior commit had tracked `remotion/node_modules/.remotion/.../chrome-headless-shell` (136MB > GitHub 100MB limit), blocking pushes. Fixed by `git-filter-repo` strip + force-push (rewrote SHAs). Then `.gitignore` hardened with: `node_modules/`, `**/node_modules/`, `.tmp/`, `*.mp4`, `*.mov`, `*.mp3`, `*.wav`, `*.parquet`, `.venv/`, `remotion/out/`, `__pycache__/`.

**How to apply:** All final outputs (video, audio, renders) go to Drive, not git — see [[feedback_igyoutube_outputs]]. Never `git add` node_modules or media. `remotion/public/sfx/*` are untracked working files the pipeline needs locally — do NOT commit them either. If a push fails on blob size, the blob is in HISTORY not just working tree — report it, don't blindly force-push.
