# RECIPE.md — build a Quran verse-card video end to end

This is the checklist I follow for every video, written so the next one takes minutes, not hours.
Commands assume repo root. Everything here was proven on videos 000 and 001 (see `CATALOG.md`).

> **Before anything:** run `./setup.sh` if `.venv/` is missing, and read
> `clip-desk/skills/quran-subtitles/SKILL.md` + its `references/quality-checklist.md`.

> **House renderer (slots 001 v2 +):** new videos are built with the v2 card renderer —
> templates in `tools/quran_v2/` (the `jobs/` originals are gitignored and vanish between
> sandboxes). Its look & sound spec lives in `docs/HOUSE-STYLE.md`, the planning queue in
> `docs/NEXT-SLOTS.md`. Sections 4 and 8 below keep the legacy `quran_visual.py` chain for
> reference; for a new slot follow **§4bis** instead.

---

## 0. Pick the slot number and read the catalog

New videos get the next free `NNN`. Check `CATALOG.md` first:

- which reciters/verses exist already,
- **which assets are already spent** (Sections 5 and 6 below are the anti-repeat rules).

Create the three matching folders in one go:

```bash
N=002; SLUG=al-baqarah_2-152-153_yasser-ad-dussary   # <surah>_<ayah-range>_<reciter>
mkdir -p assets/quran/${N}_${SLUG} jobs/${N}_${SLUG} metadata/${N}_${SLUG}
```

`jobs/` is gitignored and holds only regenerable intermediates (ASS, verses, timings, polished audio,
visual base). `assets/` holds sources that must survive. `metadata/` holds the post package.
`outputs/` holds the delivered MP4s.

---

## 1. Choose the verse + reciter (viral-first, integrity always)

Working defaults, keep using them unless the human says otherwise:

| Choice | Value that worked | Why |
|---|---|---|
| Reciter | **Yasser ad-Dussary**, QF chapter-reciter **97** | Short, emotionally direct murattal; 435K+ like TikToks prove reach |
| Verse length | **1–3 ayat, ≤ 30 s total** | Fits a reel/Short without a mid-video drop-off |
| Verse type | promise / patience / mercy / remembrance | These carry without a hook line |
| Translation | **`english_saheeh` v1.1.2** (Noor International, QuranEnc) | Clear modern English, credit-friendly |
| Arabic | `text_qpc_hafs` + `UthmanicHafs1Ver18.ttf` | Canonical, matches the font |

Also acceptable: Mishari al-ʿAfasy (ID 7), Abdul Basit Murattal (ID 2).
**Never** The Clear Quran (resource 131, all rights reserved), never Tanzil for commercial posts.

Pick the verse by what a stranger scrolling at 1 a.m. would save: a promise of mercy, patience in
hardship, or remembrance. Not legal verses, not long narratives.

---

## 2. Fetch canonical text + exact timing

```bash
# Arabic words (canonical, QPC Hafs)
curl -s 'https://api.quran.com/api/v4/verses/by_key/2:152?words=true&word_fields=text_qpc_hafs'
curl -s 'https://api.quran.com/api/v4/verses/by_key/2:153?words=true&word_fields=text_qpc_hafs'

# Exact verse/word timings for ONE specific reciter audio
curl -s 'https://api.quran.com/api/v4/chapter_recitations/97/2?segments=true'

# One named published translation, verbatim
curl -s 'https://quranenc.com/api/v1/translation/aya/english_saheeh/2/152?without_footnotes_symbols=1'
curl -s 'https://quranenc.com/api/v1/translation/aya/english_saheeh/2/153?without_footnotes_symbols=1'
```

**Where the network lives.** The sandbox blocks these hosts; `api.quran.com` and `quranenc.com` work
through the agent's `fetch_page` tool, and `download.quranicaudio.com` works from **GitHub Actions**
(any `.github/workflows/*.yml` doing `curl`). So:

- text + translations → `fetch_page`, paste into `jobs/.../verses.json` + `translation.json`
  (flat `{"<surah:ayah>": "<verbatim text>", "_meta": {...}}` — that is the shape
  `--translation-overrides` expects; the nested `{"verses": {...}}` shape is `verses.json`),
- audio → a workflow run that writes `assets/quran/<slot>/recitation.m4a` (copy
  `tools/fetch_quran_assets_v2.py`), then `git pull origin <branch> --ff-only`.

`jobs/.../timings.json` shape that `quran_subtitles.py` parses:

```json
{"reciter": "...", "source_url": "https://api.quran.com/api/v4/chapter_recitations/97/2?segments=true",
 "audio_url": "https://download.quranicaudio.com/quran/yasser_ad-dussary//002.mp3",
 "timestamps": [{"verse_key": "2:152", "start_ms": 3274050, "end_ms": 3284540},
                {"verse_key": "2:153", "start_ms": 3284640, "end_ms": 3299050}]}
```

