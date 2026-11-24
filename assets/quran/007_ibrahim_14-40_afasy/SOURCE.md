# Source assets - slot 007 - Ibrahim 14:40 - Mishari al-Afasy

Output: `outputs/quran-007_ibrahim_14-40_afasy_en_1080x1920_v1.mp4`
Post package: `metadata/007_ibrahim_14-40_afasy/`

## Recitation (RAW - no audio processing by human direction)

- Reciter: Mishari al-Afasy, Murattal (Hafs 'an 'Asim), QF reciter ID 7.
- Audio source: https://audio.qurancdn.com/Alafasy/mp3/014040.mp3 (single ayah, no inter-ayah gap).
- Timing source: https://api.quran.com/api/v4/verses/by_key/14:40?words=true&audio=7&word_fields=text_qpc_hafs (mirrored to `qf_14-40.json`).
- 14:40 [first word 70 ms, last word ends 12460 ms] (QF per-ayah mp3 014040).
- English: Saheeh International translation via QuranEnc
  (https://quranenc.com/api/v1/translation/aya/english_saheeh/14/40?without_footnotes_symbols=1, mirrored to `saheeh_14-40.json`; rotation break from rwwad documented in post.json: rwwad 14:40 reads 'some my offspring').
- Trim: file cut to [first-word-start - 0.12 s, last-word-end + 0.4 s] (head 0.000 s removed for voice-first onset; natural decay kept).
- Raw assembly: 0.35 s leading + voice + 0.6 s trailing digital silence -> `recitation_raw.m4a` (13.810 s, under the 25 s cap).
- The video build uses this file with ZERO processing (no EQ, reverb, ambience, normalization); only digital-silence padding for exact length.
- Concat map: `{"lead_s": 0.35, "head_trim_s": 0.0, "voice_s": 12.86, "tail_s": 0.6, "total_s": 13.81}` (also `concat_map.json`).
- Raw file: `recitation_raw.m4a` (`600f51c76b8185393a6da3ca49a2bf1021229aef756c85ab49365334b6ac450b`, 319078 bytes).
- ffprobe: `{"programs": [], "stream_groups": [], "streams": [{"codec_name": "aac", "codec_type": "audio", "sample_rate": "44100", "channels": 2}], "format": {"duration": "13.810000", "size": "319078", "bit_rate": "184838"}}`
- silencedetect (-45 dB): `{"silence_starts": [0.0, 13.212585], "silence_ends": [0.35, 13.815873]}`

## Background: house black surround (no full-bleed clip)

- v1 ships the house black-surround card (92 px pure-black side margins, halo, motes, grain) with the board-K popup; no full-bleed background clip.

## Popup clip (Pinterest board "K", candidate 002 - spent by this slot)

- Pin id: e1_AfqPShwWDOHMQ5I_Ev1_JobUxZAcNMrg8PElRynydnpeEjYAk8uQeA
- Board: https://www.pinterest.com/jawed1025t/k/?invite_code=516f29ecb56e4a40a891ccc8089d146a&sender=1119215082304641687 (Jaqqd / jawed1025t)
- Full clip committed from git blob `7f92d9240d02a06520c3bd01b666db3d0106e708` (commit 422b92c177ef5bd40a0761db318d1a7626a553f9, path `assets/al-baqarah-2-152-153/pinterest_candidates/002_e1_AfqPShwWDOHMQ5I_Ev1_JobUxZAcNMrg8PElRynydnpeEjYAk8uQeA.mp4`).
- File: `pinterest/002_e1_AfqPShwWDOHMQ5I_Ev1_JobUxZAcNMrg8PElRynydnpeEjYAk8uQeA.mp4` (whole clip, 11.08 s, 720x1280, 0 cuts).
- Scene: man performs wudu at a mountain stream, stands, kneels in prayer; lush green valley, face never shown.
- Mapped whole across the 13.810 s card at 1.2464x (gentle slow-motion, no loop).

