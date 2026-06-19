---
name: feedback-igyoutube-outputs
description: "IGYouTube pipeline output destinations — all final outputs go to Google Drive, not .tmp/"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: ba376808-8d42-47e8-8e51-8b4ddc246df9
---

All IGYouTube pipeline outputs (renders, audio, final video) must go to Google Drive, not `.tmp/`.

**Why:** User explicitly requested Drive storage so outputs are accessible outside local machine.

**How to apply:**
- `final_draft.mp4` → `/Users/trp/Library/CloudStorage/GoogleDrive-fificlawbot@gmail.com/My Drive/Projects/IGYouTube/<video-id>/<slug>_draft.mp4`
- Audio MP3s → `AUDIO_DIR` env var (already set to Drive path in `.env`)
- Renders → `RENDERS_DIR` env var (already set to Drive path in `.env`)
- `.tmp/` is scratch only — copy final outputs to Drive after assembly
- See [[igyoutube-state]] for env var values
