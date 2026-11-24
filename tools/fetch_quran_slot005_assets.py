#!/usr/bin/env python3
"""Importer for Slot 005: Sa`ud ash-Shuraym Surah Maryam 19:30-31 (QF id 10).

Primary audio: QF per-ayah MP3s (audio.qurancdn.com/Shuraym/mp3/019030.mp3
+ 019031.mp3) joined with a 0.5 s waqf-like pause.
Fallback per file: QF chapter_recitations/10/19 full-surah MP3 trimmed to the
verse segment.

Voice-first assembly (005 retention revision): 0.35 s leading + voice track
+ 0.6 s trailing digital silence -> recitation_raw.m4a (~16 s, under 25 s cap).

Background: Pinterest board-K candidate 010 window 122-150 s (barrel wave,
verified single continuous shot, scan010/report010.json). The 28 s window is
NOT downloaded here - it is cut locally from git blob 33ae4dc4... (commit
422b92c) into jobs/<slot>/ before the render.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import urllib.request
from pathlib import Path

UA = "Mozilla/5.0 (compatible; content-plug-quran-slot005/1.0)"

QF_AYAH_URLS = {
    30: "https://audio.qurancdn.com/Shuraym/mp3/019030.mp3",
    31: "https://audio.qurancdn.com/Shuraym/mp3/019031.mp3",
}
QF_TIMING_URLS = {
    30: "https://api.quran.com/api/v4/verses/by_key/19:30?words=true&audio=10&word_fields=text_qpc_hafs",
    31: "https://api.quran.com/api/v4/verses/by_key/19:31?words=true&audio=10&word_fields=text_qpc_hafs",
}
QF_CHAPTER_URL = "https://api.quran.com/api/v4/chapter_recitations/10/19"
RWWAD_URLS = {
    30: "https://quranenc.com/api/v1/translation/aya/english_rwwad/19/30?without_footnotes_symbols=1",
    31: "https://quranenc.com/api/v1/translation/aya/english_rwwad/19/31?without_footnotes_symbols=1",
}

# 005 retention revision: voice-first onset (~0.40 s incl. first phoneme attack).
LEAD_PAD_S = 0.35  # recitation onset lands ~0.40 s, mid scroll-settle
GAP_S = 0.5        # waqf-like pause between the two ayat
TAIL_PAD_S = 0.6   # air for the 0.55 s true-loop match-dissolve + Haram reverb wash

PIN_ID = "e1_AfqPShw8bwXQoW1ZpriWAQUldapMdZi7nE5QXT1Gb78O0tRAksu7kw"
PIN_BLOB_SHA = "33ae4dc41e3a03e01532638aa2140fb2b484e308"
PIN_CLIP_SHA256 = "839f93bd8e665c4ca4536896eefb515b3c52d78b1792c6048801526c1526bff5"
PIN_BLOB_PATH = "assets/al-baqarah-2-152-153/pinterest_candidates/010_" + PIN_ID + ".mp4"
CLIP_LEN_S = 248.27
WINDOW_S = (122.0, 150.0)  # barrel wave, verified single continuous shot
BOARD_URL = "https://www.pinterest.com/jawed1025t/k/?invite_code=516f29ecb56e4a40a891ccc8089d146a&sender=1119215082304641687"

ROOT = Path(".")
SLOT = "005_maryam_19-30-31_shuraim"
ASSETS = ROOT / "assets" / "quran" / SLOT
CACHE = ROOT / ".cache"
AYAH_MP3 = {v: CACHE / f"shuraym_0190{v}.mp3" for v in (30, 31)}
CHAPTER_MP3 = CACHE / "shuraym_019.mp3"
TRIM_MP3 = {v: CACHE / f"shuraym_0190{v}_trim.mp3" for v in (30, 31)}
RAW_RECITATION = ASSETS / "recitation_raw.m4a"
SOURCE_MD = ASSETS / "SOURCE.md"


def log(msg: str) -> None:
    print(f"[slot-005] {msg}", flush=True)


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


def fetch_json(url: str, dest: Path, timeout: int = 120) -> dict:
    log(f"fetching JSON {url}")
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    dest.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return data


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


def fetch_fallback_chapter_trim(verse: int) -> tuple[str, str]:
    """Download full surah 19 and trim one verse. Returns (used_url, timing_note)."""
    req = urllib.request.Request(QF_CHAPTER_URL, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    seg = find_chapter_segment(data, verse)
    audio_url = find_audio_url(data)
    if seg is None or not audio_url:
        raise RuntimeError(f"fallback: chapter_recitations/10/19 gave no verse-{verse} segment or audio_url")
    start_ms, end_ms = seg
    if not audio_url.startswith("http"):
        audio_url = "https://audio.qurancdn.com/" + audio_url.lstrip("/")
    if not CHAPTER_MP3.exists():
        download(audio_url, CHAPTER_MP3)
    ss = max(0.0, (start_ms - 400) / 1000.0)
    dur = (end_ms - start_ms + 800) / 1000.0
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-i", str(CHAPTER_MP3), "-ss", f"{ss:.3f}", "-t", f"{dur:.3f}",
         "-vn", "-c:a", "copy", str(TRIM_MP3[verse])],
        check=True,
    )
    note = f"fallback chapter trim {start_ms - 400}-{end_ms + 400} ms of surah 19 (verse {verse})"
    return audio_url, note


def fetch_voice(verse: int) -> tuple[Path, str, str]:
    """Returns (voice_file, used_audio_url, timing_note) for one verse."""
    dest = AYAH_MP3[verse]
    try:
        download(QF_AYAH_URLS[verse], dest, timeout=120)
        if dest.stat().st_size < 5000:
            raise RuntimeError(f"ayah mp3 too small ({dest.stat().st_size} bytes)")
        return dest, QF_AYAH_URLS[verse], f"QF per-ayah mp3 0190{verse}"
    except Exception as e:
        log(f"WARN primary per-ayah mp3 19:{verse} failed ({e}); using chapter fallback")
        used_url, note = fetch_fallback_chapter_trim(verse)
        return TRIM_MP3[verse], used_url, note


def assemble_raw(f30: Path, f31: Path) -> tuple[float, dict]:
    """Join 19:30 + 0.5 s gap + 19:31, prepend 0.35 s, append 0.6 s silence."""
    d0 = float(ffprobe_json(f30)["format"]["duration"])
    d1 = float(ffprobe_json(f31)["format"]["duration"])
    total = LEAD_PAD_S + d0 + GAP_S + d1 + TAIL_PAD_S
    fc = (
        "[0:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[v0];"
        "[1:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[v1];"
        f"aevalsrc=0:d={GAP_S}:s=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[gap];"
        "[v0][gap][v1]concat=n=3:v=0:a=1,"
        f"adelay={int(LEAD_PAD_S * 1000)}:all=1,apad=whole_dur={total:.3f}[aout]"
    )
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-i", str(f30), "-i", str(f31), "-filter_complex", fc,
         "-map", "[aout]", "-vn", "-ar", "44100", "-ac", "2",
         "-c:a", "aac", "-b:a", "192k", str(RAW_RECITATION)],
        check=True,
    )
    concat_map = {
        "lead_s": LEAD_PAD_S,
        "file30_s": round(d0, 3),
        "gap_s": GAP_S,
        "file31_offset_s": round(LEAD_PAD_S + d0 + GAP_S, 3),
        "file31_s": round(d1, 3),
        "tail_s": TAIL_PAD_S,
        "total_s": round(total, 3),
    }
    (ASSETS / "concat_map.json").write_text(
        json.dumps(concat_map, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return float(ffprobe_json(RAW_RECITATION)["format"]["duration"]), concat_map


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    ASSETS.mkdir(parents=True, exist_ok=True)

    f30, url30, note30 = fetch_voice(30)
    f31, url31, note31 = fetch_voice(31)

    qf30 = fetch_json(QF_TIMING_URLS[30], ASSETS / "qf_19-30.json")
    qf31 = fetch_json(QF_TIMING_URLS[31], ASSETS / "qf_19-31.json")
    fetch_json(RWWAD_URLS[30], ASSETS / "rwwad_19-30.json")
    fetch_json(RWWAD_URLS[31], ASSETS / "rwwad_19-31.json")

    def seg_span(qf: dict) -> str:
        segs = qf["verse"]["audio"]["segments"]
        return f"first word {segs[0][2]} ms, last word ends {segs[-1][3]} ms"

    timing_note = f"19:30 [{seg_span(qf30)}] ({note30}); 19:31 [{seg_span(qf31)}] ({note31})"

    raw_dur, concat_map = assemble_raw(f30, f31)
    log(f"raw recitation {RAW_RECITATION} ({RAW_RECITATION.stat().st_size} bytes, {raw_dur:.3f} s)")
    if raw_dur > 25.0:
        raise RuntimeError(f"raw recitation {raw_dur:.3f} s exceeds the 25 s cap")
    win_len = WINDOW_S[1] - WINDOW_S[0]
    speed = raw_dur / win_len  # 1.0x target: sub-window cut, no stretch needed

    rec_probe = ffprobe_json(RAW_RECITATION)
    sil = silence_report(RAW_RECITATION)

    (ASSETS / "selection.txt").write_text(
        "010 window 122-150 s - turquoise barrel wave curling and glowing from within, "
        "white spray crown against a steel-blue sky; single continuous shot, 0 cuts, no people, "
        "no text; sub-window cut to the card duration at 1.0x (raw original colors)\n",
        encoding="utf-8",
    )

    SOURCE_MD.write_text(
        "\n".join(
            [
                "# Source assets - slot 005 - Maryam 19:30-31 - Sa`ud ash-Shuraym",
                "",
                "Output: `outputs/quran-005_maryam_19-30-31_shuraim_en_1080x1920_v1.mp4`",
                "Post package: `metadata/005_maryam_19-30-31_shuraim/`",
                "",
                "## Recitation",
                "",
                "- Reciter: Sa`ud ash-Shuraym, Murattal (Hafs 'an 'Asim), QF chapter-reciter ID 10.",
                f"- Audio sources: {url30} + {url31} joined with a {GAP_S} s waqf-like pause.",
                f"- Timing sources: {QF_TIMING_URLS[30]} and {QF_TIMING_URLS[31]}",
                "  (mirrored to `qf_19-30.json` / `qf_19-31.json`).",
                f"- {timing_note}.",
                "- English: Rwwad translation via QuranEnc",
                f"  ({RWWAD_URLS[30]}, {RWWAD_URLS[31]}, mirrored to `rwwad_19-*.json`).",
                f"- Raw assembly (voice-first): {LEAD_PAD_S} s leading + voice track + {TAIL_PAD_S} s trailing",
                f"  digital silence -> `recitation_raw.m4a` ({raw_dur:.3f} s, under the 25 s cap).",
                f"- Concat map: `{json.dumps(concat_map)}` (also `concat_map.json`).",
                f"- Raw trim file: `recitation_raw.m4a` (`{sha256(RAW_RECITATION)}`, "
                f"{RAW_RECITATION.stat().st_size} bytes).",
                f"- ffprobe: `{json.dumps(rec_probe, ensure_ascii=False)}`",
                f"- silencedetect (-45 dB): `{json.dumps(sil)}`",
                "",
                "## Background clip (Pinterest board \"K\", candidate 010 - unused until this slot)",
                "",
                f"- Pin id: {PIN_ID}",
                f"- Board: {BOARD_URL} (Jaqqd / jawed1025t)",
                f"- Full clip re-imported from git blob `{PIN_BLOB_SHA}` (commit 422b92c177ef5bd40a0761db318d1a7626a553f9, "
                f"path `{PIN_BLOB_PATH}`); full-clip sha256 `{PIN_CLIP_SHA256}`.",
                f"- Used window: {WINDOW_S[0]:.0f}-{WINDOW_S[1]:.0f} s of the {CLIP_LEN_S} s montage "
                "(cut list + stills: `scan010/report010.json`); the window is a single continuous "
                f"shot (0 cuts) covering the {raw_dur:.3f} s card at {speed:.4f}x "
                "(sub-window cut, no stretch).",
                "- Scene: turquoise barrel wave curling left-to-right and glowing from within, white "
                "spray crown, steel-blue sky - no people, no text.",
                "- Color treatment: raw original colors preserved (no color grade).",
                "- Rights: user-supplied board; user stated no licence issue. Clear rights before commercial release.",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    log("all slot 005 source assets fetched and verified")


if __name__ == "__main__":
    main()
