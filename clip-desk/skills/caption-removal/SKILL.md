---
name: caption-removal
description: Remove captions from a clip you own or licensed — subtitle tracks instantly, burned-in text with a neural inpainter. Use when the user says "remove the caption/subtitle", "take the text off the video", "strip the subs", "get rid of the words on screen" before re-captioning or reposting. Refuses to strip other people's caption/credit text.
---

# Caption removal

A caption is a caption whether it is a subtitle track or baked into the pixels, but the two are completely different
jobs and only one of them is free. Check in this order — the first case is instant and lossless.

`python "${CLAUDE_PLUGIN_ROOT}/scripts/remove_captions.py" <clip> [--detect] [--strip-soft] [--rights own|licensed] [--vsr-home ~/vsr]`

## 1. Is it a subtitle track? (most common, and free)

`--strip-soft` removes it with ffmpeg stream copy: no re-encode, no quality loss, seconds. `ffprobe` shows it as a
`codec_type=subtitle` stream. If there is a track, **this is the whole job** — never reach for an inpainter, and never
say "captions removed" after burning a new overlay on top of the old one.

## 2. Is it burned into the pixels?

Then no amount of OpenCV will remove it. Measured on real frames of a 720x1280 clip (bold white meme captions with a
black outline, 34-48 px tall, over sky, walls and characters):

- `cv2.inpaint` TELEA r=4, NS r=5 and a multi-scale variant (fill at 0.3x, cubic upscale, feathered blend) were
  compared on identical masks. **Every one left a visible grey band** — worse than leaving the captions in.
- A feathered heavy blur instead of a fill reads as a censor box, and the line boxes clipped long captions.
- Flat backgrounds (sky, wall) inpaint acceptably; a character or detailed ground does not. Mixed results are not
  shippable as "captions removed".
- Opaque text has nothing to recover underneath, so alpha un-blending (`dewatermark --mode matte`) cannot apply.

**What does work: VSR with LaMa.** `YaoFANGUK/video-subtitle-remover` (Apache-2.0, ~1.7 GB incl. bundled weights),
`--inpaint-mode lama`, given the caption bands as `-c` regions, reconstructs sky, walls and clouds convincingly.
Evidence: `content output/caption_removal_vsr.png` (identical frames, before/after). Output keeps resolution, fps and
copies audio unchanged.

Cost, measured on 2 CPU cores / 3.9 GB: **3.6 s per frame** — 12 s excerpt = 21.7 min, 87.6 s clip ≈ 2.5 h, plus ~35 min
of OCR detection for a clip that length. More cores or a CUDA GPU is the fix, not a different tool. **Say the number
out loud before starting**, and offer re-captioning or cropping first if the human is in a hurry.

### Setting VSR up

```bash
clip-desk/scripts/setup_vsr.sh              # CPU wheels, installs to ~/vsr (~15 min, ~4 GB)
clip-desk/scripts/setup_vsr.sh ~/vsr --cuda # or CUDA wheels
clip-desk/scripts/setup_vsr.sh --verify ~/vsr   # smoke-test an existing install, changes nothing
```

It clones, builds the venv, installs the deps, patches the one Python<3.12 line and smoke-tests the import. The
gotchas it encodes, in case it ever fails and you have to do it by hand:

- **Never clone VSR into this repo.** 1.7 GB; keep it outside and pass `--vsr-home`.
- Pin **`paddlepaddle==3.0.0`**. 3.3.x dies on CPU with `ConvertPirAttribute2RuntimeAttribute not support`.
- CPU boxes need `--index-url https://download.pytorch.org/whl/cpu`, otherwise pip pulls ~3 GB of CUDA libraries.
- VSR's source needs **Python 3.12+** (PEP 701 nested quotes, `backend/inpaint/sttn_auto_inpaint.py:245`). On 3.11
  change `{frame_info['len']}` to `{frame_info["len"]}` — the only such line in the tree.
- `backend/config.py` imports Qt only to hold settings. `scripts/vsr_shim/` provides those names without Qt so the CLI
  runs on a headless box (`remove_captions.py` puts it on PYTHONPATH itself).
- `opencv-contrib-python` (a paddle dependency) wants `libGL.so.1`; `opencv-python-headless` is enough in practice.
- Set `PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True`, else paddle stalls checking HuggingFace/ModelScope before using the
  local weights.
- **Weights are bundled but the ProPainter ones are NTU S-Lab non-commercial.** Apache-2.0 covers the code, not those.
  For paid campaigns: `lama` or `sttn`, never `propainter`.
- Prefer `lama` over `sttn-auto`: STTN fills at 432x240 and upscales, which smears wide caption lines.

### What the script does on its own

`--detect` reports where the captions are, with no model and no VSR: letter-sized white components sitting inside a
dark ring, grouped into lines, and a band only counts if it appears on >=3 sampled frames (so a sign, a wall of text or
a reaction graphic is not mistaken for a caption). It hands those rectangles to VSR as `-c`, which stops the OCR from
erasing other on-screen text. Without `--rights` it refuses; without VSR it exits 3 and prints the setup above instead
of pretending; `--dry-run` prints the exact hand-off. `--selftest` checks the detector itself — run it before blaming
the tool for finding nothing.

Always keep the sidecar: it records `rights`, engine, regions and sampled counts next to the output, so a later
reviewer can see why a clip looks the way it does.

## Arabic (and other RTL languages) — measured, not assumed

Removing the source language is only half of it; the replacement has to render correctly. In this pipeline captions are
**ASS subtitles burned by libass**, which already does bidi and shaping through FriBidi + HarfBuzz — no reshaper and no
`python-bidi` needed for the ASS path.

