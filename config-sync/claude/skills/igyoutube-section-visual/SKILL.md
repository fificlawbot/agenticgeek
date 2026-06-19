---
name: igyoutube-section-visual
description: Use when building or updating a visual Remotion composition for any section of the IGYouTube trading video pipeline. Triggers on requests like "build visuals for X section", "add animations to Y", "what should the Z section look like", or any task that requires mapping VO script content to animated scenes.
---

# IGYouTube Section Visual Composer

## Overview

Each video section is a word-sync Remotion composition that maps spoken VO segments to animated visual scenes. The pattern is: **analyze VO → design scene map → implement using shared lib → render preview → iterate**.

## Shared Library (always import from here)

```tsx
import { spr, c01, sceneOp } from "../lib/scene-helpers";
import {
  AmbientParticles, ScanLine, TransitionFlash, PulseRing, GridOverlay,
} from "../lib/background-effects";
```

- `spr(rel, fps, stiffness=380, damping=22)` — spring with sensible trading-video defaults
- `c01(v)` — clamp to [0, 1]
- `sceneOp(frame, startF, endF, fadeIn=8, fadeOut=12)` — crossfade opacity for a scene window
- `AmbientParticles`, `ScanLine`, `TransitionFlash`, `PulseRing`, `GridOverlay` — always include these in every composition for visual consistency

## Step 1: Analyze the VO + Timing

Read the section script and timing file. Identify natural scene breaks — usually a new concept, a key phrase, or a strong visual noun.

```bash
# timing data lives here (30fps):
cat .tmp/audio/<section_id>_timing.json | python3 -c "
import json, sys
for w in json.load(sys.stdin):
    print(f\"{w['word']:<20} {w['start']:.2f}s  → frame {int(w['start']*30)}\")"
```

## Step 2: Design the Scene Map

Map each VO segment to a scene type. Aim for 4–7 scenes per 30-second section.

| VO Content | Scene Type | Visual |
|---|---|---|
| Statistic or number | **StatCard** | Giant animated counter, glow, label |
| P&L / account balance | **PLChart** | Line chart drawing in, red crash zone |
| Chart pattern / entry | **CandleChart** | SVG candlesticks + zone + breakout arrow |
| Achievement / pass/fail | **Badge** | Gold/red badge with shimmer sweep |
| Rules / checklist | **BulletList** | Items slide in from left, icon + text |
| Comparison / two concepts | **DualPanel** | Side-by-side cards with staggered items |
| Concept intro | **TextSlam** | Large centered text, spring entrance |

### Scene boundary triggers

Use `frameForWord(word, timingData)` to anchor each scene to a spoken word. Pick the most prominent word at the start of each concept.

```tsx
const fFail     = frameForWord("fail", timingData) || 20;
const fStrategy = frameForWord("STRATEGY", timingData) || 119;
// etc.
```

Fallback frame values should be realistic estimates from the timing data if the word isn't found.

## Step 3: Implement the Composition

### Composition boilerplate

```tsx
import React from "react";
import { AbsoluteFill, Audio, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { WordTiming, frameForWord } from "../hooks/useWordSync";
import { spr, c01, sceneOp } from "../lib/scene-helpers";
import { AmbientParticles, ScanLine, TransitionFlash, PulseRing, GridOverlay } from "../lib/background-effects";

export type <SectionName>Props = {
  timingData: WordTiming[];
  audioSrc: string;
  durationInFrames: number;
  sectionId?: string;
};

export const <SectionName>: React.FC<<SectionName>Props> = ({ timingData, audioSrc, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Scene anchor frames
  const fA = frameForWord("word_a", timingData) || <estimate>;
  const fB = frameForWord("word_b", timingData) || <estimate>;

  // Start scenes 20-80 frames BEFORE anchor word so animations ARRIVE as word hits.
  // Simple text fades: 20f early. Complex spring/slam sequences: 40-80f early.
  const FADE = 20;
  // NON-OVERLAPPING transitions: endF of scene N = startF of scene N+1.
  // sceneOp(startF, endF): scene fades in over FADE from startF, fades out ending at endF.
  // Result: s1 reaches 0 exactly when s2 starts → no simultaneous visibility.
  const s1Op = sceneOp(frame, 0,   fA,              10,   FADE);
  const s2Op = sceneOp(frame, fA,  durationInFrames, FADE, 0);

  const flashFrames = [fA, fB];
  const pulseFrames = [fA];

  return (
    <AbsoluteFill style={{ backgroundColor: "#0a0a0a", overflow: "hidden" }}>
      <GridOverlay />
      <AmbientParticles frame={frame} />
      <ScanLine frame={frame} />
      <PulseRing frame={frame} triggerFrames={pulseFrames} />

      {/* Top accent bar — use gradient relevant to section mood */}
      <div style={{
        position: "absolute", top: 0, left: 0, right: 0, height: 4,
        background: "linear-gradient(90deg, #ff2222, #ff8800, #00ff88)",
      }} />

      {s1Op > 0 && <SceneA frame={frame} fps={fps} triggerF={<frame>} opacity={s1Op} />}
      {s2Op > 0 && <SceneB frame={frame} fps={fps} triggerF={fA - FADE} opacity={s2Op} />}

      <TransitionFlash frame={frame} flashFrames={flashFrames} />
      {audioSrc && <Audio src={audioSrc} />}
    </AbsoluteFill>
  );
};
```

