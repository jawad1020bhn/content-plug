# Input JSON shapes

The helper accepts QF/QUL-style JSON or small normalized dictionaries. Examples below use synthetic placeholder
strings, not Quran text. Keep real fetched data in ignored `jobs/<id>/quran/`; do not commit raw QF API responses.

## Verses

### QF `by_chapter` / `by_key` shape

`--verses` may be the full API object, its `verses` list, a single `{"verse": {...}}`, or a list of `{"verse": {...}}`
wrappers. `join_qpc_words()` joins `words[].text_qpc_hafs` and drops `char_type_name:"end"` ayah-number markers.

```json
{
  "verses": [
    {
      "verse_key": "1:1",
      "text_uthmani": "نص عربي",
      "words": [
        {"position": 1, "char_type_name": "word", "text_qpc_hafs": "نص"},
        {"position": 2, "char_type_name": "word", "text_qpc_hafs": "عربي"},
        {"position": 3, "char_type_name": "end", "text_qpc_hafs": "١"}
      ],
      "translations": [
        {"resource_id": 0, "resource_name": "Named translation", "text": "Published translation text."}
      ]
    }
  ]
}
```

If the publisher's translation is supplied separately (recommended for rights control), use
`--translation-overrides`. The helper strips display HTML only; it does not alter wording.

```json
{
  "_meta": {
    "translation_name": "Named published translation",
    "source_url": "https://publisher.example/translation"
  },
  "1:1": "Published translation text, verbatim."
}
```

### Normalized shape

```json
{
  "translation_name": "Named published translation",
  "source_url": "https://publisher.example/translation",
  "verses": [
    {
      "verse_key": "1:1",
      "arabic": "نص عربي",
      "translation": "Published translation text.",
      "translation_name": "Named published translation"
    }
  ]
}
```

A plain list of verse objects also works. `arabic_source` is inferred as `text_uthmani_or_other` for normalized
input, so `--strict` warns; use QF `words`/`text_qpc_hafs` with `UthmanicHafs1Ver18` when possible. For QuranEnc,
use its **paired** `Hafs_20` text and font instead and override `--font-dir`/`--arabic-font`.

## Timings

### QF `chapter_recitations` shape

`--timings` may be the full API object, its `audio_file` object, a `timestamps` list, or a normalized list.
`segments` word triplets are kept for QA but the current ASS uses verse-level `timestamp_from/to`.

```json
{
  "audio_file": {
    "audio_url": "https://download.example/surah.mp3",
    "timestamps": [
      {
        "verse_key": "1:1",
        "timestamp_from": 0,
        "timestamp_to": 2500,
        "duration": 2500,
        "segments": [[1, 0, 2400]]
      },
      {
        "verse_key": "1:2",
        "timestamp_from": 2500,
        "timestamp_to": 5000,
        "duration": 2500,
        "segments": [[1, 2500, 4900]]
      }
    ]
  }
}
```

### QUL / normalized shapes

QUL-like dictionaries keyed by `verse_key` are accepted when values are objects. A normalized list is simplest:

```json
[
  {"verse_key": "1:1", "start_ms": 0, "end_ms": 2500},
  {"verse_key": "1:2", "start_ms": 2500, "end_ms": 5000}
]
```

Recognised start/end names: `start_ms`/`end_ms`, `timestamp_from`/`timestamp_to`, `from`/`to`, `start`/`end`.
`duration_ms` or `duration` can fill a missing end/start. All values are milliseconds.

## Verse range

`--range 19:30`, `--range 19:30-33`, or `--range 19:30-19:33`. The helper refuses ranges crossing surahs; make one
job per surah. `--auto-offset` shifts the first selected cue to zero and lets the MP4 renderer trim full-surah
audio/video to its original first-cue timestamp. Use `--offset-ms`, `--source-start-ms` and `--audio-start-ms` for
manual sync overrides.
