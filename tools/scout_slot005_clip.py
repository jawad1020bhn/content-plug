#!/usr/bin/env python3
"""Scout the Slot 005 YouTube clip (runs in GitHub Actions; uploads artifacts, commits nothing).

Downloads 720p, then reports: metadata, A/V probe, 12-thumb contact sheet,
full-res stills (burned-text check), cut/static detection, audio-bed fingerprint
(pause residual spectrum: silence vs rain vs music), loudness, stereo correlation,
and auto-caption keyword timestamps for viral-ayah hunting.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import numpy as np

URL = "https://www.youtube.com/watch?v=hjeiLKHO610"
WORK = Path("scout005")

META_JSON = WORK / "meta.json"
MP4 = WORK / "clip.mp4"
STRIP = WORK / "scout.png"
REPORT = WORK / "report.json"

VIRAL_PATTERNS = [
    "kun", "fayakun", "fayakoon", "maryam", "yahya", "isa", "isaa", "zakariya",
    "rahman", "rahmaan", "rahiim", "raheem", "salam", "jannah", "surga", "surga",
    "rabbi", "rabbana", "allah", "subhan", "mubin", "nur", "noor", "shifa",
]


def log(msg: str) -> None:
    print(f"[scout-005] {msg}", flush=True)


def run(cmd: list[str], timeout: int = 900) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def ytdlp_meta() -> dict:
    p = run(["yt-dlp", "--dump-json", "--no-playlist", URL])
    if p.returncode != 0:
        raise RuntimeError(f"yt-dlp meta failed: {p.stderr[-500:]}")
    meta = json.loads(p.stdout)
    META_JSON.write_text(json.dumps(meta, indent=1)[:20000], encoding="utf-8")
    return meta


def ytdlp_download() -> str:
    fmt = "bv*[height<=720][ext=mp4]+ba[ext=m4a]/b[height<=720]/b"
    attempts = [
        ["yt-dlp", "--no-playlist", "-f", fmt, "--merge-output-format", "mp4",
         "--retries", "5", "-o", str(MP4), URL],
        ["yt-dlp", "--no-playlist", "-f", fmt, "--merge-output-format", "mp4",
         "--retries", "5", "--extractor-args", "youtube:player_client=android",
         "-o", str(MP4), URL],
    ]
    for cmd in attempts:
        p = run(cmd, timeout=1200)
        if p.returncode == 0 and MP4.exists() and MP4.stat().st_size > 1_000_000:
            return " ".join(cmd[1:4])
    raise RuntimeError(f"yt-dlp download failed: {p.stderr[-800:]}")


def ytdlp_subs() -> list[str]:
    p = run(["yt-dlp", "--no-playlist", "--write-auto-sub", "--write-sub",
             "--sub-langs", "id.*,en.*,ar.*", "--sub-format", "vtt",
             "--skip-download", "-o", str(WORK / "subs"), URL], timeout=300)
    got = sorted(str(f.name) for f in WORK.glob("subs.*.vtt"))
    log(f"subs: {got or 'none'} (rc={p.returncode})")
    return got


def ffprobe_json(path: Path) -> dict:
    p = run(["ffprobe", "-v", "error", "-show_entries",
             "format=duration,size,bit_rate:stream=codec_name,codec_type,width,height,r_frame_rate,sample_rate,channels",
             "-of", "json", str(path)])
    return json.loads(p.stdout)


def vtt_ts(ts: str) -> float:
    h, m, rest = ts.split(":")
    s = rest.replace(",", ".")
    return int(h) * 3600 + int(m) * 60 + float(s)


def parse_vtt(path: Path) -> list[dict]:
    segs: list[dict] = []
    text = path.read_text(encoding="utf-8", errors="replace")
    for m in re.finditer(
        r"(\d{2}:\d{2}:\d{2}[.,]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[.,]\d{3})\s*\n(.*?)(?=\n\n|\Z)",
        text, re.S):
        words = re.sub(r"<[^>]+>", " ", m.group(3))
        words = re.sub(r"\s+", " ", words).strip()
        if words:
            segs.append({"t0": vtt_ts(m.group(1)), "t1": vtt_ts(m.group(2)), "text": words})
    return segs


def main() -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    report: dict = {"url": URL}

    meta = ytdlp_meta()
    dur = float(meta.get("duration") or 0)
    report["meta"] = {
        "title": meta.get("title"),
        "uploader": meta.get("uploader"),
        "duration_s": dur,
        "view_count": meta.get("view_count"),
        "chapters": bool(meta.get("chapters")),
        "description_head": (meta.get("description") or "")[:600],
    }
    log(f"meta: {report['meta']['title']} ({dur:.0f}s)")

    report["download"] = ytdlp_download()
    report["probe"] = ffprobe_json(MP4)
    f dur = float(report["probe"]["format"]["duration"])
    log(f"downloaded {MP4.stat().st_size / 1e6:.1f} MB, {fdur:.1f}s")

    step = max(1.0, fdur / 12.0)
    p = run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(MP4),
             "-vf", f"select='isnan(prev_selected_t)+gte(t-prev_selected_t\\,{step:.2f})',"
                    "scale=320:180,tile=12x1:margin=4:color=black",
             "-frames:v", "1", str(STRIP)])
    log(f"contact sheet rc={p.returncode}")

    stills = []
    for frac in (0.25, 0.5, 0.75):
        out = WORK / f"still_{int(frac * 100)}.png"
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             "-ss", f"{fdur * frac:.1f}", "-i", str(MP4),
             "-frames:v", "1", "-vf", "scale=960:-1", str(out)])
        stills.append(out.name)

    # Cut / static detection: 1 frame per 10 s @160x90 gray.
    raw = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(MP4),
         "-vf", "fps=1/10,scale=160:90,format=gray", "-f", "rawvideo", "pipe:1"],
        capture_output=True, timeout=900).stdout
    fr = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 90, 160).astype(np.float32)
    diffs = [float(np.mean(np.abs(fr[i] - fr[i - 1]))) for i in range(1, len(fr))]
    cuts = [round(i * 10.0, 1) for i, d in enumerate(diffs, 1) if d > 40.0]
    report["video"] = {
        "sampled_frames": len(fr),
        "mean_diff": round(float(np.mean(diffs)), 2) if diffs else None,
        "max_diff": round(float(np.max(diffs)), 2) if diffs else None,
        "suspected_cuts_s": cuts[:40],
        "suspected_cut_count": len(cuts),
        "looks_static": bool(diffs and max(diffs) < 3.0),
        "stills": stills,
    }
    log(f"video: {len(fr)} samples, maxdiff={report['video']['max_diff']}, cuts={len(cuts)}")

    # Audio: loudness + stereo correlation + pause-bed fingerprint.
    p = run(["ffmpeg", "-hide_banner", "-i", str(MP4),
             "-af", "loudnorm=print_format=summary", "-f", "null", "-"])
    loud = {}
    for line in p.stderr.splitlines():
        m = re.match(r"Input (Integrated|True Peak|LRA)\s*:\s*(.+)", line.strip())
        if m:
            loud[m.group(1)] = m.group(2).strip()
    report["loudness"] = loud

    pcm = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(MP4),
         "-ac", "2", "-ar", "8000", "-f", "f32le", "pipe:1"],
        capture_output=True, timeout=900).stdout
    stereo = np.frombuffer(pcm, dtype=np.float32).reshape(-1, 2)
    if len(stereo) > 1000:
        c = np.corrcoef(stereo[::10, 0], stereo[::10, 1])[0, 1]
        report["stereo_corr"] = round(float(c), 4)
    mono = stereo.mean(axis=1)

    # Pause bed: 10 quietest 0.5 s regions (skip first/last 5 s), band fingerprint.
    hop = 4000
    frames = [mono[i:i + hop] for i in range(0, len(mono) - hop, hop)]
    rms = np.array([float(np.sqrt(np.mean(f ** 2) + 1e-12)) for f in frames])
    order = np.argsort(rms)
    beds = []
    sr = 8000
    freqs = np.fft.rfftfreq(hop, 1 / sr)
    bands = [(20, 120), (120, 500), (500, 2000), (2000, 4000)]
    for idx in order[:60]:
        t = idx * 0.5
        if t < 5 or t > len(mono) / sr - 5:
            continue
        seg = frames[idx].astype(np.float64)
        spec = np.abs(np.fft.rfft(seg * np.hanning(hop))) ** 2 + 1e-18
        flat = float(np.exp(np.mean(np.log(spec))) / np.mean(spec))
        e = [float(spec[(freqs >= lo) & (freqs < hi)].sum()) for lo, hi in bands]
        tot = sum(e) + 1e-18
        beds.append({
            "t": round(t, 1),
            "rms_db": round(float(20 * np.log10(rms[idx] + 1e-9)), 1),
            "flatness": round(flat, 4),
            "bands": [round(x / tot, 3) for x in e],
        })
        if len(beds) >= 10:
            break
    report["pause_bed"] = beds
    med_db = float(np.median([b["rms_db"] for b in beds])) if beds else None
    med_flat = float(np.median([b["flatness"] for b in beds])) if beds else None
    if med_db is not None and med_db < -70:
        bed_verdict = "digital-silence pauses (clean studio recitation, no rain/music bed)"
    elif med_flat is not None and med_flat > 0.45:
        bed_verdict = "noise-like bed in pauses (rain/hiss ambience likely)"
    else:
        bed_verdict = "tonal/low bed in pauses (music/echo tail possible — inspect)"
    report["bed_verdict"] = bed_verdict
    log(f"audio: {loud} corr={report.get('stereo_corr')} bed={bed_verdict}")

    # Captions: keyword timestamps for viral-ayah hunting.
    subs = ytdlp_subs()
    cap_hits: dict[str, list[dict]] = {}
    cap_count = 0
    for name in subs:
        segs = parse_vtt(WORK / name)
        cap_count = max(cap_count, len(segs))
        for s in segs:
            low = s["text"].lower()
            for pat in VIRAL_PATTERNS:
                if pat in low:
                    cap_hits.setdefault(pat, []).append(
                        {"t0": s["t0"], "file": name, "text": s["text"][:90]})
                    break
    report["captions"] = {"files": subs, "segments": cap_count,
                          "hits": {k: v[:8] for k, v in cap_hits.items()}}
    log(f"captions: {cap_count} segs, {len(cap_hits)} patterns hit")

    REPORT.write_text(json.dumps(report, indent=1), encoding="utf-8")
    log("scout complete -> scout005/ (uploaded as artifact)")


if __name__ == "__main__":
    main()
