# ASSET-REGISTRY.md — what is used, what is spent, what is left

The rule the human set: **a new video gets a new clip.** This file is the memory that prevents
reusing one. Update it in the *same commit* that selects a clip.

## How to read this

- **Spent** — already used inside a delivered video. Never use again in a popup, thumbnail or b-roll.
- **Available** — present in the repo and already downloaded, never used.
- **Exhausted** — source known, but nothing usable/safe left in it.
- A clip is spent by its **pin id** (`e1_Afq…`) and by its **title/hash**, not just its file name, so
  a re-download of the same pin is still recognised as spent.

---

## Background video clips

### Spent

| Clip id | Pack | Slot used | Scene | Evidence |
|---|---|---|---|---|
| `e1_AfqPShx2sVLYlij3Z3y3YUURLZUKGojmRCUechmKqAJpT6VFjVHWVw` (candidate **008**, 89.0–108.16 s window) | `assets/quran/003_…` | 003 | cloud/mist-wrapped lush waterfall cliff, single 247.4 s drone shot | `assets/quran/003_…/selection.txt`, `SOURCE.md` |
| `e1_AfqPShzEtwAnD7ThMX5sHbgIPsLcRUnHp5Gze2TSoZqKuuDXknyc-g` (candidate **011**) | `assets/quran/002_…` | 002 | serene alpine emerald lake and mountainside chalets (32.6 s continuous) | `assets/quran/002_…/selection.txt`, `SOURCE.md` |
| `e1_AfqPShzBTTkHiKVQ5KOZPwXEUEyc8-0fQ8Dq9klY2aAfT2n2ADz_MQ` (candidate **012**) | `assets/quran/001_…` | 001 | riverside village, stone bridge, mist on green hills | `assets/quran/001_…/selection.txt`, `SOURCE.md` |
| Pinterest board “K” candidates **004, 005, 009** | — | — | blue river/forest, Swiss alpine lake montage, stormy coastal road | **deleted from the repo** during the 001 revision (multi-clip cut was rejected). Their pin ids are in `assets/quran/001_…/candidates.json` — treat them as spent too, so a re-import cannot quietly reuse them. |
| Pixabay **204756** “Sunset, Sunrise, Night” (`hsahmad472`) | `assets/quran/000_…` | 000 | sunset/sunrise sky | `assets/quran/000_…/SOURCE.md` |

### Available in the repo, never used

| Clip | Path | Length | Note |
|---|---|---|---|
| Pinterest **candidate 01 / 02 / 03 / 06 / 07 / 10** | *not in repo* — pruned for size, pin ids and thumbnails recorded in `assets/quran/001_…/candidates.json` | 6.5–248 s | Re-import from git blob at commit `422b92c` (path `assets/al-baqarah-2-152-153/pinterest_candidates/`) — **not** from Pinterest (pin ids expire); check this table first. |

### Board “K” — full candidate inventory (from `candidates.json`)

| # | Duration | Scene (from the contact sheet) | Status |
|---|---|---|---|
| 001 | 17.1 s | winding dark river, forest, stormy sky | **spent — video 004** (full clip at 0.9254×) |
| 002 | 11.1 s | man bending over water, river by houses | unused |
| 003 | 6.5 s | forest river, landscape 736×414 | unused (landscape, needs heavy crop) |
| 004 | 9.7 s | turquoise river, pine forest, cabins | **spent (deleted)** |
| 005 | 37.4 s | Swiss alpine: waterfall-village → lake → sunlit ridge → town street | **spent (deleted)** |
| 006 | 7.8 s | snow lake + prayer-rug POV, glacier wall | unused |
| 007 | 12.7 s | train-window view over green fields & clouds | unused (interior frame, not pure nature) |
| 008 | 247.4 s | cloud/mist-wrapped lush waterfall cliff, single drone shot | **spent — video 003** (89.0 s window) |
| 009 | 10.1 s | storm surf close-up → coastal road, dark green sea | **spent (deleted)** |
| 010 | 248.3 s | dramatic storm clouds over alpine road, 60 fps | unused (verify no car/branding in chosen window) |
| 011 | 32.6 s | lakeside town, emerald water & alpine chalets | **spent — video 002** |
| 012 | 18.1 s | riverside village, stone bridge, misty hills | **spent — video 001** |

Exact durations/resolutions/hashes: `assets/quran/001_al-baqarah_2-152-153_yasser-ad-dussary/candidates.json`.

---

## Recitations

| Slot | Reciter | QF id | Ayat | File | Status |
|---|---|---|---|---|---|
| 000 | Mishari Rashid al-ʿAfasy | 7 | 19:30–33 | `assets/quran/000_…/recitation.m4a` | spent |
| 001 | Yasser ad-Dussary | 97 | 2:152–153 | `assets/quran/001_…/recitation.m4a` | spent |
| 002 | Sheikh Ali Abdullah Jaber | mp3quran:76 | 2:155–157 | `assets/quran/002_…/recitation_raw.m4a` | spent |
| 003 | Sheikh Ali Abdullah Jaber | mp3quran:76 | 18:107–108 | `assets/quran/003_…/recitation_raw.m4a` | spent |

A recitation trim is spent for that verse+reciter pairing. Re-using the *same* audio for a *different*
verse card with a different background is allowed only if the human asks for a re-cut (that becomes
`_v2` of the same slot, not a new video).

---

## Translations

| Edition | Version | Used in | Status |
|---|---|---|---|
| `english_saheeh` — Noor International Center | v1.1.2 | 001, 002 | in use, credit it |
| `english_rwwad` — Rowwad Translation Center | v1.0.21 | 000, 003 | in use, credit it |

Rotating the edition between videos is a legitimate way to feel fresh; never mix two editions inside
one video, and never edit the wording.

---

## Fonts (shared, not spent)

| Font | File | License |
|---|---|---|
| KFGQPC HAFS Uthmanic Script | `clip-desk/skills/quran-subtitles/fonts/UthmanicHafs1Ver18.ttf` | KFGQPC free-use, no sale/modification; commercial release may need approval |
| Cormorant Garamond | `clip-desk/skills/quran-subtitles/fonts/CormorantGaramond[wght].ttf` | SIL OFL 1.1 |

Fonts are assets in the pipeline sense but are reusable by design — the "new asset" rule applies to
footage and recitations, not typefaces.
