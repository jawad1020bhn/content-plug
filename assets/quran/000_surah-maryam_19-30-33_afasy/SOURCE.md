# Source assets — slot 000 · Surah Maryam 19:30–33 · Mishari al-ʿAfasy

Output: `outputs/quran-000_surah-maryam_19-30-33_afasy_en_1080x1920_v1.mp4`
Post package: `metadata/000_surah-maryam_19-30-33_afasy/`
Status: first attempt, kept as history. Video 001 is the reference style.


These are source assets for a local video. Credits belong in the post caption/description,
never burned into the video pixels.

## Background

- Pixabay video 204756, “Sunset, Sunrise, Night” by hsahmad472.
- Page: https://pixabay.com/videos/sunset-sunrise-night-sky-moonlight-204756/
- Direct MP4: https://cdn.pixabay.com/video/2024/03/19/204756-925166550_large.mp4
- License: [Pixabay Content License](https://pixabay.com/service/license-summary/) — free use,
  modification and adaptation; no standalone redistribution. Attribution appreciated, not required.
- SHA-256 `6e11eb59662fea57ed7101535a14aca660e5922eb3084531f17a24ab5ea769f2` (5102910 bytes).
- ffprobe: {"programs": [], "stream_groups": [], "streams": [{"index": 0, "codec_name": "h264", "codec_type": "video", "width": 1080, "height": 1920, "r_frame_rate": "30/1"}], "format": {"duration": "8.800000", "size": "5102910"}}

## Recitation

- Reciter: Mishari Rashid al-`Afasy, Murattal (Hafs), chapter-reciter ID 7.
- QF segment/timing source: https://api.quran.com/api/v4/chapter_recitations/7/19?segments=true
- Full chapter audio: https://download.quranicaudio.com/qdc/mishari_al_afasy/murattal/19.mp3
- Trim: 397790–440010 ms (19:30–33), 42.220 s; plus 0.8 s leading silence and 0.2 s / 0.5 s fades.
- Output: `recitation.m4a` (AAC 44.1 kHz stereo, 43.020 s total).
- SHA-256 `e2b25568121d844b5f0b635b97c082acfde7f80233fa0185e52169eecec9d80d` (1033365 bytes).
- ffprobe: {"programs": [], "stream_groups": [], "streams": [{"index": 0, "codec_name": "aac", "codec_type": "audio", "sample_rate": "44100", "channels": 2, "r_frame_rate": "0/0"}], "format": {"duration": "43.020000", "size": "1033365"}}

## Rights / attribution

- Quran Foundation text/timing/audio: credit “Quran data provided by Quran Foundation.”
  plus the named reciter and translation edition in the post caption/description.
- QF [Connected Apps](https://api-docs.quran.com/docs/connected-apps/) notes that commercial use
  or redistribution of licensed recitations may require a separate written content license.
  Clear rights before any public/commercial post. No upload is done by this importer.
- Full-surah MP3 is kept only in ignored `.cache/`; raw QF API JSON is not committed.

