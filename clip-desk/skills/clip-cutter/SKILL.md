---
name: clip-cutter
description: Cut a picked moment into a finished 1080x1920 vertical clip with word-by-word captions, a hook box and an optional reaction title. Use after moment-finder, or when the user says "cut it", "make the clip", "make it vertical".
---

# Clip cutter

Run:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/cut.py" jobs/<id> --pick <n> --layout fill|blur|facecam|react --hook "TEXT"`

- `fill`: crop the source video to fill the frame. Default for footage shot wide with the action in the middle
  (gameplay, sport, a wide shot of a workshop).
- `blur`: full frame centered over a blurred copy. Use when cropping would cut off the subject (talking head,
  screen recording, charts, text on screen).
- `facecam`: the source video with the presenter's camera shown. Use for reactions, tutorials to camera.
- `react`: presenter's face on top, the source video below, optional `--title` on the seam (see `reaction-clips`).

Before running:

1. Get 3 hook options from the `hook-writer` skill and use the best one.
2. Check the audio is audible and the moment is complete (starts where the idea starts, ends on the payoff).

After running:

1. Output is an mp4 in `outputs/` (this workspace routes all deliverables there; see `docs/RECIPE.md`). Check it is 1080x1920, the hook shows in the first 2 seconds, captions are
   readable on a phone. No credit text is burned into the video; the poster credits the creator in the post.
2. Run `rule-check` on it. Fix and re-cut until it passes.
3. Trim 7 to 30 seconds for most clips. End on the payoff.
4. Show the human the file and the caption text, and ask for "yes". Do not upload anything.