### Design constants

| Token | Value |
|---|---|
| Background | `#0a0a0a` |
| Green accent | `#00ff88` |
| Red danger | `#ff2222` / `#ff4444` |
| Gold | `#ffd700` |
| Muted text | `#888888` / `#666666` |
| Card glow green | `0 0 80px rgba(0,255,136,0.55)` |
| Card glow red | `0 0 80px rgba(255,34,34,0.8)` |

### Animation timing guidelines

- **Anticipation rule**: Scene trigger frame = anchor word frame MINUS 20-80. Animations must COMPLETE as the word hits, not START when it hits.
- **Density rule**: Max ~90 frames (3s) between any two visual changes within a scene. Design 4-6 internal triggers per scene, not just one entrance.
- **Variety rule**: Never use the same enter/exit combo for consecutive scenes. Pick from the palette below and mix intentionally — monotonous transitions make the video feel cheap.
- Spring entrance: stiffness 260–420, damping 18–24
- Counter animation: complete in ~28 frames
- Chart draw-in: 28–40 frames
- Staggered list items: 40–60 frames apart
- Fade-in labels after parent: +12–20 frames offset

### Transition palette

`sceneOp` only controls opacity. Layer transforms on top for enter/exit effects. Drive them with `interpolate` off the same frame math.

**Enter effects** (scene coming in — use `rel = frame - triggerF`, spring from 0):
```tsx
// Fade (baseline — avoid overusing)
opacity: spring

// Rise up
transform: `translateY(${interpolate(spring, [0,1], [40, 0])}px)`

// Slam/zoom in (high energy — for key moments)
transform: `scale(${interpolate(spring, [0,1], [1.6, 1])})`

// Slide from right
transform: `translateX(${interpolate(spring, [0,1], [120, 0])}px)`

// Slide from left
transform: `translateX(${interpolate(spring, [0,1], [-120, 0])}px)`

// Drop in
transform: `translateY(${interpolate(spring, [0,1], [-40, 0])}px)`
```

**Exit effects** (scene leaving — use `exitRel = endF - frame`, interpolate toward 0):
```tsx
// Fade out (baseline)
opacity: exitProgress  // 1→0 as frame→endF

// Explode out (scale up while fading — energetic cut)
const exitP = Math.max(0, Math.min(1, (frame - (endF - FADE)) / FADE)); // 0→1
opacity: 1 - exitP
transform: `scale(${interpolate(exitP, [0,1], [1, 1.25])})`

// Collapse (scale down while fading)
transform: `scale(${interpolate(exitP, [0,1], [1, 0.85])})`

// Slide out left
transform: `translateX(${interpolate(exitP, [0,1], [0, -150])}px)`

// Flash cut (0-frame exit — instant scene change, no fade)
// Set fadeOut=0 in sceneOp, use TransitionFlash on that frame
```

**Mixing guidance** — pick per-scene based on energy:

| Scene type | Good enter | Good exit |
|---|---|---|
| Concept intro / title slam | Slam (zoom in) | Explode out |
| Stat card / number reveal | Rise up | Fade out |
| List / checklist | Slide from left | Slide out left |
| Warning / danger | Drop in (fast spring) | Flash cut |
| Calm explanation | Fade | Collapse |
| Call to action / closer | Rise up | — (hold to end) |

**Example: non-monotonous 4-scene composition**
```tsx
// s1: Slam in → explode out
// s2: Rise up → fade out  
// s3: Slide left → collapse out
// s4: Rise up → hold

const FADE = 18;
// ... sceneOp calls with endF=next startF (non-overlapping)

// Inside SceneA (slam enter, explode exit):
const enterSpr = c01(spr(rel, fps, 460, 18));
const exitP = Math.max(0, Math.min(1, (frame - (s2Start - FADE)) / FADE));
const scale = interpolate(enterSpr, [0,1], [1.5, 1]) * interpolate(exitP, [0,1], [1, 1.2]);
const op = enterSpr * (1 - exitP);
return <AbsoluteFill style={{ opacity: op * parentOpacity, transform: `scale(${scale})` }}>...</AbsoluteFill>
```

