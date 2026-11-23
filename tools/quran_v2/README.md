# tools/quran_v2 — the proven v2 verse-card renderer (template copy)

`jobs/` is **gitignored**, so the renderer that actually built slots `001 v2` and `002`
would vanish with the sandbox. These two files are byte-identical copies of
`jobs/002_al-baqarah_2-155-157_ali-jaber/{build_video,build_audio}.py` (the proven build),
kept here **as templates only — never run them in place**.

| File | What it produces |
|---|---|
| `build_audio_template.py` | `jobs/<slot>/recitation_master.m4a` (stereo Haram-sanctuary master, −14.3 LUFS), `haram_sanctuary_ir.wav`, ducked ambience bed, `voice_env_30fps.npy` (halo driver), `audio_report.json` |
| `build_video_template.py` | `jobs/<slot>/visual_base.mp4` + ASS captions + final muxed `outputs/quran-<slot>_en_1080x1920_v1.mp4`; `--test-preview` writes 3 pre-flight stills instead of rendering |

## Starting a new slot with this renderer

```bash
N=003; SLUG=<surah>_<ayah-range>_<reciter>          # e.g. al-baqarah_2-186_ali-jaber
mkdir -p assets/quran/${N}_${SLUG} jobs/${N}_${SLUG} metadata/${N}_${SLUG}
cp tools/quran_v2/build_audio_template.py jobs/${N}_${SLUG}/build_audio.py
cp tools/quran_v2/build_video_template.py jobs/${N}_${SLUG}/build_video.py
```

Both scripts resolve every path from `ROOT = parents[2]`, so they work from anywhere once
copied into `jobs/<slot>/`. Edit **these constants** in the copies (line numbers refer to the
template files; search by name, not number):

### build_audio.py edit points
| Constant / block | Meaning |
|---|---|
| `SLOT` | `"<NNN>_<slug>"` — drives every path |
| `RAW_IN` | source trim `assets/quran/<slot>/recitation_raw.m4a` |
| `build_subtle_ambience_and_scroll_cue()` | the ambience bed is scene-flavoured: 002 used alpine water air; rewrite the noise recipe (or silence it) to match the new background scene. Keep it ≤ −35 dBFS and ducked |
| scroll-cue times (`0.12 s`, `0.63 s`) | must match `SCROLL_END_S` physics in build_video (flick + spring lock) |
| loudnorm targets | keep −14.3 LUFS / ≤ −1.5 dBTP unless the human changes house loudness |

### build_video.py edit points
| Constant / block | Meaning |
|---|---|
| `SLOT`, `PIN_CLIP`, `OUT_MP4`, `META_DIR` | paths; `OUT_MP4` must follow the `docs/CATALOG.md` filename grammar |
| `DURATION_S`, `TOTAL_FRAMES` | master length (audio master duration, verbatim) |
| `REC_START_S`, `REC_END_S` | first phoneme / last consonant tail of the recitation inside the master (from the beat map) |
| `LOOP_FADE_START_S` | `DURATION_S − 0.45` for the seamless loop tail |
| `BEATS` | the beat map: `id/ref/start/end/arabic/english`. Arabic = QPC Hafs words joined, `\N` for line breaks (≤2 lines), **omit ayah-end circle glyphs**; English = verbatim translation, `\N` at commas. Times come from the acoustic beat-map step (see `docs/HOUSE-STYLE.md` §Beat map) |
| `ayah_spans` in `write_captions_ass()` | one `[2:xxx]` pill span per ayah so the pill never flickers between sub-beats |
| header text in `render_header_sprite()` | `"Surah <Name>"` |
| `POP_*`, `SCROLL_END_S`, style lines | **do not change** without re-running the 20:9 crop QA — these are the Reels-safe house geometry (`docs/HOUSE-STYLE.md`) |

## Run order

```bash
export PATH="$PWD/.venv/bin:$PATH"          # ffmpeg/ffprobe live in .venv/bin
python jobs/<slot>/build_audio.py           # ~20 s; prints LUFS/TP report
python jobs/<slot>/build_video.py --test-preview   # ~5 s; 3 stills into jobs/<slot>/
python jobs/<slot>/build_video.py           # ~2 min for 41 s @30 fps; muxes final MP4
```

Inspect the three pre-flight stills (`preview_scroll_strip.png`, `preview_beats_grid.png`,
`preview_reels_20x9_crop.png`) **before** the full render — they caught the libass font
fallback and the stray separator line on slot 002. Then build `metadata/<slot>/`
(`post.json`, `caption.txt`, `credits.txt`, `poster.png`, 8-panel `qa.png` from the final
MP4 including one opener frame), update `docs/ASSET-REGISTRY.md` + `docs/CATALOG.md`, and
show the human everything. Wait for an explicit "yes" before any posting or PR.
