# CATALOG.md — every delivered video

One row per delivered MP4 in `outputs/`. Slot numbers `NNN` are permanent: they appear in the output
filename, the asset folder, the metadata folder and social post bookkeeping, so never renumber them.

**Filename = the metadata.** Follow this convention exactly:

```
<surah-slug>-<NNN>_<surah>_<ayah-range>_<reciter-slug>_<lang>_<WxH>_v<version>.mp4
quran-001_al-baqarah_2-152-153_yasser-ad-dussary_en_1080x1920_v1.mp4
   │    │   │         │          │                    │  │         │
   │    │   │         │          │                    │  │         └ revision of the same cut
   │    │   │         │          │                    │  └ canvas (vertical 9:16)
   │    │   │         │          │                    └ caption language
   │    │   │         │          └ reciter (slugified, hyphens)
   │    │   │         └ ayah range as `first-last`
   │    │   └ surah name, snake_case
   │    └ slot number, zero-padded, unique forever
   └ series (only `quran` today)
```

Slug rules: lowercase ASCII, `[a-z0-9-]` only, no spaces, no apostrophes (`al-ʿAfasy` → `afasy`,
`ad-Dussary` → `yasser-ad-dussary`). Transliteration diacritics are dropped, never encoded.

A new version of the *same* cut gets `_v2` (keep `_v1` if it was already published). A different
verse, reciter, language or canvas gets a **new slot number**, never a new suffix.

---

## Delivered

| Slot | File | Surah / ayat | Reciter | Lang | Length | Size | SHA-256 (first 12) | Status |
|---|---|---|---|---|---|---|---|---|
| 000 | `quran-000_surah-maryam_19-30-33_afasy_en_1080x1920_v1.mp4` | Maryam 19:30–33 | Mishari al-ʿAfasy | en | 43.40 s | 22.2 MB | `455b8f2f484e` | first attempt, superseded in style by 001 |
| 001 | `quran-001_al-baqarah_2-152-153_yasser-ad-dussary_en_1080x1920_v1.mp4` | Al-Baqarah 2:152–153 | Yasser ad-Dussary | en | 26.20 s | 10.0 MB | `1059738c5cd9` | **reference cut** — one clip, polished audio, 46 px English |
| 002 | `quran-002_al-baqarah_2-155-157_ali-jaber_en_1080x1920_v1.mp4` | Al-Baqarah 2:155–157 | Sheikh Ali Jaber | en | 41.00 s | 29.4 MB | `b3607e4ef9df` | **review-ready** — narrowed 816×748 popup (Reels zoom safe), fake-scroll opener, raw clip colors, stereo Haram sanctuary audio |
| 003 | `quran-003_al-kahf_18-107-108_ali-jaber_en_1080x1920_v1.mp4` | Al-Kahf 18:107–108 (Jannat al-Firdaws) | Sheikh Ali Jaber | en | 19.16 s | 9.6 MB | `bfce7ca893b4` | **review-ready** — paradise theme, misty waterfall window at 1.0× stretch, Rowwad translation, same Haram stereo master |
| 003 | `quran-003_al-kahf_18-107-108_ali-jaber_en_1080x1920_v2.mp4` | Al-Kahf 18:107–108 (Jannat al-Firdaws) | Sheikh Ali Jaber | en | 19.16 s | 14.9 MB | `94ab32d6afdb` | **v2** — Slot 009 v5 styling, same waterfall and recitation |
| 009 | `quran-009_aal-e-imran_3-193-194_minshawi_en_1080x1920_v1.mp4` | Aal-e-Imran 3:193–194 | Mohamed Siddiq El-Minshawi | en | 48.02 s | 33.7 MB | `70537f4fe380` | **review-ready** — two complete ayahs at original pace, tall popup, Saheeh International |
| 009 | `quran-009_aal-e-imran_3-193-194_minshawi_en_1080x1920_v2.mp4` | Aal-e-Imran 3:193–194 | Mohamed Siddiq El-Minshawi | en | 48.02 s | 33.8 MB | `acb02945b7a2` | **v2 review-ready** — replacement train-window pin, top-aligned crop, whole layout 17 px higher |
| 009 | `quran-009_aal-e-imran_3-193-194_minshawi_en_1080x1920_v3.mp4` | Aal-e-Imran 3:193–194 | Mohamed Siddiq El-Minshawi | en | 48.02 s | 34.8 MB | `7e417f2f3f8c` | **v3 review-ready** — 16 px taller at the same width; entire layout another 23 px higher |
| 009 | `quran-009_aal-e-imran_3-193-194_minshawi_en_1080x1920_v4.mp4` | Aal-e-Imran 3:193–194 | Mohamed Siddiq El-Minshawi | en | 48.02 s | 35.9 MB | `45bb2853c9f7` | **v4** — 30 px taller at the same width; layout another 40 px higher |

Also present: `metadata/<slot>/` with `caption.txt`, `credits.txt`, `post.json`, `poster.png`, `qa.png`.

`000` was made before the revision rules existed (multi-clip background, 40 px English, no audio
polish). Treat `001` as the template; `000` is kept as history, not for posting.

---

## Social post tracker

Fill a row when (and only when) the human posts it. Numbers must be real screenshot values, never
projections.

| Slot | Platform | Posted (UTC) | URL | Views 24 h | Saves | Shares | Notes |
|---|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — | nothing posted yet |

---

## Per-video build facts

