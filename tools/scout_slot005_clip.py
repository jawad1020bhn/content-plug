#!/usr/bin/env python3
"""Scout the Slot 005 YouTube clip (runs in GitHub Actions; results committed to git).

YouTube bot-checks datacenter IPs aggressively, so every yt-dlp phase cycles
player clients [default, android, ios, tv, web_embedded]. Never dies silently:
always writes report.json (status ok/failed + per-phase errors) for the commit step.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import numpy as np

URL = "https://www.youtube.com/watch?v=hjeiLKHO610"
WORK = Path("scout005")

YT_CLIENTS: list[str | None] = [None, "android", "ios", "tv", "web_embedded"]

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


def yt_base(client: str | None) -> list[str]:
    args = ["yt-dlp", "--no-playlist", "--force-ipv4", "--retries", "3",
            "--socket-timeout", "30"]
    if client:
        args += ["--extractor-args", f"youtube:player_client={client}"]
    return args


def phase_meta(errors: list[str]) -> dict | None:
    for client in YT_CLIENTS:
        p = run(yt_base(client) + ["--dump-json", URL], timeout=180)
        if p.returncode == 0:
            try:
                meta = json.loads(p.stdout)
                META_JSON.write_text(json.dumps(meta, indent=1)[:20000], encoding="utf-8")
                log(f"meta OK via client={client or 'default'}")
                return {"meta": meta, "client": client or "default"}
            except json.JSONDecodeError:
                errors.append(f"meta client={client}: bad JSON")
        else:
            errors.append(f"meta client={client}: {p.stderr.strip()[-200:]}")
    return None


def phase_download(errors: list[str]) -> str | None:
    fmt = "bv*[height<=720][ext=mp4]+ba[ext=m4a]/b[height<=720]/b"
    for client in YT_CLIENTS:
        if MP4.exists():
            MP4.unlink()
        p = run(yt_base(client) + ["-f", fmt, "--merge-output-format", "mp4",
                                   "-o", str(MP4), URL], timeout=1200)
        if p.returncode == 0 and MP4.exists() and MP4.stat().st_size > 1_000_000:
            log(f"download OK via client={client or 'default'} "
                f"({MP4.stat().st_size / 1e6:.1f} MB)")
            return client or "default"
        errors.append(f"download client={client}: rc={p.returncode} {p.stderr.strip()[-200:]}")
    return None


def phase_subs(errors: list[str]) -> list[str]:
    for client in YT_CLIENTS:
        p = run(yt_base(client) + ["--write-auto-sub", "--write-sub",
                                   "--sub-langs", "id.*,en.*,ar.*",
                                   "--sub-format", "vtt", "--skip-download",
                                   "-o", str(WORK / "subs"), URL], timeout=300)
        got = sorted(f.name for f in WORK.glob("subs.*.vtt"))
        if got:
            log(f"subs OK via client={client or 'default'}: {got}")
            return got
        errors.append(f"subs client={client}: rc={p.returncode}")
    return []


def ffprobe_json(path: Path) -> dict:
    p = run(["ffprobe", "-v", "error", "-show_entries",
             "format=duration,size,bit_rate:stream=codec_name,codec_type,width,height,r_frame_rate,sample_rate,channels",
             "-of", "json", str(path)])
    return json.loads(p.stdout)


def vtt_ts(ts: str) -> float:
    h, m, rest = ts.split(":")
    return int(h) * 3600 + int(m) * 60 + float(rest.replace(",", "."))


def parse_vtt(path: Path) -> list[dict]:
    segs: list[dict] = []
    text = path.read_text(encoding="utf-8", errors="replace")
    for m in re.finditer(
        r"(\d{2}:\d{2}:\d{2}[.,]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[.,]\d{3})\s*\n(.*?)(?=\n\n|\Z)",
        text, re.S):
        words = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(3))).strip()
        if words:
            segs.append({"t0": vtt_ts(m.group(1)), "t1": vtt_ts(m.group(2)), "text": words})
    return segs


def analyze_av(report: dict) -> None:
    report["probe"] = ffprobe_json(MP4)
    fdur = float(report["probe"]["format"]["duration"])

    step = max(1.0, fdur / 12.0)
    p = run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(MP4),
             "-vf", f"select='isnan(prev_selected_t)+gte(t-prev_selected_t\\,{step:.2f})',"
                    "scale=320:180,tile=12x1:margin=4:color=black",
             "-frames:v", "1", str(STRIP)])
    report["strip_ok"] = p.returncode == 0 and STRIP.exists()

    stills = []
    for frac in (0.25, 0.5, 0.75):
        out = WORK / f"still_{int(frac * 100)}.png"
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             "-ss", f"{fdur * frac:.1f}", "-i", str(MP4),
             "-frames:v", "1", "-vf", "scale=960:-1", str(out)])
        if out.exists():
            stills.append(out.name)

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
        "suspected_cut_count": len(cuts),
        "suspected_cuts_s": cuts[:40],
        "looks_static": bool(diffs and max(diffs) < 3.0),
        "stills": stills,
    }

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


def main() -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    report: dict = {"url": URL, "status": "failed"}

    got_meta = phase_meta(errors)
    if got_meta:
        meta = got_meta["meta"]
        report["meta"] = {
            "title": meta.get("title"),
            "uploader": meta.get("uploader"),
            "duration_s": meta.get("duration"),
            "view_count": meta.get("view_count"),
            "client": got_meta["client"],
        }
    dl_client = phase_download(errors)
    if dl_client:
        report["download_client"] = dl_client
        try:
            analyze_av(report)
            subs = phase_subs(errors)
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
            report["status"] = "ok"
        except Exception as e:  # noqa: BLE001 — diagnostics must survive
            errors.append(f"analyze: {type(e).__name__}: {e}")
    report["errors"] = errors[-14:]
    REPORT.write_text(json.dumps(report, indent=1), encoding="utf-8")
    log(f"scout done status={report['status']} errors={len(errors)}")


if __name__ == "__main__":
    main()