Timing rule: these milliseconds are valid **only** for that exact MP3. Never reuse them on another
recording or another reciter.

**Reciters outside QF chapter_recitations** (e.g. Sheikh Ali Jaber, slot 002): use MP3Quran's
ayah timing API instead — `https://www.mp3quran.net/api/v3/ayat_timing?surah=<s>&read=<id>`
(Ali Jaber = `read=76`; audio CDN `https://cdn.mp3quran.net/audio/ali-jaber/r1/002.mp3`).
Its *mid-verse word* segments have been ~3 s early in one case (2:153): ayah boundaries are
trustworthy, but every **sub-ayah beat split must be verified acoustically** (RMS/ZCR envelope +
`silencedetect` on the actual trim) before it goes into the beat map. See `HOUSE-STYLE.md` §7.

---

## 3. Trim the recitation (silent intro + tail)

From the full-surah MP3, cut `start_ms − 800` to `end_ms`, 0.8 s of leading silence, 0.2 s/0.5 s fades,
AAC 44.1 kHz stereo → `assets/quran/<slot>/recitation.m4a`. Put **`-ss`/`-t` after `-i`**; the first
attempt in video 000 put `-t` before `-i` and silently lost the intro.

Verify: `\.venv/bin/ffprobe -v error -show_entries format=duration ...` and
`silencedetect=noise=-45dB:d=0.15` → silence should end at ≈0.82 s.

---

## 4. Render the card

```bash
J=jobs/001_al-baqarah_2-152-153_yasser-ad-dussary
A=assets/quran/001_al-baqarah_2-152-153_yasser-ad-dussary

# 4a. audio polish (hall space + clarity, words and timing untouched)
.venv/bin/python clip-desk/scripts/quran_audio_polish.py \
  --in $A/recitation.m4a --out $J/recitation_polished.m4a \
  --wet 0.15 --predelay 45 --target-lufs -14.5 --ceiling -1.5 --tail 0.4

# 4b. visual base: black card + rounded popup + slow push-in
.venv/bin/python clip-desk/scripts/quran_visual.py \
  --background $A/background.mp4 --out $J/visual_base.mp4 \
  --duration 26.2 --intro 0.8 --pop-duration 0.7 --fade-in 0.35 \
  --popup-top 340 --popup-width 1000 --popup-height 780 --radius 90 \
  --dim 0.10 --glow-strength 0.055 --border-strength 0.20 \
  --zoom-start 1.03 --zoom-end 1.00

# 4c. captions + final MP4
.venv/bin/python clip-desk/scripts/quran_subtitles.py \
  --verses $J/verses.json --timings $J/timings.json --range 2:152-153 \
  --translation-overrides $J/translation_overrides.json \
  --translation-edition 'english_saheeh v1.1.2 / QuranEnc.com' \
  --translation-credit 'English Translation - Noor International Center' \
  --reciter 'Yasser ad-Dussary (Murattal, Hafs)' \
  --timing-source 'QF chapter_recitations/97/2?segments=true' \
  --surah-name 'Surah Al-Baqarah' \
  --out $J/captions.ass --srt $J/review.srt \
  --font-dir clip-desk/skills/quran-subtitles/fonts --layers header,arabic,english,ref \
  --width 1080 --height 1920 --fps 30 \
  --header-y 270 --arabic-y 1275 --english-y 1450 --ref-y 1605 \
  --arabic-size 62 --english-size 46 --header-size 36 --ref-size 28 \
  --arabic-cpl 36 --arabic-lines 2 --english-cpl 42 \
  --fade-ms 400 --dim 0 --strict \
  --auto-offset --offset-ms 800 --source-start-ms 0 --audio-start-ms 0 \
  --video-duration 26.2 --max-duration 15 --max-cps 20 \
  --source-video $J/visual_base.mp4 --audio $J/recitation_polished.m4a \
  --video-out outputs/quran-001_al-baqarah_2-152-153_yasser-ad-dussary_en_1080x1920_v1.mp4 \
  --credits-out metadata/001_al-baqarah_2-152-153_yasser-ad-dussary/credits.txt
```

Always `--dry-run --strict` first (catches missing translations and duration overruns before a
2-minute encode). Layout numbers above are the proven mobile layout — see Section 8.

---

## 4bis. Render the card — v2 renderer (house path since 001 v2, proven on 002)

