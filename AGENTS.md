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
- The "page folder" (campaigns.md, facts.md, jobs/, media/, ...) is created by the `setup`
  skill in a subfolder named after the page. All scripts resolve paths from the current
  working directory (or `CLIP_DESK_HOME`), so **run scripts with the page folder as cwd**.

## Niche settings (per page, not per repo)

The tools are niche-agnostic. Each page folder sets three environment defaults (the `setup` skill asks
for them and writes them down):

| Variable | Meaning | Example |
|---|---|---|
| `CLIP_DESK_TOPIC` | the niche in the words people search; default for `--query` / `--topic` | `"sourdough"`, `"mechanical keyboards"`, `"valorant"` |
| `CLIP_DESK_SUBS` | subreddits where the audience talks; default for `questions.py --subs` | `"Sourdough,Breadit,AskCulinary"` |
| `CLIP_DESK_HASHTAGS` | niche tags for the localized captions in `translate.py` | `"#sourdough #bread #baking"` |

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
| `check.py`, `payouts.py`, `secrets_map.py` | fully work (local only); `secrets_map.py` is the findings map, works for any niche. |
| `translate.py` | renders localized clips, but Google Translate and edge-tts hosts are blocked: translations keep the original text (warns) and `--voice` is skipped (warns). Treat it as a layout re-render here. Hashtags come from `CLIP_DESK_HASHTAGS`. |
| `trends.py`, `streams.py`, `live.py`, `questions.py` | **blocked**: they need youtube.com / twitch.tv / reddit.com via yt-dlp or HTTP. They fail with an error message; do not retry in a loop. |

For the online half of the workflow (campaign-finder, trend-radar, stream-finder,
questions-to-posts) use the agent's own **web search / page fetch tools** instead of these
scripts, then record findings into `campaigns.md` / `watchlist.md` / `idea-bank.md` as the
skills describe. Downloading source videos must happen on the human's machine; here, work
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
expect them to vanish). **Final deliverables live in `media/edits/` and small source assets
(images, VO) in `assets/<reel>/` — both tracked** so they persist in snapshots and git. `.venv/` also rebuilds per sandbox: run `./setup.sh` when
ffmpeg/python are missing. Keep turn-end sizes reasonable (~128 MB cap): prune `jobs/`
sources after a clip is delivered (keep `candidates.json`/`transcript.json`/`info.json`).

## Harness patches applied to the vendored plugin

1. `scripts/common.py` — `tool()` falls back to local `bin/` dirs and the venv's own bin dir.
2. `scripts/facecam.py` — prefer the model shipped at `clip-desk/models/` (upstream
   download URL redirects to a blocked host); falls back to the original cache path/download.
3. `scripts/moments.py` — if the whisper model cannot be downloaded, continue with
   loudness-only scoring instead of crashing.
4. `scripts/translate.py` — if edge-tts is unreachable, render without the voice instead of
   crashing the batch.
