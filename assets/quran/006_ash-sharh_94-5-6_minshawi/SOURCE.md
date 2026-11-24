# Source assets - slot 006 - Ash-Sharh 94:5-6 - Mohamed Siddiq El-Minshawi

Output: `outputs/quran-006_ash-sharh_94-5-6_minshawi_en_1080x1920_v1.mp4`
Post package: `metadata/006_ash-sharh_94-5-6_minshawi/`

## Recitation

- Reciter: Mohamed Siddiq El-Minshawi, Murattal (Hafs 'an 'Asim), QF reciter ID 9.
- Audio sources: https://audio.qurancdn.com/Minshawi/Murattal/mp3/094005.mp3 + https://audio.qurancdn.com/Minshawi/Murattal/mp3/094006.mp3 joined with a 0.5 s waqf-like pause.
- Timing sources: https://api.quran.com/api/v4/verses/by_key/94:5?words=true&audio=9&word_fields=text_qpc_hafs and https://api.quran.com/api/v4/verses/by_key/94:6?words=true&audio=9&word_fields=text_qpc_hafs
  (mirrored to `qf_94-5.json` / `qf_94-6.json`).
- 94:5 [first word 550 ms, last word ends 5360 ms] (QF per-ayah mp3 094005); 94:6 [first word 250 ms, last word ends 4920 ms] (QF per-ayah mp3 094006).
- English: Saheeh International translation via QuranEnc
  (https://quranenc.com/api/v1/translation/aya/english_saheeh/94/5?without_footnotes_symbols=1, https://quranenc.com/api/v1/translation/aya/english_saheeh/94/6?without_footnotes_symbols=1, mirrored to `saheeh_94-*.json`).
- Per-ayah trim: each file cut to [first-word-start - 0.12 s, last-word-end + 0.4 s] (heads 0.430/0.130 s removed for voice-first onset; natural decay kept).
- Raw assembly (voice-first): 0.35 s leading + voice track + 0.6 s trailing
  digital silence -> `recitation_raw.m4a` (11.626 s, under the 25 s cap).
- Concat map: `{"lead_s": 0.35, "file5_head_trim_s": 0.43, "file5_s": 5.212, "gap_s": 0.5, "file6_offset_s": 6.062, "file6_head_trim_s": 0.13, "file6_s": 4.964, "tail_s": 0.6, "total_s": 11.626}` (also `concat_map.json`).
- Raw trim file: `recitation_raw.m4a` (`c9ee6a67e5d9614316affe7cacae89bf80bde9c81c2fb5aa8a6b0a192770906d`, 255587 bytes).
- ffprobe: `{"programs": [], "stream_groups": [], "streams": [{"codec_name": "aac", "codec_type": "audio", "sample_rate": "44100", "channels": 2}], "format": {"duration": "11.626009", "size": "255587", "bit_rate": "175872"}}`
- silencedetect (-45 dB): `{"silence_starts": [0.0, 5.562449, 11.038027], "silence_ends": [0.379932, 6.098367, 11.633197]}`

## Background: house black surround (no full-bleed clip in v1)

- v1 ships the house black-surround card (92 px pure-black side margins, halo,
  motes, grain) with the board-K popup; no full-bleed background clip.
- Scouted but NOT used: clip-010 window 63.45-75.55 s (waterfall cove, dark
  mossy canyon into a turquoise pool, per-frame verified 0 cuts, 12.10 s).
  Full clip: git blob `33ae4dc4` (commit 422b92c,
  `assets/al-baqarah-2-152-153/pinterest_candidates/010_e1_AfqPShw8bwXQoW1ZpriWAQUldapMdZi7nE5QXT1Gb78O0tRAksu7kw.mp4`,
  sha256 `839f93bd...`). Scout evidence (gitignored): `jobs/_scout006/`
  (strip_pool_62_77, per-frame cut pins at 63.38-63.40 s and freeze+dissolve at
  75.60 s). Free for a future slot needing a full-bleed background.

## Popup clip (Pinterest board "K", candidate 006 - spent by this slot)

- Pin id: e1_AfqPShwONkAF2MbmnVizxbOIXrhJbRjiVbHEuPuiU4biPcWNE0eyNA
- File: `pinterest/006_e1_AfqPShwONkAF2MbmnVizxbOIXrhJbRjiVbHEuPuiU4biPcWNE0eyNA.mp4` (whole clip, 7.8 s, 576x1024, 0 cuts).
- Scene: first-person prayer mat on a rock ledge above an alpine lake, slow left-to-right pan; looped (forward + ping-pong) in the video build.

