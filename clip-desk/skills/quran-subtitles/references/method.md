# Why this method wins

Ranked result of the Quran-caption research done before this skill was registered. Do not replace it with generic
auto-captions.

## 1. Canonical text + named translation + exact segment timing + ASS/libass

- **Arabic:** Quran Foundation `text_qpc_hafs` word arrays joined in order, with `char_type_name:"end"` ayah-number
  markers removed. Use `text_uthmani` only when the chosen font is actually compatible with that script; do not mix
  it with a QPC Hafs font. Docs: [QF font rendering](https://api-docs.quran.com/docs/tutorials/fonts/font-rendering/), [verses by chapter](https://api-docs.quran.com/docs/content_apis_versioned/4.0.0/verses-by-chapter-number/).
- **Translation:** one named, rights-cleared published edition, reproduced verbatim. Do not let an LLM rewrite or
  machine-translate it. [QF Developer Terms](https://api-docs.quran.com/legal/developer-terms/) and [Connected Apps / AI rules](https://api-docs.quran.com/docs/connected-apps/) forbid rewriting canonical Arabic and named translations; [QuranEnc API terms](https://quranenc.com/en/home/api/) require unmodified text and named publisher/source/version credit; [Tanzil](https://tanzil.net/download/) translations are non-commercial unless permission is granted. QF resource 131 (The Clear Quran) is copyrighted/all rights reserved.
- **Timing:** QF `chapter_recitations/{chapter_reciter_id}/{surah}?segments=true` gives `timestamp_from/to` and word
  triplets, or QUL [With Segments](https://qul.tarteel.ai/docs/with-segments) gives word start/end timings. Docs: [QF chapter-reciter audio files](https://api-docs.quran.com/docs/content_apis_versioned/4.0.0/chapter-reciter-audio-file/), [chapter reciters](https://api-docs.quran.com/docs/content_apis_versioned/4.0.0/chapter-reciters/). These timings belong to the exact reciter/audio; do not apply them to a different recording.
- **Render:** ASS with one `Fontname` per style and libass complex shaping (`shaping=1`, FriBidi + HarfBuzz). The
  bundled `UthmanicHafs1Ver18.ttf` family is `KFGQPC HAFS Uthmanic Script`; English uses `Cormorant Garamond Light`. This was visually verified in the workspace: Arabic RTL/harakat and the thin serif translation render correctly. SRT is a review artifact, not the primary render path.
- **QA:** scholarly/text/timing human review, phone-sized PNG still, waveform check, license check, then final MP4.
  See [`quality-checklist.md`](quality-checklist.md).

## 2. Custom recitation audio: Quran-specific forced alignment

If the audio is not the exact QF/QUL recitation, use a Quran-aware aligner/detector or manual waveform review:

- [Tilawa Studio](https://github.com/oumarknt31/tilawa-studio): wav2vec2 Quran forced alignment, recitation
  detection, waqf/breath splits and Arabic shaping.
- [QuranCaption](https://github.com/zonetecde/QuranCaption): editor with assisted verse timing and translations.
- [AyahFlow](https://ayahflow.ai/blog/how-to-make-quran-recitation-videos/) / [best Quran video maker](https://ayahflow.ai/blog/best-quran-video-maker/): vendor workflow notes (canonical text, KFGQPC font, waqf breaks, serif translation). Treat as workflow evidence, not canonical text authority.

Write the result as a normalized timing JSON and pass `--timings`; keep the exact audio and reciter name with the job.

## 3. Manual editor timing

A manual CapCut/Premiere pass gives full control and is acceptable when the reciter/audio is unusual, but it is
slow and still needs canonical text plus a font/timing/rights review. Never start from conversational ASR text.

## Rejected

- Generic CapCut, Submagic, Zeemo, Captions.ai, Whisper/faster-whisper and other conversational ASR: madd/tajwid,
  missing tashkeel, wrong words, no verse boundaries, and no canonical source.
- Machine translation or paraphrase of the Quran/translation.
- QF/QUL/Quran.com timings reused on arbitrary audio without alignment.
- `quran-subtitle-generator`'s per-verse-duration fallback for precise work: it can drift; prefer its Quran.com
  timing mode or QF segment data. [Project](https://github.com/IslomTV/quran-subtitle-generator).
- `cpfair/quran-align` 2017 segmented data as the primary source for custom audio: old EveryAyah-specific data.
- QF raw API JSON committed to a public repo. Social videos are not redistribution when QF is credited in the
  caption/description/credits, but raw data files are. See [QF Developer Terms](https://api-docs.quran.com/legal/developer-terms/).

## Legal / credit summary

- Credit "Quran data provided by Quran Foundation." in the post caption/description when using QF data, plus the
  named translation, reciter, KFGQPC font, and the original creator/background where applicable. Do not burn credit
  text into the video.
- KFGQPC font: restricted KFGQPC EULA — use/copy/distribute subject to conditions, no sale/modification/reverse
  engineering; consult the publisher for a production/commercial release. Full EULA in
  [`../licenses/LICENSE-KFGQPC.txt`](../licenses/LICENSE-KFGQPC.txt) and provenance in [`../licenses/NOTICE.md`](../licenses/NOTICE.md).
- Cormorant Garamond: SIL OFL 1.1. Full text in [`../licenses/OFL-CormorantGaramond.txt`](../licenses/OFL-CormorantGaramond.txt).
- Clear audio and translation rights before rendering; a social clip's trending audio is not automatically licensed.
- Respect QF caching limits and do not use QF Content for ML training/fine-tuning/evaluation.
