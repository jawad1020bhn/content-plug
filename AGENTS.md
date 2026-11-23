# AGENTS.md — running the Clip Desk in this workspace

This repo holds the `clip-desk` plugin (MIT): a niche-agnostic content-creation desk. It started
as a fork of an MIT-licensed fandom clipping plugin (github.com/Bodila51/gtavi-claudecode,
audited at install time, commit `dd95d393` of `main`); every fandom-specific behaviour has been
replaced with inputs you set per page. It carries small harness patches (listed at the bottom).
This file is the harness-agnostic guide to running it here.

## Layout

- `clip-desk/` — the plugin: `scripts/` (Python tools), `skills/` (workflow guides,
  read the matching `skills/<name>/SKILL.md` before running a tool), `models/` (YuNet face
  detection model, sha256-verified against opencv_zoo).
- `.venv/` — Python 3.11 env with all requirements + static `ffmpeg`/`ffprobe`.
  Not snapshotted: if missing, run `./setup.sh` (needs pypi.org + registry.npmjs.org only).
- `AGENTS.md`, `setup.sh`, `.gitignore` — harness glue.
- `assets/quran/<NNN>_<slug>/` — source assets per video: background, recitation, chosen clip,
  `SOURCE.md` (provenance/rights), `selection.txt`, `candidates.json` + contact sheet. Tracked.
- `jobs/<NNN>_<slug>/` — regenerable intermediates only (verses, timings, ASS/SRT, polished audio,
  visual base). **Ignored**: expect it to vanish between sandboxes.
- `metadata/<NNN>_<slug>/` — the post package: `post.json`, `caption.txt`, `credits.txt`,
  `poster.png`, `qa.png`. Tracked.
- `outputs/` — **finished MP4s only**, one file per video, named by the `docs/CATALOG.md` convention.
  Tracked. Nothing else goes here.
- `docs/` — `RECIPE.md` (how to build a video end to end), `CATALOG.md` (every delivered video +
  filename grammar + post tracker), `ASSET-REGISTRY.md` (what is spent, what is left),
  `PUBLISHING.md` (per-platform captions/titles/credits), `HOUSE-STYLE.md` (proven look & sound
  spec of the v2 card), `NEXT-SLOTS.md` (background/reciter/translation queue + kickoff checklist).
- `tools/quran_v2/` — durable copies of the proven v2 renderer (`build_audio_template.py`,
  `build_video_template.py` from slot 002) + README of per-slot edit points. `jobs/` is ignored,
  so this is the copy that survives between sandboxes.
- `content-inputs/` — the human's raw source video(s) for a delivery (tracked).
- The generic "page folder" (campaigns.md, facts.md, jobs/, media/, ...) can still be created by the
  `setup` skill in a subfolder named after the page; its scripts resolve paths from the cwd (or
  `CLIP_DESK_HOME`), so **run page-folder scripts with that folder as cwd**. The Quran pipeline above
  runs from the repo root instead.

## Niche settings (per page, not per repo)

The tools are niche-agnostic. Each page folder sets three environment defaults (the `setup` skill asks
for them and writes them down):

| Variable | Meaning | Example |
|---|---|---|
| `CLIP_DESK_TOPIC` | the niche in the words people search; default for `--query` / `--topic` | `"sourdough"`, `"mechanical keyboards"`, `"valorant"` |
| `CLIP_DESK_SUBS` | subreddits where the audience talks; default for `questions.py --subs` | `"Sourdough,Breadit,AskCulinary"` |
| `CLIP_DESK_HASHTAGS` | niche tags for the localized captions in `translate.py` | `"#sourdough #bread #baking"` |
| `CLIP_DESK_BANNED` | extra terms `check.py` fails on before posting (brand claims, forbidden words) | `"gluten free guarantee,miracle cure"` |

## How to run the tools

```bash
# from the page folder (example):
/home/user/content-plug/.venv/bin/python /home/user/content-plug/clip-desk/scripts/moments.py video.mp4 --top 8
/home/user/content-plug/.venv/bin/python /home/user/content-plug/clip-desk/scripts/cut.py jobs/<id> --pick 1 --layout blur --hook "..."
/home/user/content-plug/.venv/bin/python /home/user/content-plug/clip-desk/scripts/check.py jobs/<id>/edits/clip_1.mp4 --campaign campaigns.md
```

