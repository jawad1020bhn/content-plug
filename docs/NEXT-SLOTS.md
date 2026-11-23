# NEXT-SLOTS.md — queue, pairings and kickoff for the next videos

Planning memory so slot `003+` starts in minutes. Source of truth for spend remains
`ASSET-REGISTRY.md`; look & sound remains `HOUSE-STYLE.md`; renderer templates `tools/quran_v2/`.

---

## 1. Background queue (board “K”, all still unused)

Original MP4s are **not** in the repo anymore; they live in git history at commit
`422b92c177ef5bd40a0761db318d1a7626a553f9` under `assets/quran/001_…/pinterest/`. Re-import with
`gh api repos/jawad1020bhn/content-plug/contents/<path>?ref=422b92c…` (base64 blob) — **do not**
re-fetch from Pinterest: pin ids (`e1_Afq…`) expire across sessions.

| # | Length | Scene | Fit notes |
|---|---|---|---|
| 001 | 17.1 s | winding dark river, forest, gloomy cloud | moody/reflective verses; cards ≤22 s at 1.3× |
| 002 | 11.1 s | man bending over water by houses | person in frame — avoid unless cropped out |
| 003 | 6.5 s | forest river, landscape 736×414 | landscape source: heavy crop, only for short cards |
| 006 | 7.8 s | snow lake + prayer-rug POV, glacier wall | winter/quiet verses; short cards only |
| 007 | 12.7 s | train-window view over green fields & clouds | interior frame — not pure nature |
| 008 | 247.4 s | cloud/mist-wrapped lush waterfall cliff, single drone shot | **spent — video 003** (89.0 s window) |
| 010 | 248.3 s | dramatic storm clouds over alpine road, 60 fps | long cards possible; verify no car/branding in window |

Long cards (≥35 s) have **one** unused long candidate left: **010** (248 s storm-cloud road —
scout the window for cars before use). Everything else unused is ≤17.1 s, so keep the verse
recitation ≤ clip×1.3 − 1 s (house stretch rule), or ask the human for a new clip.

## 2. Reciter × verse queue (timings already fetched & verified)

| Reciter | Source id | Verse | Length | Theme |
|---|---|---|---|---|
| Sheikh Ali Jaber | mp3quran `read=76` | 18:107–108 | 18.36 s | **spent — video 003** (Jannat al-Firdaws) |
| Sheikh Ali Jaber | mp3quran `read=76` | 2:186 | 20.32 s | nearness/duʿāʾ — “When My servants ask you of Me…” (fits clip 001 at 1.19×) |
| Sheikh Ali Jaber | mp3quran `read=76` | 2:285 | 29.82 s | īmān of the Prophet & believers — needs a new long clip |
| Sheikh Ali Jaber | mp3quran `read=76` | 2:255 (Ayat al-Kursī) | 45.34 s | **too long** for the house card; only as a human-approved special format |
| Sheikh Ali Jaber | mp3quran `read=76` | 2:286 | 45.92 s | too long (same caveat) |
| Yasser ad-Dussary | QF chapter-reciter `97` | any | per QF segments | proven voice of 001 |
| Mishari al-ʿAfasy | QF chapter-reciter `7` | any | per QF segments | proven voice of 000 |

mp3quran timing endpoint: `https://www.mp3quran.net/api/v3/ayat_timing?surah=<s>&read=<id>`;
audio CDN pattern `https://cdn.mp3quran.net/audio/<slug>/r1/<surah padded>.mp3` (eg `ali-jaber/r1/002.mp3`).
Audio import runs in GitHub Actions (`download.quranicaudio.com`/CDN egress lives there): add
`.github/triggers/fetch-quran-slot0NN.trigger` + push — `gh workflow run` returns 403, never works.

Thematic series so far: **ṣabr diptych complete** (001: 2:152–153 → 002: 2:155–157).
Natural next series: mercy & nearness (2:186), then tawakkul/comfort verses.

## 3. Translation rotation

`english_saheeh` v1.1.2 (Noor International) used in 001 **and** 002; rotated to
`english_rwwad` v1.0.21 (Rowwad Center) for 003. Keep rotating saheeh ↔ rwwad between videos —
one edition per video, verbatim, credited. Never The Clear Quran (resource 131) or Tanzil.

## 4. Kickoff checklist for slot NNN

1. `python tools/new_video.py --surah … --ayah … --reciter … --duration …` (scaffolds folders).
2. Trigger the Actions audio import (trigger file + push), then `git pull --ff-only`;
   verify the trim acoustically (silence ends ≈0.82–0.85 s, tail intact).
3. Fetch canonical QPC Hafs words + verbatim translation (`fetch_page`; hosts blocked in sandbox).
4. Build the beat map: mp3quran/QF timings → RMS/ZCR + `silencedetect` verification → `BEATS` list
   (rules in `HOUSE-STYLE.md` §7).
5. `cp tools/quran_v2/build_{audio,video}_template.py jobs/<slot>/build_{audio,video}.py`,
   edit the slot constants (README in `tools/quran_v2/`), rewrite the ambience bed for the new scene.
6. `build_audio.py` → check LUFS/TP + stereo-tail correlation; `build_video.py --test-preview` →
   inspect the 3 stills; full render.
7. `metadata/<slot>/`: `post.json`, `caption.txt`, `credits.txt`, `poster.png`, 8-panel `qa.png`;
   inspect by eye.
8. `ASSET-REGISTRY.md` (clip + recitation spent, translation row) + `CATALOG.md` row, same commit.
9. Show human MP4 + caption + credits → wait for explicit “yes” → post/PR only then.

## 5. Standing traps (read before every build)

- `ffmpeg`/`ffprobe` live in `.venv/bin` only — `export PATH="$PWD/.venv/bin:$PATH"`.
- No PIL in `.venv`; all text renders through libass (`ass=…:shaping=1`).
- ASS `Fontname` must be **`Cormorant Garamond Light`** (bare “Cormorant Garamond” → silent
  DejaVu Sans fallback).
- Python 3.11 f-strings: no backslashes inside `{}` — assign `\N`/`\move` tag strings first.
- Per-frame full-res blur = timeout; precompute sprites/masks (001 v2 lesson).
- `jobs/` is gitignored: it vanishes between sandboxes — templates live in `tools/quran_v2/`.
- `-ss`/`-t` **after** `-i` when trimming (000 lost its intro the other way).
- Pinterest pin ids expire; board-K originals come from git commit `422b92c`.
