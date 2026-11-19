---
name: moment-finder
description: Find the best clip moments in a long video, stream VOD or local file. Use when the user gives a YouTube/Twitch URL or video file and wants highlights, "find the moments", or candidates to cut.
---

# Moment finder

Run:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/moments.py" <url-or-file> --top 8`

It writes `jobs/<id>/candidates.md`. Signals used: transcript with word timestamps (faster-whisper), loudness
spikes, the YouTube "most replayed" heatmap and live-chat spikes, when available. A missing signal is skipped,
not faked.

Then:

1. Read `jobs/<id>/candidates.md` and show each candidate: number, start-end, length, why it scored, transcript line.
2. Drop spoilers for a story/reveal the audience cares about, nudity, and anything that looks stolen or leaked.
3. Recommend the best 3 and say what hook angle each suggests.
4. Next step: `clip-cutter` with `--pick <n>`.

Record the source link and creator in `media/raw` notes. Credit the creator in the post caption.
