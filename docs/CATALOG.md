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

Anything not listed here is recoverable from `assets/quran/<slot>/SOURCE.md` and
`metadata/<slot>/post.json`.
