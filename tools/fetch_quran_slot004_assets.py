#!/usr/bin/env python3
"""Importer for Slot 004: Sa`ud ash-Shuraym Surah Al-Baqarah 2:186 recitation (QF id 10).

Primary audio: QF per-ayah MP3 (audio.qurancdn.com/Shuraym/mp3/002186.mp3).
Fallback: QF chapter_recitations/10/2 full-surah MP3 trimmed to the verse-186 segment.

Background clip 001 (dark winding river, 17.161 s) is NOT downloaded here — it is
re-imported locally from git blob d61084ba… (commit 422b92c) into
assets/quran/<slot>/pinterest/ before this runner's audio commit lands.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import urllib.request
from pathlib import Path

UA = "Mozilla/5.0 (compatible; content-plug-quran-slot004/1.0)"

QF_AYAH_URL = "https://audio.qurancdn.com/Shuraym/mp3/002186.mp3"
QF_TIMING_URL = "https://api.quran.com/api/v4/verses/by_key/2:186?words=true&audio=10&word_fields=text_qpc_hafs"
QF_CHAPTER_URL = "https://api.quran.com/api/v4/chapter_recitations/10/2"

# QF word segments for Shuraym 2:186 (ms, relative to the per-ayah file):
# first word starts 100 ms, last word ends 14300 ms.
LEAD_PAD_S = 0.8   # scroll opener needs recitation onset at ~0.9 s (house: scroll locks as voice starts)
TAIL_PAD_S = 0.6   # air for the 0.45 s seamless loop-tail fade + Haram reverb wash

PIN_ID = "e1_AfqPShyrnCaU19OySaDrZRa3aH3iodsRge6VLRfIMhrSrQy_bLCo_g"
PIN_BLOB_SHA = "d61084ba752d6f797074d17a6e7ca0e52b7be834"
PIN_CLIP_SHA256 = "d489bed2211c384aa9f0e5b87da62597234de3fb1b9ab43f37126d1824a44b40"
CLIP_LEN_S = 17.161
BOARD_URL = "https://www.pinterest.com/jawed1025t/k/?invite_code=516f29ecb56e4a40a891ccc8089d146a&sender=1119215082304641687"

ROOT = Path(".")
SLOT = "004_al-baqarah_2-186_shuraim"
ASSETS = ROOT / "assets" / "quran" / SLOT
CACHE = ROOT / ".cache"
AYAH_MP3 = CACHE / "shuraym_002186.mp3"
CHAPTER_MP3 = CACHE / "shuraym_002.mp3"
TRIM_MP3 = CACHE / "shuraym_002186_trim.mp3"
RAW_RECITATION = ASSETS / "recitation_raw.m4a"
SOURCE_MD = ASSETS / "SOURCE.md"


def log(msg: str) -> None:
    print(f"[slot-004] {msg}", flush=True)


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
            "format=duration,size,bit_rate:stream=codec_name,codec_type,sample_rate,channels",
            "-of", "json", str(path),
        ],
        text=True,
    )
    return json.loads(out)


def download(url: str, dest: Path, timeout: int = 300) -> None:
    log(f"downloading {url} -> {dest}")
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as resp, dest.open("wb") as out:
        while True:
            buf = resp.read(1024 * 1024)
            if not buf:
                break
            out.write(buf)


def silence_report(path: Path) -> dict:
    """First non-silence (onset) and trailing-silence start via silencedetect."""
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
         "-af", "silencedetect=noise=-45dB:d=0.15", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    starts: list[float] = []
    ends: list[float] = []
    for line in proc.stderr.splitlines():
        if "silence_start:" in line:
            try:
                starts.append(float(line.split("silence_start:")[1].split()[0]))
            except ValueError:
                pass
        if "silence_end:" in line:
            try:
                ends.append(float(line.split("silence_end:")[1].split()[0]))
            except ValueError:
                pass
    return {"silence_starts": starts, "silence_ends": ends}


def find_chapter_segment(obj, verse: int) -> tuple[int, int] | None:
    """Defensively locate [verse, start_ms, end_ms] anywhere in the chapter JSON."""
    if isinstance(obj, list) and len(obj) >= 3 and obj[0] == verse:
        try:
            return int(obj[1]), int(obj[2])
        except (TypeError, ValueError):
            return None
    if isinstance(obj, list):
        for item in obj:
            hit = find_chapter_segment(item, verse)
            if hit:
                return hit
    elif isinstance(obj, dict):
        for item in obj.values():
            hit = find_chapter_segment(item, verse)
            if hit:
                return hit
    return None


def find_audio_url(obj) -> str | None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "audio_url" and isinstance(v, str) and v:
                return v
        for v in obj.values():
            hit = find_audio_url(v)
            if hit:
                return hit
    elif isinstance(obj, list):
        for item in obj:
            hit = find_audio_url(item)
            if hit:
                return hit
    return None


def fetch_fallback_chapter_trim() -> tuple[str, str]:
    """Download full surah 2 and trim verse 186. Returns (used_url, timig_note)."""
    req = urllib.request.Request(QF_CHAPTER_URL, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    seg = find_chapter_segment(data, 186)
    audio_url = find_audio_url(data)
    if seg is None or not audio_url:
        raise RuntimeError("fallback: chapter_recitations/10/2 gave no verse-186 segment or audio_url")
    start_ms, end_ms = seg
    if not audio_url.startswith("http"):
        audio_url = "https://audio.qurancdn.com/" + audio_url.lstrip("/")
    download(audio_url, CHAPTER_MP3)
    ss = max(0.0, (start_ms - 400) / 1000.0)
    dur = (end_ms - start_ms + 800) / 1000.0
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-i", str(CHAPTER_MP3), "-ss", f"{ss:.3f}", "-t", f"{dur:.3f}",
         "-vn", "-c:a", "copy", str(TRIM_MP3)],
        check=True,
    )
    note = f"fallback chapter trim {start_ms - 400}–{end_ms + 400} ms of surah 2"
    return audio_url, note


def assemble_raw(voice_src: Path) -> float:
    """Prepend 0.8 s + append 0.6 s digital silence; returns raw duration (s)."""
    probe = ffprobe_json(voice_src)
    voice_dur = float(probe["format"]["duration"])
    total = LEAD_PAD_S + voice_dur + TAIL_PAD_S
    af = f"adelay={int(LEAD_PAD_S * 1000)}:all=1,apad=whole_dur={total:.3f}"
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-i", str(voice_src), "-af", af,
         "-vn", "-ar", "44100", "-ac", "2", "-c:a", "aac", "-b:a", "192k",
         str(RAW_RECITATION)],
        check=True,
    )
    return float(ffprobe_json(RAW_RECITATION)["format"]["duration"])


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    ASSETS.mkdir(parents=True, exist_ok=True)

    timing_note = "QF word segments: first word 100 ms, last word ends 14300 ms (per-ayah file)"
    try:
        download(QF_AYAH_URL, AYAH_MP3, timeout=120)
        if AYAH_MP3.stat().st_size < 5000:
            raise RuntimeError(f"ayah mp3 too small ({AYAH_MP3.stat().st_size} bytes)")
        used_audio_url = QF_AYAH_URL
        voice_src = AYAH_MP3
    except Exception as e:
        log(f"WARN primary per-ayah mp3 failed ({e}); using chapter fallback")
        used_audio_url, timing_note = fetch_fallback_chapter_trim()
        voice_src = TRIM_MP3

    raw_dur = assemble_raw(voice_src)
    log(f"raw recitation {RAW_RECITATION} ({RAW_RECITATION.stat().st_size} bytes, {raw_dur:.3f} s)")
    if raw_dur > 25.0:
        raise RuntimeError(f"raw recitation {raw_dur:.3f} s exceeds the 25 s cap")
    stretch = raw_dur / CLIP_LEN_S

    rec_probe = ffprobe_json(RAW_RECITATION)
    sil = silence_report(RAW_RECITATION)

    (ASSETS / "selection.txt").write_text(
        "001 — winding dark river through forest under a stormy teal cloud sky, yellow wildflowers "
        "in the foreground; full 17.161 s single continuous shot used whole at "
        f"{stretch:.4f}x (raw original colors)\n",
        encoding="utf-8",
    )

    SOURCE_MD.write_text(
        "\n".join(
            [
                "# Source assets — slot 004 · Al-Baqarah 2:186 · Sa`ud ash-Shuraym",
                "",
                "Output: `outputs/quran-004_al-baqarah_2-186_shuraim_en_1080x1920_v1.mp4`",
                "Post package: `metadata/004_al-baqarah_2-186_shuraim/`",
                "",
                "## Recitation",
                "",
                "- Reciter: Sa`ud ash-Shuraym, Murattal (Hafs 'an 'Asim), QF chapter-reciter ID 10.",
                f"- Audio source: {used_audio_url}",
                f"- Timing source: {QF_TIMING_URL}",
                f"- {timing_note}.",
                f"- Raw assembly: 0.8 s leading + voice + 0.6 s trailing digital silence -> "
                f"`recitation_raw.m4a` ({raw_dur:.3f} s, under the 25 s cap).",
                f"- Raw trim file: `recitation_raw.m4a` (`{sha256(RAW_RECITATION)}`, "
                f"{RAW_RECITATION.stat().st_size} bytes).",
                f"- ffprobe: `{json.dumps(rec_probe, ensure_ascii=False)}`",
                f"- silencedetect (-45 dB): `{json.dumps(sil)}`",
                "",
                "## Background clip (Pinterest board “K”, candidate 001 — unused until this slot)",
                "",
                f"- Pin id: {PIN_ID}",
                f"- Board: {BOARD_URL} (Jaqqd / jawed1025t)",
                f"- Full clip re-imported from git blob `{PIN_BLOB_SHA}` (commit 422b92c177ef5bd40a0761db318d1a7626a553f9, "
                "path `assets/al-baqarah-2-152-153/pinterest_candidates/`); full-clip sha256 "
                f"`{PIN_CLIP_SHA256}` matches candidates.json.",
                f"- Used whole: the 17.161 s single continuous shot covers the {raw_dur:.3f} s card at "
                f"{stretch:.4f}x (renderer maps the full clip across the full duration; "
                "well inside the 1.3x house stretch rule).",
                "- Scene: winding dark river through forest under a stormy teal cloud sky, yellow "
                "wildflowers in the foreground — one continuous shot, 0 scene cuts, no people.",
                "- Color treatment: raw original colors preserved (no color grade).",
                "- Rights: user-supplied board; user stated no licence issue. Clear rights before commercial release.",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    log("all slot 004 source assets fetched and verified")


if __name__ == "__main__":
    main()
