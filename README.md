# content-plug

A faceless content-creation desk for **any niche** — not one fandom. The plugin lives at [`clip-desk/`](clip-desk/)
(MIT) and is adapted to the Arena agent harness.

Today this workspace's active series is **Quran verse cards**: 9:16 videos with canonical QPC Hafs Arabic,
a named published translation, an exact-timing recitation, and a single scenic clip behind a rounded popup.
Nothing is posted automatically — every video waits for an explicit human "yes".

## Start here

| If you are… | Read |
|---|---|
| building the next video | **[docs/RECIPE.md](docs/RECIPE.md)** — the whole build, with proven numbers |
| choosing a background clip | **[docs/ASSET-REGISTRY.md](docs/ASSET-REGISTRY.md)** — never reuse a spent clip |
| naming a file / finding the next slot | **[docs/CATALOG.md](docs/CATALOG.md)** — filename grammar + delivered list |
| writing the caption/title/credits | **[docs/PUBLISHING.md](docs/PUBLISHING.md)** — per-platform text |
| running tools or debugging the sandbox | [AGENTS.md](AGENTS.md) |
| first-time setup in a fresh sandbox | `./setup.sh` — recreates `.venv` + static ffmpeg/ffprobe |

## Folder layout

```
assets/quran/<NNN>_<slug>/   source assets  (background, recitation, chosen clip, SOURCE.md)  tracked
jobs/<NNN>_<slug>/           intermediates  (verses, timings, ASS, polished audio)            ignored
metadata/<NNN>_<slug>/       post package   (post.json, caption, credits, poster, qa)         tracked
outputs/                     finished MP4s only, named by the catalog convention              tracked
docs/                        recipe, catalog, asset registry, publishing guide
content-inputs/              raw human-supplied source videos
clip-desk/                   the plugin: scripts/, skills/, models/, fonts
```

Slot numbers are permanent and never reused. Output filenames carry the metadata:

```
quran-001_al-baqarah_2-152-153_yasser-ad-dussary_en_1080x1920_v1.mp4
└ series └ slot └ surah └ ayah range └ reciter └ lang └ canvas └ version
```

## The 60-second version of the workflow

1. Pick the next slot in `docs/CATALOG.md`; pick an **unused** clip in `docs/ASSET-REGISTRY.md`.
2. Get canonical Arabic (`text_qpc_hafs`), one named translation (QuranEnc), and exact QF segment timings
   for that specific reciter audio.
3. `quran_audio_polish.py` → `quran_visual.py` → `quran_subtitles.py`, writing the MP4 to `outputs/`.
4. QA the poster + contact sheet by eye, write `metadata/<slot>/`, mark the clip spent.
5. Show the human the file, caption and credits. Wait for "yes". Never post.

Hard rules: credits go in the caption, never in the pixels; no ASR/machine translation of Quran text;
no reused footage; every credit and number must be real.

## Pick your niche once (generic plugin use)

```bash
export CLIP_DESK_TOPIC="sourdough"                     # the niche in the words people search
export CLIP_DESK_SUBS="Sourdough,Breadit,AskCulinary"  # where the audience talks
export CLIP_DESK_HASHTAGS="#sourdough #bread #baking #fermentation"
```

Then every skill works on that niche. Games, cooking, tech, sport, music, crafts, finance — the tools are
niche-agnostic; the `setup` skill asks for these three values and writes them into your page folder.
