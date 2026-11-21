# Human QA checklist

Run `--dry-run --strict` first, then generate a PNG with `--preview` and **open it**. A passing script is not a
passing Quran caption.

## Text

- [ ] Canonical Arabic matches the selected authoritative source character-for-character, including hamza, madd,
      shadda, sukun and waqf marks. QPC Hafs text is paired with `UthmanicHafs1Ver18`; QuranEnc v20 text is paired
      with `Hafs_20`. No dotted boxes or fallback-glyph squares.
- [ ] Translation is verbatim from one named published edition; no machine translation, paraphrase, summarisation,
      added footnote text, or LLM "improvement".
- [ ] Verse references use the full `surah:ayah` form (`[19:31]`, not `[9:31]`). Ayah-number end markers are not
      duplicated inside the Arabic line.
- [ ] A qualified human has reviewed the Arabic and translation before posting.

## Render

- [ ] Arabic reads right-to-left; letters are connected in the correct order; harakat are not detached or stacked.
- [ ] One plain Arabic run per cue. No per-word RTL colour override that could split bidi order.
- [ ] English wraps at punctuation, max two lines, readable at 1080x1920 on a phone. No clipped glyphs.
- [ ] Black/dim background keeps off-white text legible; 25–35% dim and 300–500 ms fades are the starting point.
- [ ] Black intro reads as intentional; the rounded popup scales/fades in cleanly, with no clipped corners, square
      edges or visible loop seam. Popup border/glow stay subtle on a phone.
- [ ] Arabic and English captions sit **below** the popup, not over it; header, Arabic, English and reference do not
      overlap. Inspect a contact sheet with at least one frame per verse, not only the first frame.
- [ ] If the background is anime, it contains **neither people nor animals**.
- [ ] The ASS uses a single `Fontname` per Style; no comma-separated fallback list. `fontsdir` contains only font
      binaries, not README/license text files that libass may try to load.

## Timing / audio

- [ ] Cue start/end match the exact reciter/audio. QF/QUL timings were not reused on a different recording.
- [ ] Custom audio was aligned with a Quran-specific aligner/editor or manual waveform review.
- [ ] `--auto-offset` and source/audio start values sync the first word; no cue starts before the recitation.
- [ ] Waqf/semantic breaks are respected; long verses are split at a pause, not by shortening or deleting words.
- [ ] No overlapping cues. QF/QUL verse timings are often contiguous; check the transition visually and add a
      two-frame gap only if the renderer flickers. Reading speed is comfortable for the target audience.
- [ ] Audio rights are cleared. QF/translation/reciter/creator/background credits are in the post caption or
      description, **never burned into the video**.

## Repo / approval

- [ ] Raw QF/QUL API JSON and generated `.ass`/`.srt` with Quran text stay in ignored `jobs/<id>/quran/`.
- [ ] Final MP4 is in `media/edits/`; credits file is shown with it.
- [ ] `rule-check` passes. Show the human the MP4, caption and credits and wait for an explicit **"yes"**.
- [ ] Nothing is uploaded, scheduled or posted automatically.