`common.py tool()` finds `ffmpeg`/`ffprobe` in `.venv/bin/` automatically. Scripts are
importable from each other regardless of cwd. Always follow the skill guide for the tool
you are running (argument meanings, review steps, approval gates).

## What works inside this sandbox (offline pipeline)

Sandbox egress is allowlisted (github.com, pypi.org, registry.npmjs.org, ...), so:

| Tool | Status |
|---|---|
| `moments.py <local file>` | works, **loudness-only**: faster-whisper's model host (huggingface.co) is blocked, so no transcript → no word captions, no hype-word signal. If a `transcript.json` for the job already exists it is used as-is. |
| `cut.py` | fully works (ffmpeg + opencv + local YuNet model). Captions render only when a transcript exists. |
| `facecam.py` | fully works (model is local, sha256 `8f2383e4...` = opencv_zoo). |
| `arabic_version.py` | burns a localized (RTL) caption track over a clip whose captions live in bars: finds the English bar per line, draws an Arabic bar in the same place, fits the font, `--vo` mixes the dub over a ducked bed and normalises to -14 LUFS. Re-run `--script` with re-timed lines after the VO is conformed. |
| `quran_subtitles.py` | fully works offline with user-supplied canonical text/timing JSON (see `skills/quran-subtitles`): joins QPC Hafs words, one verbatim named translation and exact QF/QUL segment times, writes RTL-safe ASS + review SRT/credits/PNG, and optionally renders `outputs/*.mp4` with libass `shaping=1`. Bundled best-fit fonts are KFGQPC Uthmanic Hafs + Cormorant Garamond. `--selftest` proves the fonts without network; no ASR, no machine translation, no raw QF data in the repo, no posting. |
| `quran_audio_polish.py` | fully works offline with numpy + static ffmpeg: adds a subtle synthetic-hall reverb send (pre-delay on the wet path only, so no word repeats), rumble/presence EQ, gentle compression, peak limiting and loudness matching. Never time-stretches, pitch-shifts or re-cuts the recitation, so QF timings stay exact. |
| `quran_visual.py` | fully works offline with OpenCV/numpy + static ffmpeg: builds the black 9:16 verse-card visual base, black intro, rounded animated background-video popup, soft glow/shadow/border and slow push-in. Draws no text/credits; `quran_subtitles.py` adds the canonical captions and audio. |
| `remove_captions.py` | removes captions (see `skills/caption-removal`). **Soft subtitle tracks**: ffmpeg stream copy, lossless, seconds. **Burned-in text**: `--selftest` proves the detector without any model; `--detect` reports the bands; the fill is handed to an external VSR checkout (`--vsr-home`, Apache-2.0, ~1.7 GB, never inside this repo) — LaMa is verified to work (`content output/caption_removal_vsr.png`) at 3.6 s/frame on CPU. OpenCV fill does not work; never ship its grey band. Missing VSR exits 3 with setup steps; `--rights` mandatory; `--dry-run` shows the hand-off. |
| `dewatermark.py` | fully works offline (ffmpeg + OpenCV, CPU only; no model, no network). `--selftest` proves the engine (97% on a synthetic mark); `--probe` reports where a pale mark sits and suggests a calibration it has *verified* against the overlay model. For footage the human **owns or licensed** — `--rights` is mandatory. On a soft, per-shot-scaled overlay expect fading, not erasure: read the skill before promising a clean result. |
| `check.py`, `payouts.py`, `secrets_map.py` | fully work (local only); `secrets_map.py` is the findings map, works for any niche. |
| `translate.py` | renders localized clips. Google Translate and edge-tts hosts are blocked, so pass `--translations <file.json>` with the wording you translated yourself (`{"es": {"<original>": "<translated>"}}`); anything missing keeps the original and is listed as `NOT TRANSLATED` in `clip_<n>_captions.md`. `--voice` is skipped here (warns). Hashtags come from `CLIP_DESK_HASHTAGS`. |
| `trends.py`, `streams.py`, `live.py`, `questions.py` | **blocked**: they need youtube.com / twitch.tv / reddit.com via yt-dlp or HTTP. They fail with an error message; do not retry in a loop. |