- **Font.** The default styles use `Arial Black`, which has no Arabic glyphs. `build_ass` now picks an RTL family
  (`Cairo`, `Noto Naskh Arabic`, `Amiri`, `Segoe UI`, `Geeza Pro`, `DejaVu Sans`) via `rtl_font()`, overridable with
  `CLIP_DESK_RTL_FONT`. It must be **one** family name: a comma-separated fallback list inside ASS `Fontname` shifts
  every later field on the Style line and the style silently stops rendering entirely (cost: one debugging round).
- **Word-by-word colour highlight does not survive RTL.** Every word wrapped in `{\c...}` splits the bidi paragraph and
  libass then lays the words out in no stable order — the same line came out as `لازم البيع عن نتكلم`,
  `لازم نتكلم البيع عن` and `عن نتكلم لازم البيع` in three consecutive events, each highlighting a different word.
  Wrapping *every* word symmetrically does not fix it. For RTL, `build_ass` therefore emits one plain run per caption
  group (correct order, no per-word flash). A karaoke `\k` version would keep one paragraph and is the way to restore
  the highlight if it is ever needed.
- **Verify by eye, every time.** Compose a still with `ffmpeg -i frame.png -vf "ass=<file>"` and read the words right to
  left. `content output/arabic_caption_preview.png` is the reference for what "correct" looks like.

## Producing a localized version (Arabic, end to end)

When the source edit already draws its captions as full-width bars, the English sits **inside a plate** — so a
localized version needs no inpainting at all, just an Arabic bar in the same place. `arabic_version.py` does that:

```bash
# 1. read the captions off the frames, write script.json  ({t0,t1,en,ar} per line)
# 2. record the voice, split it per line, conform the captions to the dub
python build_vo.py                 # -> vo.wav + script_vo.json (lines re-timed to the audio)
# 3. burn it
python clip-desk/scripts/arabic_version.py SRC --script script_vo.json --vo vo.wav \
    --out out.mp4 --crf 17 --preset slow --bed 0.10
```

Things that bit us, in order of how much time they cost:

- **No ASR here.** HuggingFace and GitHub release assets are unreachable, so no Whisper model can be downloaded; the
  transcript has to come from the burned-in captions (read them off the frames) or from the human. Say so instead of
  pretending to transcribe.
- **The dub drives the captions, not the other way round.** TTS lines are longer than the original slots; after
  placing each line, push the following ones (`script_vo.json` keeps `t0_orig`) rather than overlapping two Arabic
  voices. Overlap is the one defect a listener notices instantly.
- **Split the TTS on silence, then match segments to lines** by minimising distance to character-proportional targets.
  A naive proportional split cuts words in half; the voice pauses mid-sentence far more than expected.
- **Fit the font per line.** A fixed 62 px overflows the bar on long Arabic lines; measure with the real TTF and shrink
  until it fits (`fit_size`).
- **Take the dominant text cluster only.** Footage often has two text areas at once (caption + end card); the union of
  both paints a bar over half the frame. `band_at` picks the densest cluster and caps the bar height.
- **End cards and other baked-in English** ("YOUR SOUL", "YOU WANT IT BACK?") are part of the footage, not the caption
  track. Translate them too, or the Arabic version ends in English.
- **Loudness**: `loudnorm I=-14` puts it where platforms expect it; keep the original bed at about -20 dB under the
  voice, not silent, so the edit keeps its rhythm (`--bed 0.10`).

## 3. Or don't remove them at all

Often the better edit: re-caption in another language over the original text (`multilang`), or crop/zoom the caption out
of frame when it hugs an edge (`dewatermark --mode crop`). Both are instant, honest, and sometimes what the human
actually wants.

## Which third-party remover to use (audited 2026-11)

| tool | licence / state | run it where | verdict |
|---|---|---|---|
| **VSR** `YaoFANGUK/video-subtitle-remover` | Apache-2.0, 13.8k stars, active | Win/mac/Linux, CPU or GPU | **the one to use** — verified end-to-end on real footage |
| **VSR Pro** = `SysAdminDoc/VideoSubtitleRemover` | MIT | Windows 10/11 GUI, CPU ONNX lane | good Windows fallback: region selector, mask review, batch queue, keeps color tags upstream drops; its "ProPainter" is a LaMa hybrid, not the ICCV weights |
| `videowipe` `KKenny0` | **GPL-3.0** | own machine, CPU via ONNX | works, but GPL — never vendor into this MIT repo; run it as an external step |
| `AbdullahPesteli` fork of VSR | Apache-2.0 (inherited) | — | adds OpenCode/GStack agent scaffolding, not removal capability; use upstream |
| VideoTextRemover.ai | closed SaaS | uploads your footage | no — the promise here is that nothing leaves the machine |
| `guyow/video-studio` | large pipeline | own machine | remove-then-re-caption mirrors this repo's job, far too big to depend on |

None of them is a dependency of this repo: they are multi-GB, CUDA-hungry, and one is GPL. The adapter calls an
external checkout, which keeps the licence boundary clean and this repo small.

## Guardrails

- `--rights own|licensed` is mandatory and goes into the sidecar.
- Refuse when the text belongs to someone else (a credit, a handle, a licence notice): that is attribution stripping,
  not cleanup.
- Captions carry the original creator's wording and jokes. Removing them does not make the clip yours — the underlying
  footage still has rights attached, and `dewatermark`'s provenance rules apply unchanged.
- Show the before/after sheet to the human before anything gets posted.