Note: when mixing custom enter/exit transforms with `sceneOp` opacity, you can either multiply them or bypass `sceneOp` entirely and drive both opacity and transform from frame math directly.

## Step 4: Register the Composition

**Root.tsx** — add import + `<Composition>` block:

```tsx
import { <SectionName> } from "./compositions/<SectionName>";
// Inside RemotionRoot:
<Composition
  id="<SectionName>"
  component={<SectionName>}
  durationInFrames={WORD_SYNC_DEFAULT.durationInFrames}
  fps={30} width={1920} height={1080}
  defaultProps={{ ...WORD_SYNC_DEFAULT, sectionId: "<section_id>" }}
  calculateMetadata={({ props }) => ({ durationInFrames: props.durationInFrames })}
/>
```

**tools/run_pipeline.py** — add to `WORD_SYNC_COMPOSITIONS`:

```python
WORD_SYNC_COMPOSITIONS = {"WordSyncBold", ..., "HookV2", "<SectionName>"}
```

**script_orb.json** — update the section's `"composition"` field to `"<SectionName>"`.

## Step 5: Render and Preview

```bash
# Delete old render first if section was previously rendered
rm "/path/to/renders/<section_id>.mp4"

# Render + mux audio preview
.venv/bin/python3 tools/run_pipeline.py .tmp/script_orb.json --preview-section <section_id>

# Open result
open "/path/to/renders/<section_id>_preview.mp4"
```

TypeScript errors? Run `cd remotion && npx tsc --noEmit` to catch them before the slow render.

## Scene Component Template

Every scene follows this exact signature — keep it consistent so scenes are composable:

```tsx
const SceneName: React.FC<{ frame: number; fps: number; triggerF: number; opacity: number }> = ({
  frame, fps, triggerF, opacity,
}) => {
  const rel = frame - triggerF;
  // all animation based on `rel` (frames since scene started)
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", opacity }}>
      {/* scene content */}
    </AbsoluteFill>
  );
};
```

## Sizing Rule — Background Chart is Always Present

The `#0a0a0a` background always has a faint chart texture behind all content. Overlay SVG charts, animated visuals, and text **must be deliberately large** or they vanish into the background:

- SVG charts: span **60%+ of frame width** (1152px+ of 1920px)
- Chart labels / axis text: **fontSize 48px minimum** (64px+ preferred)
- Supporting explainer text below charts: **fontSize 40px minimum**
- Stat card numbers: **fontSize 120–180px**
- Scene titles / slams: **fontSize 96–140px**

When in doubt, bigger. Small charts become unreadable in the rendered 1080p output.

## Common Mistakes

- **Forgetting WORD_SYNC_COMPOSITIONS**: Pipeline won't inject timing data → blank composition
- **Using `frame` instead of `rel`**: Scenes animate from global frame 0, not their trigger
- **Too many scenes**: 7+ scenes in 30s = no scene gets time to breathe. Cut mercilessly.
- **Hardcoding trigger frames**: Always use `frameForWord()` with a fallback, never magic numbers only
- **Missing audio**: `audioSrc` prop comes from pipeline automatically when section is in `WORD_SYNC_COMPOSITIONS`
- **Starting scene AT anchor word**: Animations start when word hits instead of arriving — always subtract 20-80f from anchor word for scene trigger
- **Fade for everything**: Using fade-in/fade-out on every scene transition makes the video feel flat and monotonous. Mix from the transition palette — vary enter/exit per scene based on energy level.
- **Crossfade overlap on dense scenes**: `sceneOp(fA - FADE, ...)` as next scene's startF means both scenes render simultaneously for FADE frames. Fine for simple text dissolves. For scenes with multiple independent animated elements (rows, badges, cards), use non-overlapping boundaries: scene N's `endF = scene N+1's startF`
- **Long static windows**: Scenes with only 1-2 triggers feel dead — design 4-6 internal animation moments per scene, max 90 frames between changes
- **Charts too small**: Background chart makes small overlays unreadable. Charts must span 60%+ of frame — see Sizing Rule above.
- **TypeScript before render**: `cd remotion && npx tsc --noEmit` catches errors before the 3–5 min render. Always run first.
- **Stale render cached**: Pipeline skips existing renders. Delete `$RENDERS_DIR/<section_id>.mp4` before re-rendering a section after code changes.