The v2 renderer replaces 4b+4c: it draws the black card, narrowed Reels-safe popup, fake-scroll
opener, halo/motes/filament and the ASS captions in one streaming pass, then muxes the mastered
audio. Templates + per-slot edit points: `tools/quran_v2/README.md`. Spec: `HOUSE-STYLE.md`.

```bash
export PATH="$PWD/.venv/bin:$PATH"
cp tools/quran_v2/build_audio_template.py jobs/<slot>/build_audio.py
cp tools/quran_v2/build_video_template.py jobs/<slot>/build_video.py
# edit SLOT constants: paths, DURATION_S, REC_START/END_S, BEATS, ayah_spans, header text,
# and rewrite the scene-matched ambience bed in build_audio.py

python jobs/<slot>/build_audio.py                 # master + voice_env_30fps.npy + report
python jobs/<slot>/build_video.py --test-preview  # ~5 s: 3 pre-flight stills, LOOK at them
python jobs/<slot>/build_video.py                 # full render + final mux into outputs/
```

Pre-flight stills caught both of slot 002's defects (libass font fallback, stray separator line)
before a 2-minute render — never skip them.

---

## 5. Background: one clip, never reused

Rules the human set explicitly:

- **One clip only.** No montage, no crossfade between scenes. A single continuous shot for the whole verse card.
- **Never reuse a clip** that a previous video used. The registry below is the source of truth.
- A clip file is "spent" once it appears in `selection.txt` of any asset pack.

Procedure:

1. Look at `docs/ASSET-REGISTRY.md` → *Spent clips* to see what is off-limits.
2. Pick the next unused candidate from the same source board (or a new supplied source).
3. Slow or trim it to the exact duration; do not loop-cut in the middle of the card if avoidable.
4. Record the pin/clip id, duration, resolution, sha256 and the transformation in
   `assets/quran/<slot>/SOURCE.md` and in the registry.

Single-clip background build (proven, no scene cuts):

```bash
CLIP=assets/quran/<slot>/pinterest/<file>.mp4
# 26.2 s target from an 18.13 s clip -> setpts factor 1.4453, then scale/crop to 1080x1920
.venv/bin/ffmpeg -y -i "$CLIP" \
  -vf "setpts=1.4453*PTS,fps=30,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920" \
  -an -t 26.2 -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p -movflags +faststart \
  assets/quran/<slot>/background.mp4
```

Verify it is truly one scene: scene-detect must return **0** cuts:
`.venv/bin/ffmpeg -i out.mp4 -filter:v "select='gt(scene,0.3)',showinfo" -f null - 2>&1 | grep -c pts_time`

Anime backgrounds: no people, no animals (standing rule).

---

## 6. Assets: upload, select, prune, register

- Human-supplied boards/links → import with a GitHub Actions job (egress lives there), 12 candidates,
  contact sheet + `candidates.json`.
- Inspect `candidates_sheet.png` by eye; pick **one**.
- Delete the unselected candidate MP4s from the repo immediately (they are large), keep
  `candidates.json`, the contact sheet and the chosen clip.
- Write `selection.txt` with the chosen index and a one-line reason.
- Add the chosen clip to **Spent clips** in `docs/ASSET-REGISTRY.md` in the same commit.

---

## 7. QA before showing anything

```bash
V=outputs/quran-001_....mp4
.venv/bin/ffprobe -v error -show_entries format=duration,size \
  -show_entries stream=codec_name,width,height,r_frame_rate,sample_rate,channels -of json "$V"
.venv/bin/ffmpeg -i "$V" -vf blackdetect=d=0.3:pix_th=0.01 -an -f null - 2>&1 | grep black_
.venv/bin/ffmpeg -i "$V" -af silencedetect=noise=-45dB:d=0.2 -vn -f null - 2>&1 | grep silence_
.venv/bin/ffmpeg -i "$V" -af loudnorm=print_format=summary -f null - 2>&1 | grep 'Input '
```

Then a poster + 6-frame contact sheet into `metadata/<slot>/` and **look at both**:

```bash
.venv/bin/ffmpeg -y -ss 18 -i "$V" -frames:v 1 -update 1 metadata/<slot>/poster.png
.venv/bin/ffmpeg -y -i "$V" -vf "select='eq(n,12)+eq(n,90)+eq(n,300)+eq(n,420)+eq(n,600)+eq(n,760)',\
setpts=N/FRAME_RATE/TB,scale=540:960,tile=2x3:padding=8:margin=8" -frames:v 1 -update 1 metadata/<slot>/qa.png
```

Hard gates: 1080×1920, 30 fps, H.264 + AAC 44.1 kHz, ≈26 s (or verse length + 1.2 s),
black intro 0→0.83 s, loudness ≈−14.5 LUFS / true peak ≤ −1.5 dBTP, no circular mask on the popup,
Arabic RTL with connected harakat, English ≥46 px, nothing overlapping.

