# AGENTS.md — running the GTA 6 Clip Desk in this workspace

This repo vendors the `gtavi-claudecode` plugin (github.com/Bodila51/gtavi-claudecode, MIT,
audited at install time, commit `dd95d393` of `main`) with small harness patches (listed at
the bottom). The plugin was written for Claude Code (`/plugin install`, `CLAUDE_PLUGIN_ROOT`,
`.venv\Scripts\python`). This file is the harness-agnostic replacement for those conventions.

## Layout

- `gtavi-claudecode/` — the plugin: `scripts/` (Python tools), `skills/` (workflow guides,
  read the matching `skills/<name>/SKILL.md` before running a tool), `models/` (YuNet face
  detection model, sha256-verified against opencv_zoo).
- `.venv/` — Python 3.11 env with all requirements + static `ffmpeg`/`ffprobe`.
  Not snapshotted: if missing, run `./setup.sh` (needs pypi.org + registry.npmjs.org only).
- `AGENTS.md`, `setup.sh`, `.gitignore` — harness glue.
- The "page folder" (campaigns.md, facts.md, jobs/, media/, ...) is created by the `setup`
  skill in a subfolder named after the page. All scripts resolve paths from the current
  working directory (or `CLIP_DESK_HOME`), so **run scripts with the page folder as cwd**.

## How to run the tools

```bash
# from the page folder (example):
/home/user/stream-plug/.venv/bin/python /home/user/stream-plug/gtavi-claudecode/scripts/moments.py video.mp4 --top 8
/home/user/stream-plug/.venv/bin/python /home/user/stream-plug/gtavi-claudecode/scripts/cut.py jobs/<id> --pick 1 --layout blur --hook "..."
/home/user/stream-plug/.venv/bin/python /home/user/stream-plug/gtavi-claudecode/scripts/check.py jobs/<id>/edits/clip_1.mp4 --campaign campaigns.md
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
| `check.py`, `payouts.py`, `secrets_map.py` | fully work (local only). |
| `translate.py` | renders localized clips, but Google Translate and edge-tts hosts are blocked: translations keep the original text (warns) and `--voice` is skipped (warns). Treat it as a layout re-render here. |
| `trends.py`, `streams.py`, `live.py`, `questions.py` | **blocked**: they need youtube.com / twitch.tv / reddit.com via yt-dlp or HTTP. They fail with an error message; do not retry in a loop. |

For the online half of the workflow (campaign-finder, trend-radar, stream-finder,
questions-to-posts) use the agent's own **web search / page fetch tools** instead of these
scripts, then record findings into `campaigns.md` / `watchlist.md` / `idea-bank.md` as the
skills describe. Downloading source videos must happen on the human's machine; here, work
from files the human attaches.

## Hard rules carried over from the plugin (non-negotiable)

1. Never upload or post anything automatically. Every post needs the human's explicit "yes";
   they post it themselves. Show file path + caption + credit and wait.
2. No leaks, no "play early"/piracy, no GTA Online money glitches/AFK bots, no fake news,
   no pretending to be Rockstar. Every fact needs an official source link.
3. Credit the creator in the post caption. Never burn credit text into the video.
4. Real numbers only in `scoreboard.csv` / `payouts.csv`; never invent or project earnings.
5. Stock TTS voices only; never clone or imitate a real person's voice.

## Workspace budget

Turn-end snapshots are capped (~128 MB). Video jobs are heavy: after presenting a finished
clip, prune `jobs/<id>/source.mp4`, `audio.wav` and `live/seg_*.ts` when no longer needed
(keep `candidates.json`, `transcript.json`, `edits/`, `info.json` — they are small and let
`cut.py` re-render). `jobs/` and `media/` are gitignored.

## Harness patches applied to the vendored plugin

1. `scripts/common.py` — `tool()` falls back to local `bin/` dirs and the venv's own bin dir.
2. `scripts/facecam.py` — prefer the model shipped at `gtavi-claudecode/models/` (upstream
   download URL redirects to a blocked host); falls back to the original cache path/download.
3. `scripts/moments.py` — if the whisper model cannot be downloaded, continue with
   loudness-only scoring instead of crashing.
4. `scripts/translate.py` — if edge-tts is unreachable, render without the voice instead of
   crashing the batch.
