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
| 001 | `quran-001_al-baqarah_2-152-153_yasser-ad-dussary_en_1080x1920_v1.mp4` | Al-Baqarah 2:152–153 | Yasser ad-Dussary | en | 26.20 s | 10.0 MB | `1059738c5cd9` | superseded by `_v2` |
| 001 | `quran-001_al-baqarah_2-152-153_yasser-ad-dussary_en_1080x1920_v2.mp4` | Al-Baqarah 2:152–153 | Yasser ad-Dussary | en | 27.00 s | 11.1 MB | `cd482005edfc` | **reference cut (v2)** — Frame-0 hook, 4 synced beats, emerald grade, breathing halo |

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
| 001 (v1) | Pinterest board “K” (`jawed1025t`) | candidate **012**, single continuous scene, slowed 1.4453× | 340 | hall polish, −14.5 LUFS | 780 px tall popup, 26.2 s |
| 001 (v2) | Pinterest board “K” (`jawed1025t`) | candidate **012**, single continuous scene, true 1000×780 aspect crop + emerald grade | 340 | hall polish + subtle stream air, −14.58 LUFS | Frame-0 optical open, 1.44 s quiet hook, 4 phoneme-synced beats, voice-breathing halo, progress filament, 27.0 s |

Anything not listed here is recoverable from `assets/quran/<slot>/SOURCE.md` and
`metadata/<slot>/post.json`.
