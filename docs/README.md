# docs/ — the memory of this repo

Everything learned while building videos 000 and 001 lives here, so the next video is assembly, not
research. Read in this order.

| File | What it answers |
|---|---|
| [RECIPE.md](RECIPE.md) | "How do I build a video?" — every command, in order, with the proven numbers |
| [CATALOG.md](CATALOG.md) | "What exists already, what is it called, what's the next slot, did it get posted?" |
| [ASSET-REGISTRY.md](ASSET-REGISTRY.md) | "Which clip may I use?" — spent clips, available clips, recitations, translations |
| [PUBLISHING.md](PUBLISHING.md) | "What do I write in the caption/title?" — per-platform text and credit block |

## Folder contract (memorise this)

| Path | Holds | Git |
|---|---|---|
| `assets/quran/<NNN>_<slug>/` | background, recitation, chosen clip, `SOURCE.md`, `selection.txt`, `candidates.json`, contact sheet | **tracked** |
| `jobs/<NNN>_<slug>/` | verses, timings, translation overrides, ASS/SRT, polished audio, visual base, `build.sh` | ignored (regenerable) |
| `metadata/<NNN>_<slug>/` | `post.json`, `caption.txt`, `credits.txt`, `poster.png`, `qa.png` | **tracked** |
| `outputs/` | the delivered MP4s, nothing else | **tracked** |
| `content-inputs/` | raw human-supplied videos | tracked |

Rule of thumb: if losing it would cost a download or a 2-minute render, it goes in `jobs/`. If losing it
would cost information, it goes in `assets/`, `metadata/`, `outputs/` or `docs/`.

## Two commands that save the most time

```bash
# scaffold the next slot: creates the 3 folders, fills paths, durations and the
# background setpts factor, and writes jobs/<slot>/build.sh + JSON templates
.venv/bin/python tools/new_video.py --surah al-baqarah --ayah 2:255-255 \
  --reciter "Yasser ad-Dussary" --duration 22 --clip-seconds 18.133 --write

# catch caption/timing mistakes in ~2 s instead of after a 2-minute encode
.venv/bin/python clip-desk/scripts/quran_subtitles.py "${CAP_ARGS[@]}" --dry-run
```

## Decisions already made — do not re-litigate

- Reciter default: **Yasser ad-Dussary** (QF 97). Alternate: Mishari al-ʿAfasy (7).
- Translation default: **`english_saheeh` v1.1.2** (Noor International). Alternate: `english_rwwad`.
- Arabic: `text_qpc_hafs` + `UthmanicHafs1Ver18.ttf`, never mixed with another script/font family.
- Timing: QF `chapter_recitations/<id>/<surah>?segments=true`, valid only for that exact audio file.
- Composition: black card, one rounded popup, Arabic + English below, no burned credits, no UI.
- Background: **one continuous clip**, never one used before.
- Audio: hall polish (wet 0.15, 45 ms wet-only pre-delay), −14.5 LUFS, ≤ −1.5 dBTP.
- Mobile type: Arabic 62 px, **English 46 px**, header 36 px, reference 28 px at 1080×1920.
- Approval: show file + caption + credits, wait for an explicit "yes". No auto-posting, ever.

## Environment gotchas (each one already cost time once)

| Symptom | Cause / fix |
|---|---|
| `No module named numpy`, `ffprobe: No such file` | fresh sandbox — run `./setup.sh` (~2 min) |
| `jobs/` is empty though it had ASS + audio | `jobs/` is gitignored; re-fetch text/timing, re-run polish (TTS-free, fast) |
| `curl` to api.quran.com fails with SSL error | blocked in the sandbox; use `fetch_page`, and GitHub Actions for audio downloads |
| `git pull --ff-only` says "no tracking information" | use `git pull origin <branch> --ff-only` |
| recitation is 0.8 s short | `-t` placed before `-i`; put `-ss`/`-t` after the input |
| huge circular translucent overlay | old `border_mask` bug; fixed — keep `border_mask(outer, border, radius)` |
| English text overlapping the reference | recompute y-positions from Section 8 of RECIPE, don't eyeball |
| `MaxDownloadsReached` in the Pinterest importer | use `playlistend`, not `max_downloads` |
| workflow never runs | push the workflow file first; `gh workflow run` 404s until it is registered |
