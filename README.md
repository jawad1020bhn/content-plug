# content-plug

A faceless content-creation desk for **any niche** — not one fandom. The plugin lives at [`clip-desk/`](clip-desk/)
(MIT) and is adapted to the Arena agent harness.

It finds campaigns and trends on your topic, scores long videos for the best moments, cuts 1080x1920 clips with
captions and hooks, checks them against campaign rules, localizes them, and runs a learning loop on real numbers.
Nothing is posted automatically: you approve every post.

- **Audit + install notes, and how to run everything here:** see [AGENTS.md](AGENTS.md)
- **First-time / fresh sandbox setup:** `./setup.sh` (recreates `.venv` with all
  requirements plus static ffmpeg/ffprobe)
- Plugin docs: [clip-desk/README.md](clip-desk/README.md)

## Pick your niche once

```bash
export CLIP_DESK_TOPIC="sourdough"                     # the niche in the words people search
export CLIP_DESK_SUBS="Sourdough,Breadit,AskCulinary"  # where the audience talks
export CLIP_DESK_HASHTAGS="#sourdough #bread #baking #fermentation"
```

Then every skill works on that niche. Games, cooking, tech, sport, music, crafts, finance — the tools are
niche-agnostic; the `setup` skill asks for these three values and writes them into your page folder.
