# Slot 009 sources

- **Recitation:** Mohamed Siddiq El-Minshawi, Murattal (Quran Foundation reciter 9). Source takes: [3:193](https://audio.qurancdn.com/Minshawi/Murattal/mp3/00319193.mp3) and [3:194](https://audio.qurancdn.com/Minshawi/Murattal/mp3/00319194.mp3). The supplied 3:193 start and the next complete ayah run about 48 s at the original pace. See `concat_map.json` for segment offsets and silence. The 3:195–197 files were staged for timing comparison and are not used.
- **Arabic and timing:** exact QPC Hafs word strings and QF reciter-9 word timing in `qf_3-193.json` and `qf_3-194.json`. The seven subtitle beats are listed in `beats009.json`.
- **English:** Saheeh International [3:193](https://api.quran.com/api/v4/verses/by_key/3:193?translations=20) and [3:194](https://api.quran.com/api/v4/verses/by_key/3:194?translations=20). Unmatched closing double quote at the end of the excerpt omitted; no wording edits.
- **Popup:** user-selected [pin 1119214944936118877](https://www.pinterest.com/pin/1119214944936118877/) ([short link](https://pin.it/69696p6RX)), 14.567 s, 576×1024 at 30 fps. Source is a landscape montage; the seven internal cuts are softened with short dissolves, and repetitions are joined with 0.4 s crossfades. Original colors; source audio not used. Pin attribution does not establish reuse rights.
- **Source clip SHA-256:** `944b5d89a2621237e1c764ae0c0b78a3381903ff44901a0056e446f91331c503`.

## v2 popup replacement

- **Source:** [pin 1119214944936118886](https://www.pinterest.com/pin/1119214944936118886/) ([short link](https://pin.it/7FdofUUxi)), shared by `zuu_cop`. Train-window view of fields and clouds; 8.20 s of video at 720×1280, 30 fps. Original footage creator and reuse rights are unverified.
- **Treatment:** top-aligned aspect-fill in the existing 860×1040 popup, six passes with 0.4 s crossfades, no source audio. The entire 1080×1920 composition (including subtitles) is shifted up 17 px. Recitation and caption timing are unchanged from v1.
- **Source SHA-256:** `ca45621375d767ccf0be8163285b1e2066ee28687eab90bf01b47f01db653691`.

Rebuild from the repository root after `./setup.sh`:

```sh
.venv/bin/python tools/quran_v2/build_slot009_v2.py assets/quran/009_aal-e-imran_3-193-194_minshawi/pinterest/009_pin_1119214944936118886.mp4
```

## v3 layout adjustment

Keeps the same v2 train-window footage, top-aligned crop, and 860 px popup width. For this clip only, the popup height increases from 1040 to 1056 px. The full layout moves another 23 px up (40 px total above v1); recitation and subtitle timing are unchanged.

Rebuild after `./setup.sh`, using the tracked v2 MP4 as the audio input:

```sh
.venv/bin/python tools/quran_v2/build_slot009_v2.py --version 3 assets/quran/009_aal-e-imran_3-193-194_minshawi/pinterest/009_pin_1119214944936118886.mp4
```

## v4 layout adjustment

Relative to v3, the whole composition moves 40 px up, and the top-aligned popup grows from 1056 to 1086 px at the same 860 px width. Of the additional height, 26 px grows toward the title and 4 px toward the captions to retain clearance on both sides. The source footage, recitation and subtitle timing are unchanged.

Rebuild after `./setup.sh`, using the tracked v3 MP4 as the audio input:

```sh
.venv/bin/python tools/quran_v2/build_slot009_v2.py --version 4 assets/quran/009_aal-e-imran_3-193-194_minshawi/pinterest/009_pin_1119214944936118886.mp4
```

## v5 layout adjustment

Relative to v4, the popup grows from 860×1086 to 860×1106 px, keeping the same width and top-aligned source crop. The composition baseline shifts up another 23 px. To open up the spacing, the header moves a further 22 px up and the caption/reference/progress block moves 40 px down relative to that shifted baseline. The recitation is copied from v4 unchanged, and subtitle timing is unchanged.

Rebuild after `./setup.sh`, using the tracked v4 MP4 as the audio input:

```sh
.venv/bin/python tools/quran_v2/build_slot009_v2.py --version 5 assets/quran/009_aal-e-imran_3-193-194_minshawi/pinterest/009_pin_1119214944936118886.mp4
```
