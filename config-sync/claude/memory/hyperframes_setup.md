---
name: hyperframes_setup
description: "HyperFrames (HeyGen HTML-video engine) installed globally — skills, CLI, Nate's kit learnings, ElevenLabs caveat"
metadata: 
  node_type: memory
  type: project
  originSessionId: 937a896d-381c-4825-a6cf-a5a8ae418a72
---

# HyperFrames Setup (2026-06-13)

HeyGen's HyperFrames = AI-native video engine: agents write HTML/CSS/JS + GSAP, render via headless Chrome → MP4. Being evaluated as alternative/complement to Remotion for [[igyoutube-state]] trading videos. Decided: bake-off one DLL section both engines before any migration — don't rip out working Remotion stack on vibes.

## Installed globally (~/.claude/skills/) — 15 official skills only
- **15 official** (github.com/heygen-com/hyperframes, `skills/`): hyperframes, hyperframes-cli, hyperframes-media, hyperframes-registry, gsap, website-to-hyperframes, remotion-to-hyperframes, contribute-catalog + adapters three/lottie/animejs/waapi/css-animations/tailwind/typegpu
- **Nate's 2 skills (make-a-video, short-form-video) were installed then REMOVED 2026-06-13** — too personalized ("when Nate says...", reads his AIS MOTION_PHILOSOPHY + example projects that don't exist here). Kept as REFERENCE DOCS only, not active skills.
- Installed by manual `cp -R` from repos (NOT plugin marketplace) → manual updates. Plugin auto-update alt: `/plugin` → claude-plugins-official → hyperframes.

## CLI
`npx hyperframes <cmd>` — no global install. npm pkg `hyperframes` (internal `@hyperframes/cli`) v0.6.97. Node >=22. Commands: init, lint, inspect, preview, render, add, transcribe, tts, remove-background, snapshot, doctor, cloud/lambda/cloudrun.

## CRITICAL: TTS
HyperFrames CLI `tts` = **Kokoro-82M only** (on-device, free; voices af_heart/af_nova/bf_emma/am_adam; ~338MB model auto-dl). **ElevenLabs NOT wired in.** For our ElevenLabs VO: generate externally → import narration.wav → `npx hyperframes transcribe` for word-level caption sync. See [[feedback_igyoutube_outputs]].

## Nate's kit — key learnings (refs staged at IGYouTube/docs/hyperframes-refs/ + MOTION_PHILOSOPHY.md at IGYouTube root for make-a-video Gate 4)
- **Law 11**: every GSAP timeline ends with `tl.to({}, {duration: SLOT_DURATION}, 0)` no-op anchor, else black-frame flashes when timeline.duration() < data-duration. Most common bug.
- `npx hyperframes lint` before EVERY render — catches silent black frames.
- ~1.5s avg scene; one idea per beat (one stat/concept/candle).
- Entrances always `gsap.from()` never `.to()`; transitions handle exits.
- 3 layers min: bg treatment + foreground content + accents. Pure #000 = "nothing loaded."
- Caption energy → technique: high = karaoke + glow + 15% pop; low = gentle shift + 3%. Emphasis words break pattern.
- Audio-reactive: drive GSAP props (scale on bass, glow on treble) — NEVER EQ bars/spectrum.
- make-a-video = 8-gate beginner E2E (brief synthesis is HARD gate). short-form-video = 9:16 talking-head + karaoke captions "May Shorts 19" playbook, 10-rule checklist.
