---
name: reaction-clips
description: Make reaction clips (face on top, source video below, big title on the seam) from the biggest live streamer or presenter in the niche. Use when the user wants reaction clips, "face on top" clips, stream clips, or asks who is streaming the niche right now.
---

# Reaction clips

Face on top, the thing being reacted to below, a big title on the seam. The format that travels in every
vertical feed, from games to cooking to podcasts to sport.

## 1. Find the streamer or presenter

`python "${CLAUDE_PLUGIN_ROOT}/scripts/streams.py" --query "<topic or Twitch category>"` lists the top live
streams on Twitch, YouTube and Kick, ranked by viewers. Pick a streamer who runs a clipping campaign (check
`campaigns.md`), or one whose clips you have permission to post.

## 2. Get the moment

- Live: `python "${CLAUDE_PLUGIN_ROOT}/scripts/live.py" https://twitch.tv/<login> --minutes 60` records the
  stream, reads Twitch chat anonymously and cuts a clip every time chat explodes.
- After the fact: `python "${CLAUDE_PLUGIN_ROOT}/scripts/moments.py" <twitch VOD, YouTube video or clip URL> --top 8`
  scores the video and writes `candidates.md`.

## 3. Cut the reaction clip

```
python "${CLAUDE_PLUGIN_ROOT}/scripts/cut.py" jobs/<id> --pick 1 --layout react --cam auto \
  --title "Marco REALIZED why the dough needed 24 HOURS" --title-style box --captions bubble
```

- `--cam auto` finds the streamer's webcam itself (face detection plus the webcam frame around it). It prints
  where it found the cam. If it finds no stable face it falls back to the blur layout and says so. Check the first
  frame once; if the crop is wrong, pass `--cam x:y:w:h` fractions.
- `--title-style box`: white band with bold black text on the seam. `--title-style outline`: white text with a
  thick black outline across the top of the footage, for short titles ("Fixing a Dead Lift").
- `--captions bubble`: white speech bubble ("Oh my god!"). `word`: word-by-word captions. `none`: title only.
- Write the title with `hook-writer` (reaction titles section).

## Rules

- Clip a creator only inside their campaign or with permission. Credit them in the post caption, not on the video.
- Titles describe what happened. Never invent a quote or an opinion.
- Run `rule-check` before posting. No spoilers in the title for a launch, finale or reveal.
- If the source is paywalled, private or clearly stolen, do not clip it.
