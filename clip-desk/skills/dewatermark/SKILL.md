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

## First, two commands that save the whole afternoon

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/dewatermark.py" --selftest          # engine sane? 97% removal on a synthetic clip
python "${CLAUDE_PLUGIN_ROOT}/scripts/dewatermark.py" <in.mp4> --probe 16 # where is the mark?
```

`--selftest` builds a 3 s clip with a known 25%-alpha mark, removes it and asserts the result (also asserts a bold
caption is untouched). If it fails, the engine is broken — stop and fix that before touching a real video.

`--probe` samples N frames, groups pale text-like shapes by size, ranks them by **recurrence** (a real watermark
shows up again and again; a smooth wall or a bright patch does not), draws a sheet, and prints
`verified: --calibrate t:x,y,w,h (alpha=..., white=..., residual=...)`. "Verified" means that box was fitted to
`I = (1-a)B + aW` and passed: a plausible alpha, a white level, a low residual. Opaque text is rejected (that is
`delogo` territory, not a pale overlay).

**Treat the suggestion as a lead, not a verdict.** On the first real run of this tool the probe verified a pale box
at 72 s while the mark was also sitting at five other positions and two different sizes; a hand-picked box on the
flattest instance gave the better result. Always open the sheet.

## Pick the mode by looking at the mark

| Mark | Mode | What it does |
|---|---|---|
| pale, semi-transparent text (10-30% opacity), may drift or change size | `matte` | calibrates the mark's alpha and white level, then tracks it per frame and subtracts its fitted contribution |
| faint mark everywhere, moves too fast to track | `soft` | fades low-amplitude brightening globally; no detection, but it also flattens faint highlights |
| opaque logo or text, always in the same place | `delogo` | ffmpeg `delogo` on `--box x,y,w,h`; interpolates from the box edges |
| mark hugging one edge | `crop` | cuts `--crop` pixels off the bottom and rescales; nothing is painted over |

`matte` needs one calibration frame where the whole mark sits on a **plain** background:
`--calibrate t:x,y,w,h` (t in seconds), or `--calibrate auto` to use the probe's verified suggestion. The fit is
checked before anything is processed: an implausible alpha, a wild white level, or a high residual is rejected with
a message instead of producing a bad matte. That check is why a wrong box costs one rerun, not a ruined export.

## Always look at the preview

Every run writes `<out>_preview.png` (before/after pairs). Open it and judge at 1:1, not thumbnail size — a ghost
that is invisible in a contact sheet is legible on a phone. Then report honestly:

1. What fraction of frames the mark was located in (`matte` prints it).
2. Where it is still visible, with timestamps.
3. That nothing was posted, and wait for a yes.

Do not claim "removed" when the result is "faded". A faint ghost plus a clean-looking thumbnail is how a page gets
caught by the original creator.

## What is automatic, and what still is not

Automatic now: finding pale text-like shapes, ranking them by recurrence, verifying a calibration against the overlay
model, tracking the mark frame by frame, choosing per frame between original / soft / matte by whichever leaves the
least residue, and writing the sidecar + preview.

Still yours: when the mark is **scaled differently per shot** (common), one calibration only fits one size — run the
probe, note the `recurring mark sizes` line, and do one pass per section, or pick the dominant size. When the probe
cannot verify anything, you supply one `t:x,y,w,h` from a frame you can see. That is a minute of work, and it is the
reason this skill exists: not re-deriving which filter sees a 24%-alpha blurred overlay.

## When the mark is too hard

A blurred, per-shot-scaled, low-alpha overlay that also moves is at the edge of what CPU-only filtering can do.
Say so, show the comparison, and offer the escalation instead of quietly shipping a ghost:

- Run a proper inpainting tool on the human's own machine (`videowipe` — STTN on CPU, no GPU needed; GPL-3.0, so
  run it as an external tool, never vendor it into this MIT plugin). 87 s of 720x1280 is a few minutes.
- Or re-cut from the original master if the human still has it — always cheaper than repair.

## Reproducing the first delivery

The 87 s cut in `content output/testoldaccountshorts_nomark.mp4` came from:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/dewatermark.py" \
  "../content inputs/Video_by_conspiracy_peterx.mp4" \
  --out "../content output/testoldaccountshorts_nomark.mp4" --mode matte \
  --calibrate 2:40,840,352,40 --rights own \
  --threshold 40 --falloff 90 --passes 2 --crf 20 --preview 8
```

Known limit on that file: the mark is soft, ~24% alpha, and changes scale between shots, so the strongest instances
(the mark over the bright orange rays around 20 s) are faded ~60-70%, not erased. Recorded in the sidecar.

## Burned-in captions and subtitles are NOT this tool's job

Tested end-to-end on real footage (bold white meme captions with a black outline, ~34 px tall, over sky, walls and
characters). Detection works well: letter-sized white components that sit inside a dark ring, grouped into lines.
The **fill** is what fails. With only `cv2.inpaint` (TELEA and NS) available in this environment:

- TELEA r=4, NS r=5, and a multi-scale variant (fill at 0.3x, upscale, feathered blend) were all compared on the
  same frames. Every one left a visible grey band where the text had been — worse than the original captions.
- A feathered heavy blur instead of a fill reads as a deliberate censor box, not as removal, and the line boxes
  clipped the ends of longer captions.
- Captions over flat backgrounds (sky, walls) do inpaint acceptably; captions over a character or detailed ground
  do not. Mixed results are not shippable as "captions removed".

Opaque text has nothing to recover underneath, so un-blending (the `matte` mode) cannot apply. What actually works:

1. A neural inpainter on the human's machine — `videowipe` (STTN via ONNX, CPU, GPL-3.0 so run it externally) or
   `video-subtitle-remover`. Minutes for a minute of video; no GPU required.
2. Re-caption instead of removing: keep the burned-in text and add the new-language text over/under it
   (`multilang` already renders localized captions).
3. Crop/zoom to push the caption out of frame, when it hugs an edge (`--mode crop`).

Say this plainly to the human instead of shipping a grey band. If only *some* captions are over flat areas, offer
the partial result and show the before/after sheet so they can decide with their eyes.

## Guardrails

- Audio is copied, never re-encoded.
- Output goes in `media/edits/` (tracked, survives snapshots); the heavy source stays in `jobs/` (ignored).
- Sidecar JSON keeps `rights`, mode, params and calibration for provenance, so a later reviewer can see why a clip
  looks the way it does.
