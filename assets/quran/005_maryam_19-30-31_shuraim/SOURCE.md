# Source assets - slot 005 - Maryam 19:30-31 - Sa`ud ash-Shuraym

Output: `outputs/quran-005_maryam_19-30-31_shuraim_en_1080x1920_v1.mp4`
Post package: `metadata/005_maryam_19-30-31_shuraim/`

## Recitation

- Reciter: Sa`ud ash-Shuraym, Murattal (Hafs 'an 'Asim), QF chapter-reciter ID 10.
- Audio sources: https://audio.qurancdn.com/Shuraym/mp3/019030.mp3 + https://audio.qurancdn.com/Shuraym/mp3/019031.mp3 joined with a 0.5 s waqf-like pause.
- Timing sources: https://api.quran.com/api/v4/verses/by_key/19:30?words=true&audio=10&word_fields=text_qpc_hafs and https://api.quran.com/api/v4/verses/by_key/19:31?words=true&audio=10&word_fields=text_qpc_hafs
  (mirrored to `qf_19-30.json` / `qf_19-31.json`).
- 19:30 [first word 60 ms, last word ends 6000 ms] (QF per-ayah mp3 019030); 19:31 [first word 40 ms, last word ends 7990 ms] (QF per-ayah mp3 019031).
- English: Rwwad translation via QuranEnc
  (https://quranenc.com/api/v1/translation/aya/english_rwwad/19/30?without_footnotes_symbols=1, https://quranenc.com/api/v1/translation/aya/english_rwwad/19/31?without_footnotes_symbols=1, mirrored to `rwwad_19-*.json`).
- Raw assembly (voice-first): 0.35 s leading + voice track + 0.6 s trailing
  digital silence -> `recitation_raw.m4a` (16.225 s, under the 25 s cap).
- Concat map: `{"lead_s": 0.35, "file30_s": 6.382, "gap_s": 0.5, "file31_offset_s": 7.232, "file31_s": 8.393, "tail_s": 0.6, "total_s": 16.225}` (also `concat_map.json`).
- Raw trim file: `recitation_raw.m4a` (`58705a25f7697ae456e9c851c0425a704708ae1ae1d404ff200d4f7bac4d583d`, 383005 bytes).
- ffprobe: `{"programs": [], "stream_groups": [], "streams": [{"codec_name": "aac", "codec_type": "audio", "sample_rate": "44100", "channels": 2}], "format": {"duration": "16.225011", "size": "383005", "bit_rate": "188846"}}`
- silencedetect (-45 dB): `{"silence_starts": [0.0, 6.723878, 15.609184], "silence_ends": [0.382585, 7.268662, 16.230748]}`

## Background clip (Pinterest board "K", candidate 010 - unused until this slot)

- Pin id: e1_AfqPShw8bwXQoW1ZpriWAQUldapMdZi7nE5QXT1Gb78O0tRAksu7kw
- Board: https://www.pinterest.com/jawed1025t/k/?invite_code=516f29ecb56e4a40a891ccc8089d146a&sender=1119215082304641687 (Jaqqd / jawed1025t)
- Full clip re-imported from git blob `33ae4dc41e3a03e01532638aa2140fb2b484e308` (commit 422b92c177ef5bd40a0761db318d1a7626a553f9, path `assets/al-baqarah-2-152-153/pinterest_candidates/010_e1_AfqPShw8bwXQoW1ZpriWAQUldapMdZi7nE5QXT1Gb78O0tRAksu7kw.mp4`); full-clip sha256 `839f93bd8e665c4ca4536896eefb515b3c52d78b1792c6048801526c1526bff5`.
- Used window: 122-150 s of the 248.27 s montage (cut list + stills: `scan010/report010.json`); the window is a single continuous shot (0 cuts) covering the 16.225 s card at 0.5795x (sub-window cut, no stretch).
- Scene: turquoise barrel wave curling left-to-right and glowing from within, white spray crown, steel-blue sky - no people, no text.
- Color treatment: raw original colors preserved (no color grade).
- Rights: user-supplied board; user stated no licence issue. Clear rights before commercial release.

