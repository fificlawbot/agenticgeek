---
name: igyoutube-thumbnail
description: Use when generating a YouTube thumbnail for any IGYouTube video. Triggers on "generate thumbnail", "create thumbnail", "render thumbnail", or any task that requires producing the thumbnail.png for a finished video.
---

# IGYouTube Thumbnail Generator

## Overview

Thumbnail is a Remotion `still` composition rendered to PNG. No VO, no timing data needed — just run the tool.

## Step 1: Design the Composition (first-time per video)

Composition lives at `remotion/src/compositions/Thumbnail.tsx`. It uses the same design tokens as all other compositions.

Key design rules:
- **1920×1080** — YouTube requires full HD thumbnails
- Dark background (`#0a0a0a`) with vivid accent colors
- Large text, high contrast — readable at 320px thumbnail size
- Bold title at top, compelling stat or hook in center, channel branding at bottom-right
- Use `GridOverlay`, accent bar, particle effects for visual consistency

Reference: `remotion/src/compositions/Thumbnail.tsx` for current orb-prop-eval implementation.

## Step 2: Register Composition

`remotion/src/Root.tsx` must have a `<Composition>` block for `Thumbnail` with `durationInFrames={1}`:

```tsx
import { Thumbnail } from "./compositions/Thumbnail";
// Inside RemotionRoot:
<Composition
  id="Thumbnail"
  component={Thumbnail}
  durationInFrames={1}
  fps={30}
  width={1920}
  height={1080}
  defaultProps={{}}
/>
```

## Step 3: Render

Ensure env vars set, then run from repo root:

```bash
export VIDEO_SLUG=<slug>
export IGYOUTUBE_DRIVE="<drive path>"

cd /Users/trp/projects/IGYouTube
.venv/bin/python3 tools/generate_thumbnail.py
```

Output: `$IGYOUTUBE_DRIVE/$VIDEO_SLUG/thumbnail.png`

To pass custom props (override text/colors at render time):
```bash
# Tool accepts props dict internally — edit render_thumbnail() call in script if needed
```

## Step 4: Verify

```bash
open "$IGYOUTUBE_DRIVE/$VIDEO_SLUG/thumbnail.png"
```

Check: readable at small size, no clipped text, colors pop.

## Common Mistakes

- **TS errors prevent render** — run `cd remotion && npx tsc --noEmit` first
- **Composition not registered** — `npx remotion still Thumbnail` fails with "No composition found"
- **Output dir doesn't exist** — tool creates it automatically via `mkdir -p`
- **Wrong IGYOUTUBE_DRIVE** — output goes to `.tmp/<slug>/` fallback if var unset

## Env Requirements

```bash
VIDEO_SLUG=orb-prop-eval
IGYOUTUBE_DRIVE="/path/to/Google Drive/FifiBot/Projects/IGYouTube"
```