| Slot | Background source | Clip used | Popup top | Audio | Notes |
|---|---|---|---|---|---|
| 000 | Pixabay 204756 (`hsahmad472`) | full 8.8 s clip, looped | 380 | none (raw trim) | 43.4 s, 860 px tall popup |
| 001 | Pinterest board “K” (`jawed1025t`) | candidate **012**, single continuous scene, slowed 1.4453× | 340 | hall polish, −14.5 LUFS | 780 px tall popup, 26.2 s |
| 002 | Pinterest board “K” (`jawed1025t`) | candidate **011**, single continuous 32.6 s scene, slowed 1.257×, raw ungraded colors | 342 | stereo Masjid al-Haram sanctuary IR (3.2 s, 56 ms predelay), −14.3 LUFS | narrowed 816×748 popup (132 px side margins), fake-scroll opener, 7 beats, 41.0 s |
| 003 | Pinterest board “K” (`jawed1025t`) | candidate **008**, 89.0–108.16 s window of a 247.4 s single drone shot, 1.0× stretch, raw ungraded colors | 342 | same stereo Haram sanctuary IR as 002 (−14.22 LUFS measured), waterfall-mist ambience bed | 3 beats (18:107 ×2 + 18:108), Rowwad translation, 19.16 s |
| 003 v2 | same board “K” candidate 008 | same continuous waterfall window; crop raised slightly to keep cliff and falls visible | 121 | Identical AAC to 003 v1 | 860×1106 popup in the Slot 009 v5 layout; same three Rowwad beats and 19.16 s runtime |
| 004 | Pinterest board “K” (`jawed1025t`) | candidate **001**, full 17.2 s single continuous shot used whole at 0.9254×, raw ungraded colors | 342 | same stereo Haram sanctuary IR as 002 (−14.6 LUFS measured), dark-river ambience bed | 3 beats of 2:186, Saheeh translation, 15.88 s |
| 005 | Pinterest board “K” (`jawed1025t`) | candidate **010**, 130–146.2 s barrel-wave window of the 248.3 s montage (verified single continuous shot, 0 cuts) at 1.0×, raw ungraded colors | 342 | same stereo Haram sanctuary IR as 002 (−14.52 LUFS measured), dark-river ambience bed | 4 beats (19:30 ×2 + 19:31 ×2), Rwwad translation, voice-first 0.41 s, true-loop match-dissolve, v3: user pin 1119214944936119709 (horses, whole @1.083×, 2 cuts disclosed), Ref 66 / Header 70, 16.23 s |
| 006 | Pinterest board “K” (`jawed1025t`) | candidate **006**, first 5 s + ping-pong reverse of the 7.8 s prayer-mat pan (0 cuts), raw ungraded colors | 290 | same stereo Haram sanctuary IR as 002 (−14.67 LUFS measured), lake-water ambience bed | 2 beats (94:5 + 94:6), Saheeh translation, voice-first 0.47 s, Minshawi Murattal, 896×1000 popup (92 px black margins), exact-length mux, true-loop MAE 0.95, 11.63 s |
| 007 | Pinterest board “K” (`jawed1025t`) | candidate **002**, whole 11.08 s wudu→prayer arc at 0.803× (0 cuts), raw ungraded colors | 280 | RAW voice, zero processing (−13.95 LUFS natural), PCM-verified bit-transparent | 2 beats (14:40 split at waqf), Saheeh translation (rotation break, rwwad ungrammatical), Afasy, Mushaf Arabic 80, voice-first 0.42 s, 896×940 popup, loop MAE 0.83, 13.81 s |
| 008 | user pin (pin.it/TyccIFsfB, NOT board K) | pin **1119214944936149443**, 9.83 s road/valley/clouds ×5 with 0.4 s xfades (1427 f, seamless), mapped 0.805×, raw ungraded colors | 280 | RAW+gain: trim + static +5.5 dB only (−15.01 LUFS / −1.3 dBTP), no dynamics/EQ/reverb | 11 beats (20:13–17), Rowwad translation, Ghaith Samreen, Mushaf Arabic 80, voice-first 0.40 s, 916×940 popup (82 px black margins), loop MAE 0.87, 38.30 s |
| 009 | user pin (pin.it/69696p6RX) | pin **1119214944936118877**, 14.57 s landscape montage, internal dissolves and 0.4 s repetition crossfades, raw colors | 250 | Minshawi Murattal at native pace, boundary trims and spacing only (−15.65 LUFS / −1.28 dBTP) | 7 QF-timed beats, 860×1040 popup, subtle bokeh and stars, 0.485 loop-endpoint luma MAE, 48.02 s |
| 009 v2 | user pin (pin.it/7FdofUUxi) | pin **1119214944936118886**, 8.20 s train-window view, six passes with 0.4 s crossfades | 233 | Identical AAC to 009 v1 | 860×1040 top-aligned crop; entire layout shifted up 17 px, 0.474 loop-endpoint luma MAE |
| 009 v3 | same user pin as v2 | same source and top alignment as v2 | 210 | Identical AAC to 009 v2 | 860×1056 popup (16 px taller for this clip only); full layout 23 px above v2, 0.460 loop-endpoint luma MAE |
| 009 v4 | same user pin as v3 | same source and top alignment as v3 | 144 | Identical AAC to 009 v3 | 860×1086 popup, 30 px taller; 40 px layout lift from v3 verified on title, captions and progress line |

Anything not listed here is recoverable from `assets/quran/<slot>/SOURCE.md` and
`metadata/<slot>/post.json`.
