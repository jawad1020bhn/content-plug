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

## Burned-in captions: not this script's job — hand them to VSR

A caption is a caption whether it is a subtitle track or baked into the pixels. Check which one you have in this
order; the first case is free and instant.

**1. A subtitle track** (most common). `remove_captions.py <clip> --strip-soft` removes it with ffmpeg stream copy:
no re-encode, no quality loss, seconds. `ffprobe` shows it as a `codec_type=subtitle` stream.

**2. Burned-in text.** No amount of OpenCV will remove it. Measured here, on real frames of the 720x1280 clip
(bold white meme captions with a black outline, 34-48 px tall, over sky, walls and characters):

- `cv2.inpaint` TELEA r=4, NS r=5, and a multi-scale variant (fill at 0.3x, cubic upscale, feathered blend) were
  compared on identical masks. Every one left a visible grey band — worse than leaving the captions in.
- A feathered heavy blur instead of a fill reads as a censor box, and the line boxes clipped long captions.
- Captions over flat backgrounds (sky, wall) inpaint acceptably; over a character or detailed ground they do not.
  Mixed results are not shippable as "captions removed".
- Opaque text has nothing to recover underneath, so un-blending (`--mode matte`) cannot apply.

**What does work: VSR with LaMa.** `YaoFANGUK/video-subtitle-remover` (Apache-2.0), `--inpaint-mode lama`, given the
caption bands as `-c` regions, reconstructs sky, walls and clouds convincingly. Evidence sheet:
`content output/caption_removal_vsr.png` (same frames, before/after). Output keeps 720x1280, 30 fps and copies audio.

Cost, measured on 2 CPU cores / 3.9 GB RAM: **3.6 s per frame**. A 12 s excerpt took 21.7 min; the full 87.6 s clip
is ~2.5 h. More cores or a CUDA GPU is the fix — not a different tool. Say the number out loud before starting.

### Setting VSR up (every gotcha here cost a run)

```bash
git clone --depth 1 https://github.com/YaoFANGUK/video-subtitle-remover ~/vsr   # ~1.7 GB incl. bundled weights
python3 -m venv ~/vsr/.venv
~/vsr/.venv/bin/pip install torch torchvision          # CPU-only box: add --index-url https://download.pytorch.org/whl/cpu
~/vsr/.venv/bin/pip install opencv-python-headless numpy av einops tqdm scikit-image \
    filesplit requests darkdetect pillow scipy matplotlib "paddlepaddle==3.0.0" paddleocr
```

- **Never clone VSR into this workspace.** 1.7 GB with a 755 MB `.git`; keep it outside and point `--vsr-home` at it.
- Pin **`paddlepaddle==3.0.0`**. 3.3.x dies on CPU with `ConvertPirAttribute2RuntimeAttribute not support`.
- VSR's source needs **Python 3.12+** (PEP 701 nested quotes in `backend/inpaint/sttn_auto_inpaint.py:245`). On 3.11,
  change `{frame_info['len']}` to `{frame_info["len"]}` — it is the only such line.
- `backend/config.py` imports Qt only to hold settings. `clip-desk/scripts/vsr_shim` supplies those names with no Qt,
  so the CLI starts on a server without libGL/libQt (`remove_captions.py` puts it on PYTHONPATH for you).
- `opencv-contrib-python` (a paddle dependency) needs `libGL.so.1`; `opencv-python-headless` is enough in practice.
- Set `PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True`, else paddle stalls checking HuggingFace/ModelScope first. The
  weights are already in the repo, so nothing is downloaded.
- Weights are bundled, but **the ProPainter ones are NTU S-Lab non-commercial**. Apache-2.0 covers the code, not those.
  For paid campaigns use `lama` or `sttn`, never `propainter`.
- Prefer `lama` over `sttn-auto`: STTN fills at 432x240 and upscales, which smears wide caption lines.

### The front door: `remove_captions.py`

```bash
python3 clip-desk/scripts/remove_captions.py <clip> --detect                 # where are the captions?
python3 clip-desk/scripts/remove_captions.py <clip> --strip-soft             # track case, lossless
python3 clip-desk/scripts/remove_captions.py <clip> --rights own --vsr-home ~/vsr
```

It detects caption bands (letter-sized white components inside a dark ring, grouped into lines; a band must appear on
>=3 sampled frames so a sign or a wall of text is not mistaken for a caption), hands those rectangles to VSR as `-c`,
and writes a sidecar. Without `--rights` it refuses; without VSR it exits 3 and prints the setup above rather than
pretending. Detection alone is also useful as a review step.

### Which third-party remover to use (audited 2026-11)

| tool | license / state | run it where | verdict |
|---|---|---|---|
| **VSR** `YaoFANGUK/video-subtitle-remover` | Apache-2.0, 13.8k stars, active | Windows/macOS/Linux, CPU or GPU | **the one to use** — verified end-to-end above |
| **VSR Pro** = `SysAdminDoc/VideoSubtitleRemover` | MIT | Windows 10/11 GUI, CPU ONNX lane | good Windows fallback: region selector, mask review, batch queue, preserves color tags that upstream drops; its "ProPainter" is a LaMa hybrid, not the ICCV weights |
| `videowipe` `KKenny0` | **GPL-3.0** | own machine, CPU via ONNX | works, but GPL — never vendor it into this MIT repo; run it as an external step |
| `AbdullahPesteli` fork of VSR | Apache-2.0 (inherited) | — | adds OpenCode/GStack agent scaffolding, not removal capability; use upstream |
| VideoTextRemover.ai | closed SaaS | uploads your footage | no: the whole promise here is that nothing leaves the machine |
| `guyow/video-studio` | mixed pipeline (subtitle + dubbing studios) | own machine | remove-then-re-caption is the same idea as this skill, but far too large to depend on |

Do not add any of them as a dependency of this repo: they are multi-GB, CUDA-hungry, and one is GPL. The adapter
calls an external checkout, which keeps the licence boundary clean and the repo small.

## Re-captioning or cropping instead

When the render time is unacceptable, or the caption sits on a face: keep the text and add your own language over it
(`multilang` renders localized captions), or crop/zoom it out of frame when it hugs an edge (`--mode crop`). Both are
honest, instant, and sometimes the better edit.

## Guardrails

- Audio is copied, never re-encoded.
- Output goes in `media/edits/` (tracked, survives snapshots); the heavy source stays in `jobs/` (ignored).
- Sidecar JSON keeps `rights`, mode, params and calibration for provenance, so a later reviewer can see why a clip
  looks the way it does.