For the online half of the workflow (campaign-finder, trend-radar, stream-finder,
questions-to-posts) use the agent's own **web search / page fetch tools** instead of these
scripts, then record findings into `campaigns.md` / `watchlist.md` / `idea-bank.md` as the
skills describe.

Reachability through the agent's own tools (checked, not assumed): YouTube search pages, individual
watch pages (with transcript and chapter timestamps) and Google/Bing results all fetch fine; **Reddit's
`.json` API returns 403** (search snippets still work, and `fetch_page` on a normal reddit.com thread can
work); Twitch/Whop/Clip pages load. **Nothing in the sandbox can download a video file** — the container
itself can only reach github/pypi/npm, so source media must be attached by the human (or a URL fetched on
their machine). Turn paths that need per-view numbers (views/hour, live viewer counts) into web-search
findings, or say which numbers you could not verify instead of guessing.

These scripts now fail loudly instead of faking an empty result: `trends.py` writes a
`NOT A RESULT` header and exits 1, `streams.py` marks the unreachable platform and exits 3,
`questions.py` says Reddit was unreachable for every subreddit and exits 1. **Never turn any of
those into "nothing is trending / nobody is live / nobody is asking" in a report or a post.** Downloading source videos must happen on the human's machine; here, work
from files the human attaches.

## Hard rules carried over from the plugin (non-negotiable)

1. Never upload or post anything automatically. Every post needs the human's explicit "yes";
   they post it themselves. Show file path + caption + credit and wait.
2. No leaks, no "play early"/piracy, no stolen or paywalled material, no exploits that break a
   platform's rules, no fake news, never pretend to be the brand/publisher the page covers.
   Every fact needs a primary or named source link.
3. Credit the creator in the post caption. Never burn credit text into the video.
4. Real numbers only in `scoreboard.csv` / `payouts.csv`; never invent or project earnings.
5. Stock TTS voices only; never clone or imitate a real person's voice.

## Workspace budget & persistence rules

**The platform snapshot respects `.gitignore`**: anything ignored is lost between turns.
`jobs/`, `media/raw/` and `media/official/` are ignored (heavy, regenerable intermediates —
expect them to vanish). **Final deliverables live in `outputs/`, post packages in `metadata/`, and
small source assets in `assets/quran/<slot>/` — all tracked** so they persist in snapshots and git.
`.venv/` rebuilds per sandbox: run `./setup.sh` when ffmpeg/python are missing. Keep turn-end sizes
reasonable (~128 MB cap): prune `jobs/` sources after a video is delivered (keep
`candidates.json`/`transcript.json`), and delete unselected candidate clips from
`assets/quran/<slot>/pinterest/` as soon as one is chosen.

## Quran video workflow — read these first

1. `docs/RECIPE.md` — the full build, with the proven numbers.
2. `docs/ASSET-REGISTRY.md` — **pick a clip that is not spent**, and mark the new one spent.
3. `docs/CATALOG.md` — next free slot number and the output filename grammar.
4. `docs/PUBLISHING.md` — caption/title/credit text per platform.

## Harness patches applied to the vendored plugin

1. `scripts/common.py` — `tool()` falls back to local `bin/` dirs and the venv's own bin dir.
2. `scripts/facecam.py` — prefer the model shipped at `clip-desk/models/` (upstream
   download URL redirects to a blocked host); falls back to the original cache path/download.
3. `scripts/moments.py` — if the whisper model cannot be downloaded, continue with
   loudness-only scoring instead of crashing.
4. `scripts/translate.py` — if edge-tts is unreachable, render without the voice instead of
   crashing the batch.
5. Repo-level output convention: deliverables go to `outputs/` (not `media/edits/`), sources to
   `assets/quran/<slot>/`, post metadata to `metadata/<slot>/`. `quran_subtitles.py` warns when
   `--video-out` is outside `outputs/`.