v2 renderer additions: inspect the three `--test-preview` stills **before** the full render
(scroll strip, beats grid, **20:9 Reels crop sim**), and build `qa.png` with **8 panels from the
final MP4** — one opener frame (t≈0.25 s) plus one per beat — see `metadata/002_…/qa.png` as the
reference sheet. Loudness gate for v2 masters: ≈−14.3 LUFS.

---

## 8. Proven numbers (do not re-derive these)

| Thing | Value |
|---|---|
| Canvas | 1080×1920, 30 fps, H.264 crf 18, `+faststart`, AAC 192 kbps 44.1 kHz |
| Popup | top 340, 1000×780, radius 90, border 2 @ 0.20, glow 0.055, shadow blur 26/offset 14/0.34 |
| Intro | 0.8 s black, popup pops in 0.7 s with 0.35 s fade, zoom 1.03→1.00 |
| Arabic | 62 px, 36 cpl, max 2 lines, y 1275 |
| English | **46 px**, 42 cpl, y 1450 |
| Header | 36 px at y 270; reference 28 px at y 1605 |
| Audio | wet 0.15 (−16 dB), pre-delay 45 ms (wet only), decay 0.52 s, IR 1.6 s, −14.5 LUFS |
| Caption gap | verse gap 100 ms (`--auto-offset` handles the lead-in) |

Reading speed sanity: 6.8–7.4 CPS on video 001 is comfortable; `--max-cps 20` is the hard ceiling.

### v2 proven numbers (slots 001 v2, 002 — full spec in `HOUSE-STYLE.md`)

| Thing | Value |
|---|---|
| Popup | **816×748** @ (132, 342), radius 76 — Reels 20:9 zoom keeps ≥70 px black + halo each side |
| Opener | fake scroll 0→0.84 s from +1340 px, −15 px overshoot @0.65 s, **no hook text** |
| Header | `Cormorant Garamond Light` 36 px sprite strip @ y 226 |
| Arabic / English / Ref | 60 px @ y 1248/1236 · 46 px @ y 1408/1422 (+100 ms stagger) · 28 px @ y 1568 (per-ayah spans) |
| Filament / motes / halo | y 1612, 168 px · 28 pre-blurred sprites · σ34 ring, strength 0.055+0.068·env |
| Audio | Haram stereo IR 3.2 s, 56 ms pre-delay, wet 0.42, ducked scene bed ≤−35 dBFS, −14.3 LUFS |
| Loop | 0.45 s tail fade for seamless Reels loop |

---

## 9. Publish package (metadata/<slot>/)

`caption.txt` = description with credits inline. `credits.txt` = the plain credit block.
`post.json` = machine-readable metadata (filled by hand or script). See `docs/PUBLISHING.md`
for the per-platform fields. Credits never go into video pixels.

---

## 10. Close the loop

1. Add the row to `CATALOG.md` (status `ready for review`).
2. Append the clip to **Spent clips** in `docs/ASSET-REGISTRY.md`.
3. Commit + push. Open a PR only when the human asks for a merge.
4. Show the human: MP4 path, caption, credits, poster, QA sheet. **Wait for an explicit "yes".**

---

## 11. Sandbox & tooling traps (hard-won, re-read before every build)

- `ffmpeg`/`ffprobe` exist **only** in `.venv/bin` — `export PATH="$PWD/.venv/bin:$PATH"` first.
- No PIL/Pillow in `.venv`; every text render goes through libass (`ass=…:shaping=1`).
- libass matches the font's internal family name: the bundled serif is
  **`Cormorant Garamond Light`**; writing `Cormorant Garamond` silently falls back to DejaVu Sans.
- Python 3.11 f-strings cannot contain backslashes inside `{}` — assign `\N`/`\move` tag strings
  to a variable first.
- Never `GaussianBlur` full frames per frame (001 v2 hit the 600 s timeout); precompute
  sprites/masks, stream source frames with a ring buffer.
- `gh workflow run` → HTTP 403 here; trigger Actions with a `.github/triggers/*.trigger` file + push.
- `jobs/` is gitignored and vanishes between sandboxes — durable templates live in `tools/quran_v2/`.
- `-ss`/`-t` go **after** `-i` when trimming (slot 000 lost its intro otherwise).
- Pinterest pin ids expire across sessions; board-K originals are re-imported from git commit
  `422b92c177ef5bd40a0761db318d1a7626a553f9`, not from Pinterest.
- MP3Quran mid-verse word timings can be seconds early — verify splits on the waveform.
