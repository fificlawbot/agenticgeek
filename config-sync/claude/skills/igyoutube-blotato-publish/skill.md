---
name: igyoutube-blotato-publish
description: Use when publishing a finished IGYouTube video to YouTube via Blotato. Triggers on "publish to YouTube", "upload video", "post to YouTube", or any task that requires getting the video live on the channel.
---

# IGYouTube Blotato YouTube Publisher

## Overview

Blotato requires a **public URL** for the video and thumbnail. Files live in Google Drive (fificlawbot@gmail.com). The flow is: share Drive files publicly → get direct download URLs → call `publish_blotato.py` → video appears in YouTube Studio as private → manually schedule in YouTube Studio.

**Security rule:** Only use Google Drive MCP (authenticated as fificlawbot@gmail.com). Never upload to external file hosts (0x0.st, transfer.sh, catbox.moe, etc.).

## Step 1: Locate Files on Google Drive

Files sync automatically from local `$IGYOUTUBE_DRIVE/$VIDEO_SLUG/` to fificlawbot's Drive. Confirm they exist:

```
Google Drive path: FifiBot/Projects/IGYouTube/<VIDEO_SLUG>/
Files needed:
  final.mp4         (assembled video)
  thumbnail.png     (rendered thumbnail)
```

Use Google Drive MCP to search if Drive IDs are unknown:
```
mcp: search_files("final.mp4 <VIDEO_SLUG>")
```

## Step 2: Make Files Publicly Accessible

Drive MCP has no `set_permissions` tool. User must share manually:

1. Open Google Drive in browser (fificlawbot@gmail.com)
2. Right-click `final.mp4` → Share → "Anyone with the link" → Viewer
3. Right-click `thumbnail.png` → same

Get the file IDs from the Drive URLs or MCP search results.

**Direct download URL pattern:**
```
https://drive.google.com/uc?export=download&id=<FILE_ID>
```

## Step 3: Register with Blotato CDN

Blotato's `/v2/media` accepts a public URL and returns a Blotato-hosted URL. `publish_blotato.py` handles this automatically when `--video-url` and `--thumbnail-url` are passed.

## Step 4: Publish as Private

Run from IGYouTube repo root:

```bash
cd /Users/trp/projects/IGYouTube

.venv/bin/python3 tools/publish_blotato.py \
  .tmp/script_<slug>.json \
  --privacy private \
  --video-url "https://drive.google.com/uc?export=download&id=<VIDEO_FILE_ID>" \
  --thumbnail-url "https://drive.google.com/uc?export=download&id=<THUMB_FILE_ID>"
```

- **No `--scheduled-time`** = Blotato publishes immediately (video appears in YouTube Studio within ~1 min)
- **`--privacy private`** = video stays private; user schedules in YouTube Studio
- **`--dry-run`** to verify payload before sending

Required `.env`:
```
BLOTATO_API_KEY=...
DRIVE_DIR=/path/to/$IGYOUTUBE_DRIVE/$VIDEO_SLUG
VIDEO_SLUG=<slug>
AUDIO_DIR=/path/to/$IGYOUTUBE_DRIVE/$VIDEO_SLUG/audio  # for chapter timestamps
```

## Step 5: Schedule in YouTube Studio

1. Go to https://studio.youtube.com
2. Find the uploaded video (it's private)
3. Click Edit → Visibility → Scheduled
4. Set date/time (default: next Friday 9:00 AM ET)
5. Save

## Blotato Behavior Notes

- **Blotato with `scheduledTime`**: holds post internally, uploads to YouTube AT that time — video invisible in Studio until then
- **Blotato without `scheduledTime`**: uploads immediately — video appears in Studio as private
- To cancel a scheduled Blotato post (if `scheduledTime` was accidentally set): https://my.blotato.com/api-dashboard
- `postSubmissionId` returned by tool = Blotato's internal ID (not YouTube video ID)

## Common Mistakes

- **Forgetting `--privacy private`** — defaults to private but explicit is clearer
- **Adding `--scheduled-time`** — makes video invisible in Studio until that time; don't use
- **Drive file not public** — Blotato gets 403 when fetching; must share "Anyone with the link"
- **Wrong DRIVE_DIR** — tool needs path to the specific video folder (not parent IGYouTube folder)
- **Using astha.tarun Drive** — security rule: fificlawbot@gmail.com only for all Drive operations
