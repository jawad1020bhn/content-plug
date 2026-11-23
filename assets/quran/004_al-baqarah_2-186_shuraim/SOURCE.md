# Source assets — slot 004 · Al-Baqarah 2:186 · Sa`ud ash-Shuraym

Output: `outputs/quran-004_al-baqarah_2-186_shuraim_en_1080x1920_v1.mp4`
Post package: `metadata/004_al-baqarah_2-186_shuraim/`

## Recitation

- Reciter: Sa`ud ash-Shuraym, Murattal (Hafs 'an 'Asim), QF chapter-reciter ID 10.
- Audio source: https://audio.qurancdn.com/Shuraym/mp3/002186.mp3
- Timing source: https://api.quran.com/api/v4/verses/by_key/2:186?words=true&audio=10&word_fields=text_qpc_hafs
- QF word segments: first word 100 ms, last word ends 14300 ms (per-ayah file).
- Raw assembly: 0.8 s leading + voice + 0.6 s trailing digital silence -> `recitation_raw.m4a` (15.880 s, under the 25 s cap).
- Raw trim file: `recitation_raw.m4a` (`997ba847be6e3109ea07f2c36a7b728a6cc8b454f2c4c74690a5e835a18100c5`, 374065 bytes).
- ffprobe: `{"programs": [], "stream_groups": [], "streams": [{"codec_name": "aac", "codec_type": "audio", "sample_rate": "44100", "channels": 2}], "format": {"duration": "15.880000", "size": "374065", "bit_rate": "188445"}}`
- silencedetect (-45 dB): `{"silence_starts": [0.0, 15.271837], "silence_ends": [0.845306, 15.882449]}`

## Background clip (Pinterest board “K”, candidate 001 — unused until this slot)

- Pin id: e1_AfqPShyrnCaU19OySaDrZRa3aH3iodsRge6VLRfIMhrSrQy_bLCo_g
- Board: https://www.pinterest.com/jawed1025t/k/?invite_code=516f29ecb56e4a40a891ccc8089d146a&sender=1119215082304641687 (Jaqqd / jawed1025t)
- Full clip re-imported from git blob `d61084ba752d6f797074d17a6e7ca0e52b7be834` (commit 422b92c177ef5bd40a0761db318d1a7626a553f9, path `assets/al-baqarah-2-152-153/pinterest_candidates/`); full-clip sha256 `d489bed2211c384aa9f0e5b87da62597234de3fb1b9ab43f37126d1824a44b40` matches candidates.json.
- Used whole: the 17.161 s single continuous shot covers the 15.880 s card at 0.9254x (renderer maps the full clip across the full duration; well inside the 1.3x house stretch rule).
- Scene: winding dark river through forest under a stormy teal cloud sky, yellow wildflowers in the foreground — one continuous shot, 0 scene cuts, no people.
- Color treatment: raw original colors preserved (no color grade).
- Rights: user-supplied board; user stated no licence issue. Clear rights before commercial release.

