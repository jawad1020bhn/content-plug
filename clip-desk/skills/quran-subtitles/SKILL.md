---
name: quran-subtitles
description: Build verified Quran-recitation subtitles from canonical QPC Hafs Arabic, one named rights-cleared translation, and exact QF/QUL or Quran-aligned ayah/word timing, rendered as RTL-safe ASS/libass with the bundled KFGQPC Uthmanic Hafs and Cormorant Garamond fonts. Use before making a Quran video or when the user says "Quran subtitles", "ayah captions", "caption this recitation", "Surah ... subtitles", "Quran caption method", or "best fit font for Quran"; never use generic ASR/Whisper/CapCut auto-captions or machine translation.
---

# Quran subtitles

Use this skill **before** the generic caption tools whenever the audio is Quran recitation. The winning method is
canonical text + a named published translation + exact timing + libass, followed by human QA. See
[`references/method.md`](references/method.md) for the ranked evidence and source links.

**Hard gates:**

- No generic ASR, Whisper/faster-whisper, CapCut/Zeemo/auto-caption output, OCR of an unknown card, or machine
  translation as the text source. Quran recitation has madd/tajwid/waqf that breaks conversational ASR.
- Use QF/QUL segment timings **only for the exact reciter/audio they describe**. For custom audio (for example an
  Instagram recitation), use Quran-specific forced alignment or manual waveform review first. Do not copy QF
  timestamps onto arbitrary audio.
- Keep raw QF/QUL API JSON, generated `.ass`/`.srt` containing Quran text, and temporary fetched data in an ignored
  `jobs/<slot>/` folder. Do **not** commit raw API data to the public repo. Final MP4s go in `outputs/`,
with the post package in `metadata/<slot>/` and sources in `assets/quran/<slot>/` (see `docs/RECIPE.md`).
- Credits go in the **post caption/description**, never burned into the video. Credit Quran Foundation/KFGQPC, the
  named translation, the reciter, and the original creator/background as applicable.
- `rule-check` still applies. Show the human the file, caption and credits, then wait for an explicit **"yes"**.
  Nothing is uploaded or posted automatically.
- If the human asks for an **anime** background, it must contain **neither people nor animals**.

## Best-fit fonts (already bundled)

| Layer | Font | Why |
|---|---|---|
| Arabic QPC Hafs | `KFGQPC HAFS Uthmanic Script` (`UthmanicHafs1Ver18.ttf`) | Matches Quran Foundation `text_qpc_hafs`; verified here with libass + FriBidi + HarfBuzz, RTL and harakat intact. |
| English / reference | `Cormorant Garamond Light` (`CormorantGaramond-wght.ttf`) | Thin OFF-white serif that matches the black 9:16 verse-card look; SIL OFL 1.1. |

Fonts live in `${CLAUDE_PLUGIN_ROOT}/skills/quran-subtitles/fonts/`. License texts, provenance and SHA-256 hashes are
in [`licenses/NOTICE.md`](licenses/NOTICE.md). The script defaults to that font directory; pass `--font-dir`
explicitly when working from another checkout.

**Do not mix paired data and fonts:** QF `text_qpc_hafs` needs `UthmanicHafs1Ver18`; QuranEnc `Hafs_20` text needs
its own paired `Hafs_20.ttf` and a `--font-dir`/`--arabic-font` override; `text_uthmani` is not QPC Hafs text. One
ASS `Fontname` per Style, never a comma-separated fallback list. Avoid per-word RTL colour overrides because they
split bidi runs; use one plain Arabic run per cue (or karaoke `\k` if later needed).

## Parameters to settle with the human / job

| Decision | Flag / file |
|---|---|
| Verse range | `--range 19:30-33` (or `19:30`, `19:30-19:33`) |
| Canonical text source | `--verses <jobs/.../verses.json>`; `--quran-source "Quran Foundation"` for credits |
| Translation edition/resource | `--translation-edition`, `--translation-credit`, `--translation-overrides <json>`; verbatim text only |
| Audio / timing source | `--timings <jobs/.../timings.json>`, `--timing-source`, `--reciter`, `--audio`, `--auto-offset`, `--source-start-ms`, `--audio-start-ms` |
| Subtitle layers | `--layers header,arabic,english,ref` (disable any layer by omitting it) |
| Font override | `--font-dir`, `--arabic-font`, `--english-font`, `--arabic-size`, `--english-size` |
| Card layout | `--arabic-cpl`, `--arabic-lines`, `--header-y`, `--arabic-y`, `--english-y`, `--ref-y` |
| Rounded popup visual | `quran_visual.py` with `--background`, `--intro`, `--pop-duration`, `--popup-top`, `--popup-width`, `--popup-height`, `--radius`, `--dim` |
| Audio polish | `quran_audio_polish.py` with `--wet`, `--predelay`, `--target-lufs`, `--ceiling`: subtle hall reverb + clarity EQ; words and timing unchanged, wet pre-delay only so nothing repeats |
| Subtitle outputs | `--out <jobs/.../captions.ass>` (primary), `--srt <jobs/.../review.srt>` (review only) |
| QA / credits / final path | `--preview <jobs/.../preview.png>`, `--credits-out metadata/<slot>/credits.txt`, `--video-out outputs/<video-name>.mp4` |

