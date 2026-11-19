---
name: trend-radar
description: Rank recent videos on the page's topic by views per hour to see what is trending now. Use when the user asks what is hot, what to clip today, or wants fresh source videos.
---

# Trend radar

Run:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/trends.py" --query "<topic>" --hours 24 --limit 30`

Use the niche's main search term, or a narrower angle for the day (a product, an event, a creator name, a
question people are asking). Set `CLIP_DESK_TOPIC` to skip `--query`. Change `--hours` for a wider window.

Then:

1. Show the top 10 as a short table: title, channel, views, views per hour, age, link.
2. Pick 3 that fit the page's niche angle and that the page can add value to (not plain re-uploads of the same
   moment everyone posts).
3. Flag any that look stolen, paywalled or leaked: drop them and say so.
4. Offer the next step for the picks: `moment-finder <url> --top 8`.

If the script errors, show the last error line and fix the cause (missing yt-dlp, network). Do not invent a list.
