---
name: stream-finder
description: Find live streams about the page's topic on YouTube, Twitch and Kick, ranked by concurrent viewers. Use when the user asks who is streaming now, wants live moments to clip, or before live-mode.
---

# Stream finder

Run:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/streams.py" --query "<topic or Twitch category>"`

Use the niche's search term, or a Twitch category name when the niche is a game or genre ("Just Chatting",
"Minecraft", "Music", "Cooking"). Set `CLIP_DESK_TOPIC` once in the page folder's environment and `--query`
can be omitted.

Then:

1. Show the top 10 live streams: platform, channel, title, concurrent viewers, link.
2. Skip streams that are clearly stolen re-streams, paywalled content re-broadcast, or pirated copies. Say why in
   one line.
3. Recommend 1 to 3 streams. Prefer official channels and creators who allow sharing or who run a campaign.
4. Offer the next step: `live-mode <url> --minutes 60` to record and clip chat spikes, or `moment-finder` on a
   finished VOD.

Viewer counts are what the script returns at that moment. Do not guess or round them up. If a platform is marked
as unreachable (exit code 3), that section is unknown, not zero: use web search, or say which platform you could
not check instead of reporting "nobody is live".