`--out` ASS is the primary subtitle deliverable. SRT is **review-only**: most SRT renderers do not shape Uthmani
Arabic correctly. Keep both inside ignored `jobs/` unless the human explicitly approves a public subtitle asset.

## Verse-card popup layout

For the black-background / rounded-popup look, render a silent visual base first:

```bash
"$PY" "$ROOT/scripts/quran_visual.py" \
  --background assets/<reel>/background.mp4 \
  --out jobs/<id>/quran/visual_base.mp4 \
  --duration <seconds> --intro 0.8 --pop-duration 0.7 \
  --popup-top 380 --popup-width 1000 --popup-height 860 --radius 90 \
  --dim 0.10 --glow-strength 0.055 --border-strength 0.20
```

Then pass that visual as `--source-video` to `quran_subtitles.py`, add the trimmed recitation with `--audio`, and
move the caption layers below the popup:

```bash
--source-video jobs/<id>/quran/visual_base.mp4 \
--audio assets/<reel>/recitation.m4a \
--offset-ms 800 --video-duration <seconds> \
--header-y 270 --arabic-y 1275 --english-y 1450 --ref-y 1605 \
--arabic-size 62 --english-size 46 --header-size 36 --ref-size 28 \
--english-cpl 42 --arabic-cpl 36 --arabic-lines 2 --max-duration 15
```

`--offset-ms` must equal the silent `--intro` when the audio already includes that silence. Use `--preview` at
several cue midpoints and inspect a contact sheet from the final MP4; do not trust a single frame.

## Workflow

