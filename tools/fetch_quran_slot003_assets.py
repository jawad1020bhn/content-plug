#!/usr/bin/env python3
"""Importer for Slot 003: Sheikh Ali Jaber Surah Al-Kahf 18:107-108 studio recitation.

Background clip 008 (misty waterfall cliff, 247.4 s continuous drone shot) is NOT downloaded
here — it is cut locally from the git blob f3d93cbd… (commit 422b92c) into
assets/quran/<slot>/pinterest/ before this runner's audio commit lands.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import urllib.request
from pathlib import Path

UA = "Mozilla/5.0 (compatible; content-plug-quran-slot003/1.0)"

AUDIO_URLS = [
    "https://cdn.mp3quran.net/audio/ali-jaber/r1/018.mp3",
    "https://server11.mp3quran.net/a_jbr/018.mp3",
]
EVERYAYAH_URLS = {
    107: "https://everyayah.com/data/Ali_Jaber_64kbps/018107.mp3",
    108: "https://everyayah.com/data/Ali_Jaber_64kbps/018108.mp3",
}
TIMING_SOURCE_URL = "https://www.mp3quran.net/api/v3/ayat_timing?surah=18&read=76"

# Official mp3quran read=76 timestamps for 18:107-108:
#   18:107: 1677480 -> 1689400 ms
#   18:108: 1689400 -> 1695840 ms
START_MS = 1677080   # 400 ms pre-roll before first phoneme
END_MS = 1696240     # 400 ms tail after final consonant

PIN_ID = "e1_AfqPShx2sVLYlij3Z3y3YUURLZUKGojmRCUechmKqAJpT6VFjVHWVw"
PIN_BLOB_SHA = "f3d93cbdb1504e274f2d17f9c91a5b1ebb593ff2"
PIN_CLIP_SHA256 = "0a76d24c454626af2eea3f13367305308edadca226e1f40a913b843641ef2ba4"
CLIP_WINDOW_START_S = 89.0
BOARD_URL = "https://www.pinterest.com/jawed1025t/k/?invite_code=516f29ecb56e4a40a891ccc8089d146a&sender=1119215082304641687"

ROOT = Path(".")
SLOT = "003_al-kahf_18-107-108_ali-jaber"
ASSETS = ROOT / "assets" / "quran" / SLOT
PINTEREST_DIR = ASSETS / "pinterest"
CACHE = ROOT / ".cache"
FULL_AUDIO = CACHE / "ali_jaber_018.mp3"
RAW_RECITATION = ASSETS / "recitation_raw.m4a"
SOURCE_MD = ASSETS / "SOURCE.md"


def log(msg: str) -> None:
    print(f"[slot-003] {msg}", flush=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def ffprobe_json(path: Path) -> dict:
    out = subprocess.check_output(
        [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration,size,bit_rate:stream=codec_name,codec_type,width,height,r_frame_rate,sample_rate,channels",
            "-of", "json", str(path),
        ],
        text=True,
    )
    return json.loads(out)


def fetch_everyayah_durations() -> dict[str, float]:
    CACHE.mkdir(parents=True, exist_ok=True)
    durs: dict[str, float] = {}
    for ayah, url in EVERYAYAH_URLS.items():
        try:
            dest = CACHE / f"everyayah_018{ayah}.mp3"
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=60) as resp, dest.open("wb") as out:
                out.write(resp.read())
            probe = ffprobe_json(dest)
            durs[str(ayah)] = round(float(probe["format"]["duration"]), 3)
        except Exception as e:
            log(f"WARN everyayah {ayah}: {e}")
    return durs


def fetch_and_trim_audio() -> str:
    CACHE.mkdir(parents=True, exist_ok=True)
    ASSETS.mkdir(parents=True, exist_ok=True)
    for url in AUDIO_URLS:
        try:
            log(f"downloading {url} -> {FULL_AUDIO}")
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=300) as resp, FULL_AUDIO.open("wb") as out:
                while True:
                    buf = resp.read(1024 * 1024)
                    if not buf:
                        break
                    out.write(buf)
            if FULL_AUDIO.stat().st_size > 5_000_000:
                dur_s = (END_MS - START_MS) / 1000.0
                subprocess.run(
                    [
                        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                        "-i", str(FULL_AUDIO),
                        "-ss", f"{START_MS / 1000.0:.3f}",
                        "-t", f"{dur_s:.3f}",
                        "-vn", "-ar", "44100", "-ac", "2", "-c:a", "aac", "-b:a", "192k",
                        str(RAW_RECITATION),
                    ],
                    check=True,
                )
                log(f"trimmed {RAW_RECITATION} ({RAW_RECITATION.stat().st_size} bytes)")
                return url
        except Exception as e:
            log(f"WARN: {url} failed: {e}")

    log("falling back to EveryAyah per-ayah MP3s")
    parts = []
    for ayah, url in EVERYAYAH_URLS.items():
        dest = CACHE / f"everyayah_018{ayah}.mp3"
        if not dest.exists() or dest.stat().st_size < 5000:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=120) as resp, dest.open("wb") as out:
                out.write(resp.read())
        parts.append(dest)
    concat_txt = CACHE / "concat003.txt"
    concat_txt.write_text("\n".join(f"file '{p.resolve()}'" for p in parts) + "\n", encoding="utf-8")
    subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_txt),
            "-vn", "-ar", "44100", "-ac", "2", "-c:a", "aac", "-b:a", "192k",
            str(RAW_RECITATION),
        ],
        check=True,
    )
    return "https://everyayah.com/data/Ali_Jaber_64kbps/ (018107-018108)"


def main() -> None:
    used_audio_url = fetch_and_trim_audio()
    ea_durs = fetch_everyayah_durations()

    rec_probe = ffprobe_json(RAW_RECITATION)

    (ASSETS / "selection.txt").write_text(
        "008 — cloudy mist-wrapped waterfall cliff, single continuous 247.4 s drone shot; "
        f"local window from {CLIP_WINDOW_START_S}s at 1.0x stretch (raw original colors)\n",
        encoding="utf-8",
    )

    SOURCE_MD.write_text(
        "\n".join(
            [
                "# Source assets — slot 003 · Al-Kahf 18:107–108 · Sheikh Ali Jaber",
                "",
                "Output: `outputs/quran-003_al-kahf_18-107-108_ali-jaber_en_1080x1920_v1.mp4`",
                "Post package: `metadata/003_al-kahf_18-107-108_ali-jaber/`",
                "",
                "## Recitation",
                "",
                "- Reciter: Sheikh Ali Abdullah Jaber (1953–2005), Murattal (Hafs 'an 'Asim).",
                f"- Audio source: {used_audio_url}",
                f"- Official ayah timing source: {TIMING_SOURCE_URL} (`18:107` 1677480–1689400 ms, `18:108` 1689400–1695840 ms).",
                f"- EveryAyah per-ayah reference durations (s): `{json.dumps(ea_durs)}`",
                f"- Raw excerpt trim: {START_MS}–{END_MS} ms (Surah Al-Kahf 18:107–108).",
                f"- Raw trim file: `recitation_raw.m4a` (`{sha256(RAW_RECITATION)}`, {RAW_RECITATION.stat().st_size} bytes).",
                f"- ffprobe: `{json.dumps(rec_probe, ensure_ascii=False)}`",
                "",
                "## Background clip (Pinterest board “K”, candidate 008 — unused until this slot)",
                "",
                f"- Pin id: {PIN_ID}",
                f"- Board: {BOARD_URL} (Jaqqd / jawed1025t)",
                f"- Full clip re-imported from git blob `{PIN_BLOB_SHA}` (commit 422b92c177ef5bd40a0761db318d1a7626a553f9, path `assets/al-baqarah-2-152-153/pinterest_candidates/`); full-clip sha256 `{PIN_CLIP_SHA256}` matches candidates.json.",
                f"- Used window: continuous segment starting at {CLIP_WINDOW_START_S}s of the 247.41 s single drone shot, length = audio master duration, stretch 1.0x (no slow-down).",
                "- Scene: cloud/mist-wrapped lush green cliff with waterfall — one continuous shot, 0 scene cuts, no people.",
                "- Color treatment: raw original colors preserved (no color grade).",
                "- Rights: user-supplied board; user stated no licence issue. Clear rights before commercial release.",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    log("all slot 003 source assets fetched and verified")


if __name__ == "__main__":
    main()
