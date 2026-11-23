# HOUSE-STYLE.md — the proven look & sound of the verse-card series

Everything here was earned on `001 v2` and `002` and verified by eye on real Reels crops and
QA sheets. **Do not re-derive these numbers**; copy the renderer templates from
`tools/quran_v2/` and change only the per-slot constants listed in `tools/quran_v2/README.md`.
Legacy `quran_visual.py` numbers (slot 000/001 v1) remain in `RECIPE.md` §8 for history.

---

## 1. Canvas & encode

| Thing | Value |
|---|---|
| Canvas | 1080×1920, 30 fps, pure-black `#000000` surround |
| Video | H.264, crf 18, yuv420p, `+faststart` |
| Audio | AAC 192 kbps, 44.1 kHz, stereo |
| Duration | exactly the audio-master duration (recitation verbatim + 0.85 s lead-in) |
| Loop tail | last **0.45 s** fade-to-black so the Reel loops seamlessly |

## 2. Popup geometry — Reels zoom-safe (the 001-v2 fix)

Tall phones (20:9) horizontally zoom-crop ≈60 px per side of a 9:16 upload. The old 1000 px
popup sat flush against the crop edge on a real device (see the human's Instagram screenshot
of 001 v2). House geometry since then:

| Thing | Value |
|---|---|
| Popup | **816 × 748 px**, radius **76**, centred: `x = 132 … 948`, `y = 342 … 1090` |
| Side margins | **132 px pure black per side** → ≥70 px black + full halo + full glass border survive the crop |
| Header strip | `"Surah <Name>"`, 120 px tall sprite at `y = POP_Y − 116` (226); scrolls & blurs with the card |
| Rule | never widen the popup again without re-running the 20:9 crop simulation (`--test-preview`) |

## 3. Typography (exact ASS styles)

libass matches the font's **internal family name**. The bundled variable font's name is
`Cormorant Garamond Light` — writing `Cormorant Garamond` silently falls back to DejaVu Sans
(sans-serif look). Verify the serif in every pre-flight still.

```ass
Style: Header,Cormorant Garamond Light,36,&H3AC4CED8,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0.6,0,1,0,0,5,40,40,10,1
Style: Arabic,KFGQPC HAFS Uthmanic Script,60,&H00E2EDF2,&H000000FF,&H88080808,&H90000000,0,0,0,0,100,100,0,0,1,1.2,2.0,5,155,155,20,1
Style: English,Cormorant Garamond Light,46,&H06CBD7DD,&H000000FF,&H88080808,&H80000000,0,0,0,0,100,100,0.2,0,1,0.9,1.5,5,165,165,20,1
Style: Ref,Cormorant Garamond Light,28,&H328E989E,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,1.0,0,1,0,0,5,180,180,20,1
```

| Layer | y (1-line / 2-line Arabic) | Motion |
|---|---|---|
| Arabic | 1248 / 1236 | enters at beat start, glides ↑15 px / 340 ms, `\fad(250,220)` |
| English | 1408 / 1422 | **+100 ms stagger**, glides ↑14 px / 360 ms, `\fad(270,220)` |
| Ref pill `[2:xxx]` | 1568 | one cue per **ayah** span (no flicker between sub-beats), `\fad(260,220)` |
| Progress filament | 1612 | 168 px wide, 2 px line; track BGR (44,47,50), fill BGR (188,202,214), luminous tip; fades in 0.35 s after the opener locks |

Line limits: Arabic ≤ 2 lines (break at waqf/comma), English ≤ 2 lines (break at commas).
No hook text anywhere — the opener carries the first second.

## 4. Fake-scroll opener (0.00 → 0.84 s)

- Active card sweeps in from **+1340 px** below with velocity-proportional vertical shutter blur.
- Micro-overshoot **−15 px at 0.65 s**, spring-locks at **0.84 s** exactly as the voice enters (0.85 s).
- Outgoing ghost card: blurred dark card 1560 px above with a blurred header line — sells "feed".
- **No hook text, no separator lines** (a faint horizontal divider above the header was caught in
  002 pre-flight and removed; keep it removed).
- Audio side: two non-musical scroll air cues at **0.12 s** (flick) and **0.63 s** (lock).

## 5. Micro-animations (all precomputed; per-frame cost must stay ~65 ms/frame)