1. **Identify the exact audio, reciter, verse range, translation and rights.** If the audio is one of the QF/QUL
   chapter recitations, fetch its `segments=true` / With Segment data. If it is a social clip with a different
   reciter, use a Quran-specific aligner ([Tilawa Studio](https://github.com/oumarknt31/tilawa-studio),
   [QuranCaption](https://github.com/zonetecde/QuranCaption), [AyahFlow](https://ayahflow.ai/blog/how-to-make-quran-recitation-videos/))
   or manually inspect the waveform and write per-ayah timings. Clear audio rights before rendering.
2. **Fetch canonical text into `jobs/<id>/quran/verses.json`.** For QF use
   `https://api.quran.com/api/v4/verses/by_chapter/<surah>?words=true&word_fields=text_qpc_hafs&per_page=50&page=<n>`
   and select the requested verses; use the agent's web/fetch tools inside this sandbox. For QF timing use
   `https://api.quran.com/api/v4/chapter_recitations/<chapter_reciter_id>/<surah>?segments=true`; chapter-reciter
   IDs come from [`resources/chapter_reciters`](https://api.quran.com/api/v4/resources/chapter_reciters) and are not
   ayah-by-ayah recitation IDs. QUL's [With Segments](https://qul.tarteel.ai/docs/with-segments) is the equivalent
   word-timing source. Input shapes are in [`references/input-schema.md`](references/input-schema.md).
3. **Add the translation verbatim.** Prefer a rights-cleared published edition. Write a JSON object mapping
   `verse_key` to the exact translation text, with `_meta.translation_name` and `_meta.source_url`, and pass it via
   `--translation-overrides`. Do not paraphrase, summarise, machine-translate, or "fix" the published wording;
   strip only HTML display markup. The Clear Quran (QF resource 131) is copyrighted — use it only with permission;
   QuranEnc editions require unmodified text and strict publisher/source/version credit; Tanzil translations have
   non-commercial restrictions.
4. **Validate dry, then render ASS + preview.** Run `--dry-run --strict` first. Then generate `.ass`, `.srt`, credits
   and a PNG preview with `--font-dir "${CLAUDE_PLUGIN_ROOT}/skills/quran-subtitles/fonts"`. Use `--preview-time`
   at the midpoint of a cue, not at frame 0. Use `--auto-offset` when cutting an excerpt from full-surah audio; it
   shifts the first selected cue to 0 and the MP4 renderer trims the source/audio to the matching timestamp.
5. **Open the PNG and verify by eye.** Arabic letter order, harakat, waqf marks, ayah-number end markers, full
   `surah:ayah` references, English line breaks, timing and phone readability. Re-run with `--strict` until the QA
   list in [`references/quality-checklist.md`](references/quality-checklist.md) passes. A scholarly/text reviewer
   must confirm the canonical Arabic and named translation before posting.
6. **Render the final MP4 only after QA.** Pass `--video-out outputs/<video-name>.mp4` (naming rules in
   `docs/CATALOG.md`) with either
   `--source-video <recitation video>` or `--background <scenic image/video> --audio <recitation audio>`.
   `--layers`, `--dim`, `--fade-ms`, `--fps`, `--crf` and `--preset` control the look. Then run `rule-check`,
   show the MP4 + caption + `--credits-out` file to the human, and wait for "yes". Never post.

## Example

```bash
PY=/home/user/content-plug/.venv/bin/python
ROOT="${CLAUDE_PLUGIN_ROOT:-/home/user/content-plug/clip-desk}"
JOB=jobs/001_al-baqarah_2-152-153_yasser-ad-dussary
OUT=outputs/quran-001_al-baqarah_2-152-153_yasser-ad-dussary_en_1080x1920_v1.mp4

# 1. Validate the join before writing any subtitle file.
"$PY" "$ROOT/scripts/quran_subtitles.py" \
  --verses "$JOB/quran/verses.json" \
  --timings "$JOB/quran/timings.json" \
  --range 19:30-33 \
  --out "$JOB/quran/captions.ass" \
  --translation-overrides "$JOB/quran/translation.json" \
  --translation-edition "resource <id>" \
  --translation-credit "Named published translation" \
  --quran-source "Quran Foundation" \
  --timing-source "QF chapter_recitations/<id>/19?segments=true" \
  --reciter "Named reciter" \
  --font-dir "$ROOT/skills/quran-subtitles/fonts" \
  --layers header,arabic,english,ref \
  --surah-name "Surah Maryam" \
  --auto-offset --dry-run --strict

# 2. Render ASS, review SRT, credits and a phone-sized PNG preview.
"$PY" "$ROOT/scripts/quran_subtitles.py" \
  --verses "$JOB/quran/verses.json" \
  --timings "$JOB/quran/timings.json" \
  --range 19:30-33 \
  --out "$JOB/quran/captions.ass" \
  --srt "$JOB/quran/review.srt" \
  --translation-overrides "$JOB/quran/translation.json" \
  --translation-edition "resource <id>" \
  --translation-credit "Named published translation" \
  --quran-source "Quran Foundation" \
  --timing-source "QF chapter_recitations/<id>/19?segments=true" \
  --reciter "Named reciter" \
  --font-dir "$ROOT/skills/quran-subtitles/fonts" \
  --layers header,arabic,english,ref \
  --surah-name "Surah Maryam" \
  --auto-offset \
  --credits-out "metadata/001_al-baqarah_2-152-153_yasser-ad-dussary/credits.txt" \
  --preview "$JOB/quran/preview.png" \
  --preview-time 3.0 \
  --background "$JOB/quran/background.jpg" \
  --background-credit "Licensed background source"

# 3. After human visual/text/timing QA, render the final MP4.
#    Use --source-video instead of --background/--audio when the recitation is already a video.
"$PY" "$ROOT/scripts/quran_subtitles.py" \
  --verses "$JOB/quran/verses.json" \
  --timings "$JOB/quran/timings.json" \
  --range 19:30-33 \
  --out "$JOB/quran/captions.ass" \
  --translation-overrides "$JOB/quran/translation.json" \
  --translation-edition "resource <id>" \
  --translation-credit "Named published translation" \
  --quran-source "Quran Foundation" \
  --timing-source "QF chapter_recitations/<id>/19?segments=true" \
  --reciter "Named reciter" \
  --font-dir "$ROOT/skills/quran-subtitles/fonts" \
  --layers header,arabic,english,ref \
  --surah-name "Surah Maryam" \
  --auto-offset \
  --video-out "$OUT" \
  --background "$JOB/quran/background.jpg" \
  --audio "$JOB/quran/recitation.mp3" \
  --credits-out "metadata/001_al-baqarah_2-152-153_yasser-ad-dussary/credits.txt"
```

`--selftest` runs a synthetic non-Quran font/timing test with no network and writes only to `.cache/`:

```bash
"$PY" "$ROOT/scripts/quran_subtitles.py" --selftest --font-dir "$ROOT/skills/quran-subtitles/fonts"
```
