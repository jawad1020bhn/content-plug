---
name: dewatermark
description: Remove a burned-in watermark from a video you own or licensed. Use when the user says "remove the watermark/logo/@handle" from their own footage, usually before reposting an old clip on a new page. Refuses to be a tool for stripping someone else's attribution.
---

# Dewatermark

Run:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/dewatermark.py" <in.mp4> --out <out.mp4> --rights own|licensed --mode matte|soft|delogo|crop`

`--rights` is **required** and is written into the sidecar JSON next to the output. Ask the human first: is this
footage theirs, or do they hold a licence for it? If it is someone else's clip, stop — removing another creator's
watermark is attribution stripping, and the desk's credit rule (`rule-check`) forbids it. There is no "just this
once" here.

## Pick the mode by looking at the mark

| Mark | Mode | What it does |
|---|---|---|
| pale, semi-transparent text (10-30% opacity), may drift or change size | `matte` | calibrates the mark's alpha and white level, then tracks it per frame and subtracts its fitted contribution |
| faint mark everywhere, moves too fast to track | `soft` | fades low-amplitude brightening globally; no detection, but it also flattens faint highlights |
| opaque logo or text, always in the same place | `delogo` | ffmpeg `delogo` on `--box x,y,w,h`; interpolates from the box edges |
| mark hugging one edge | `crop` | cuts `--crop` pixels off the bottom and rescales; nothing is painted over |

`matte` needs one calibration frame where the whole mark sits on a **flat** background:
`--calibrate t:x,y,w,h` (t in seconds). Read `x,y,w,h` off a frame you extracted — the script exits with a clear
message if the fit is implausible, which usually means the box included hard edges.

## Always look at the preview

Every run writes `<out>_preview.png` (before/after pairs). Open it and judge at 1:1, not thumbnail size — a ghost
that is invisible in a contact sheet is legible on a phone. Then report honestly:

1. What fraction of frames the mark was located in (`matte` prints it).
2. Where it is still visible, with timestamps.
3. That nothing was posted, and wait for a yes.

Do not claim "removed" when the result is "faded". A faint ghost plus a clean-looking thumbnail is how a page gets
caught by the original creator.

## When the mark is too hard

A blurred, per-shot-scaled, low-alpha overlay that also moves is at the edge of what CPU-only filtering can do.
Say so, show the comparison, and offer the escalation instead of quietly shipping a ghost:

- Run a proper inpainting tool on the human's own machine (`videowipe` — STTN on CPU, no GPU needed; GPL-3.0, so
  run it as an external tool, never vendor it into this MIT plugin). 87 s of 720x1280 is a few minutes.
- Or re-cut from the original master if the human still has it — always cheaper than repair.

## Guardrails

- Audio is copied, never re-encoded.
- Output goes in `media/edits/` (tracked, survives snapshots); the heavy source stays in `jobs/` (ignored).
- Sidecar JSON keeps `rights`, mode, params and calibration for provenance, so a later reviewer can see why a clip
  looks the way it does.
