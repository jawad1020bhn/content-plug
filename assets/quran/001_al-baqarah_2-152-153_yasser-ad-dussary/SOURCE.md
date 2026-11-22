# Source assets — slot 001 · Al-Baqarah 2:152–153 · Yasser ad-Dussary

Output: `outputs/quran-001_al-baqarah_2-152-153_yasser-ad-dussary_en_1080x1920_v1.mp4`
Post package: `metadata/001_al-baqarah_2-152-153_yasser-ad-dussary/`


Local review assets. Post caption/description credits are generated separately; no credit text is
burned into the video and no social upload is performed by this importer.

## Recitation

- Reciter: Yasser ad-Dussary, Murattal (Hafs), QF chapter-reciter ID 97.
- QF segment/timing source: https://api.quran.com/api/v4/chapter_recitations/97/2?segments=true
- Full chapter audio: https://download.quranicaudio.com/quran/yasser_ad-dussary//002.mp3
- Trim: 3274050–3299050 ms (2:152–153), 25.000 s; plus 0.8 s leading silence and 0.2 s / 0.5 s fades.
- Output: `recitation.m4a` (AAC 44.1 kHz stereo, 25.800 s total). This is the
  untouched trim and stays the timing reference for every caption cue.
- SHA-256 `b6d0aa6eb65a8b4b4c7880f09b0ce9c9111ece2a01a6d259f249d799dd971685` (624252 bytes).
- ffprobe: {"programs": [], "stream_groups": [], "streams": [{"codec_name": "aac", "codec_type": "audio", "sample_rate": "44100", "channels": 2, "r_frame_rate": "0/0"}], "format": {"duration": "25.800000", "size": "624252"}}

## Audio polish (hall space, clarity)

- Script: `clip-desk/scripts/quran_audio_polish.py` (committed, reusable).
- Synthetic hall impulse response: exponentially decaying, high-frequency-damped noise,
  0.52 s decay constant, 1.6 s IR, **45 ms pre-delay on the reverb send only**. The dry
  voice is never delayed, so no word is repeated or doubled and QF timings stay exact.
- Reverb send is low level (`--wet 0.15`, about -16 dB) so it reads as room depth, not as
  an effect or a musical tone.
- Clarity chain: 72 Hz high-pass, -1.6 dB at 330 Hz, +2 dB at 2.9 kHz, 1.7:1 compressor,
  -1.5 dBTP limiter, loudness matched to -14.5 LUFS.
- Output: `jobs/001_al-baqarah_2-152-153_yasser-ad-dussary/recitation_polished.m4a` (26.200 s with reverb tail,
  -14.5 LUFS integrated, -1.8 dBTP). Verified against the dry trim: 0 ms envelope lag and no
  duplicate segment matches, i.e. no echo of speech.
- Job artifacts (ASS, polished audio, visual base) stay in gitignored `jobs/`.

## Pinterest background candidates

- Supplied short link: https://pin.it/4pKEOoyfx
- Board: https://www.pinterest.com/jawed1025t/k/?invite_code=516f29ecb56e4a40a891ccc8089d146a&sender=1119215082304641687
- Public signed-out metadata names the board “K” by Jaqqd (jawed1025t).
- Downloaded 12 candidate clips. The revision uses ONE clip only: candidate 012, a single
  continuous scene. Clips 04, 05 and 09 were deleted from the repo after review.
- `selection.txt` records the single selection; the popup background is `background.mp4`,
  derived from clip 012 alone (slowed 1.4453x to cover 26.2 s, no cuts, no crossfades).
- `background.mp4`: 1080x1920, 30 fps, 26.200 s, H.264, no audio, SHA-256
  `a4a44d840786d78726c8545371296b5250515214694cec95d48e17cc81015c1c` (29,022,002 bytes).
- Pin IDs, source URLs, durations, hashes and ffprobe data: `candidates.json`.
- Visual contact sheet: `candidates_sheet.png`.
- Rights: the user supplied this board and explicitly stated “no licence issue” for using the clips
  as the popup background. This record does not claim a public stock licence; clear rights before
  any public or commercial release.

## Credits to carry into the post caption/description

- “Quran data provided by Quran Foundation.”
- Arabic: QPC Hafs / UthmanicHafs1Ver18 — King Fahd Glorious Quran Printing Complex (KFGQPC).
- Translation: English Translation - Noor International Center (`english_saheeh` v1.1.2 / QuranEnc.com).
- Reciter: Yasser ad-Dussary (Murattal, Hafs).
- Fonts: KFGQPC Uthmanic Hafs + Cormorant Garamond (SIL OFL 1.1).
- Background: Pinterest board “K” by Jaqqd / jawed1025t (user-supplied clip 012).

QF Connected Apps notes that commercial use or redistribution of licensed recitations may require a
separate written content license; KFGQPC reproduction/commercial release may require written approval.
Full-surah MP3 is kept only in ignored `.cache/`; raw QF API JSON is not committed.