| Element | Parameters |
|---|---|
| Voice-reactive halo | ring = GaussianBlur(σ34) of card mask in a 96 px padded ROI, BGR (192,208,224); strength `0.055 + 0.068·voice_env` |
| Top-lit glass border | precomputed border mask, brighter on the top edge |
| Dust motes | **28** warm-ivory particles, pre-blurred 17×17 sprite, BGR (200,214,226); v_y 14–31 px/s, sway amp 8–24 px @0.18–0.45 Hz, α 0.10–0.26 × (0.75+0.45·voice_env) |
| Voice envelope | `voice_env_30fps.npy` exported by the audio build (RMS @30 fps) — halo, motes and filament tip read it |

Performance rule: **never** call full-frame `GaussianBlur` per frame (001 v2 hit the 600 s
timeout that way). Precompute sprites/masks once; stream source frames with a 2-frame ring buffer.

## 6. Audio master chain (build_audio_template.py)

Order matters; words, order, pitch and timing of the recitation are **never** altered.

1. Clarity EQ sculpt on the dry recitation.
2. **True-stereo Masjid al-Haram sanctuary IR**: 3.2 s, dual-decay tail + decorrelated marble
   early reflections, **56 ms pre-delay on the wet only** (consonants stay crisp, zero doubling),
   wet mix **0.42** (`amix weights 1.0 0.42, normalize=0`).
3. Scene-matched non-musical ambience bed ≤ **−35 dBFS**, sidechain-ducked
   (`duck = 1 − 0.65·clip(env/0.12)`) so the voice stays 100% pure; plus the two scroll cues.
4. Two-pass EBU R128 master to **−14.3 LUFS** integrated, true peak ≤ −1.5 dBTP (002 measured
   −5.35 dBTP, LRA 2.3 LU).
5. Export `voice_env_30fps.npy`.

QA numbers that prove the chain: waqf breaths carry a stereo reverb tail ≈ −23 dBFS with
L/R correlation ≈ 0.6 (mono would read ≈1.0); overall L/R correlation ≈ 0.82.

## 7. Beat map (caption timing)

- Split each ayah into beats at **audible breaths and Mushaf waqf marks** (`ۗ` minor-pause,
  `ۖ` permissible-pause), not at
  fixed character counts; 5–8 beats per card is the comfortable band.
- Verify every boundary acoustically (RMS/ZCR envelope + `silencedetect`) **and by ear-stripe**:
  MP3Quran mid-verse word segments have been ~3.4 s early (2:153 case). Never trust them blind.
- Keep the final consonant tail: `REC_END_S` = last phoneme + ~0.25 s (002: final `نْ` at 40.48 s).
- Ayah ref pills span the whole ayah; beats inside one ayah share the pill.
- English text: verbatim named translation, line-broken at commas; Arabic: QPC Hafs words joined,
  ayah-end circle glyphs omitted, `\N` at waqf/comma.

## 8. Background clip rules

- **One continuous clip, zero scene cuts** (scene-detect must return 0), never a spent clip
  (`ASSET-REGISTRY.md` is the source of truth).
- **Raw original colours by default** — no grade (002). If the human ever asks for a grade,
  record `color_graded: true` in `post.json`.
- Stretch factor ≤ **1.3×** via `setpts` (002: 32.6 s → 41.0 s = 1.257×); prefer candidates
  ≥ target/1.3 s long; portrait orientation preferred.
- No prominent people; anime backgrounds: no people, no animals.

## 9. QA gates (all visual — look, don't assume)

1. `--test-preview` → inspect `preview_scroll_strip.png` (opener blur, no stray lines above the
   header), `preview_beats_grid.png` (typography, serif, RTL/harakat/waqf), `preview_reels_20x9_crop.png`
   (both side margins black + halo + border intact).
2. Full render → `ffprobe` (1080×1920@30, h264+aac 44.1k stereo, exact duration) +
   `loudnorm=print_format=summary` (≈ −14.3 LUFS).
3. `metadata/<slot>/qa.png`: **8 panels from the final MP4** — one opener frame (t≈0.25 s) + one
   per beat; plus `poster.png` at a strong beat. Inspect both by eye.
4. Registry/catalog rows updated in the same commit; show the human MP4 + caption + credits;
   wait for an explicit **"yes"** before posting or PR.
