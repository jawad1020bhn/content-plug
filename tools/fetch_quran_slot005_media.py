#!/usr/bin/env python3
"""Slot 005 media acquisition (runs in GitHub Actions; small results committed to git).

YouTube blocks yt-dlp from datacenter IPs, so the 27-min Maryam audio is fetched
via Piped / Invidious / cobalt API frontends (audio-only). Then faster-whisper
transcribes it (Arabic, word timestamps) and distinctive phrases locate viral-ayah
candidates (19:96, 19:64, 19:35, ...). Also builds a contact sheet for Pinterest
clip 010 (from git blob) so the popup window can be chosen. Never dies silently:
always writes report.json.
"""

from __future__ import annotations

import json
import re
import subprocess
import unicodedata
import urllib.request
from pathlib import Path

import numpy as np

VIDEO_ID = "hjeiLKHO610"
WATCH_URL = f"https://www.youtube.com/watch?v={VIDEO_ID}"
UA = "Mozilla/5.0 (compatible; content-plug-quran-slot005/1.0)"

WORK = Path("media005")
AUDIO = WORK / "maryam_audio.m4a"
TRANSCRIPT = WORK / "transcript.json"
REPORT = WORK / "report.json"
SHEET010 = WORK / "sheet010.png"

CLIP010_BLOB_PATH = "422b92c177ef5bd40a0761db318d1a7626a553f9:assets/al-baqarah-2-152-153/pinterest_candidates/010_e1_AfqPShw8bwXQoW1ZpriWAQUldapMdZi7nE5QXT1Gb78O0tRAksu7kw.mp4"

# ayah -> distinctive normalized phrase (matched in the Arabic transcript)
CANDIDATES = {
    "19:96": "سيجعل لهم الرحمن ودا",
    "19:64": "وما كان ربك نسيا",
    "19:35": "كن فيكون",
    "19:36": "ربي وربكم فاعبدوه",
    "19:21": "هو علي هين",
    "19:65": "هل تعلم له سميا",
    "19:12": "خذ الكتاب بقوه",
    "19:15": "ويوم يبعث حيا",
}


def log(msg: str) -> None:
    print(f"[media-005] {msg}", flush=True)


def run(cmd: list[str], timeout: int = 900) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def http_get(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def http_post_json(url: str, payload: dict, timeout: int = 60) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={
        "User-Agent": UA, "Accept": "application/json", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def download_file(url: str, dest: Path, timeout: int = 900) -> int:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    n = 0
    with urllib.request.urlopen(req, timeout=timeout) as resp, dest.open("wb") as out:
        while True:
            buf = resp.read(1024 * 1024)
            if not buf:
                break
            out.write(buf)
            n += len(buf)
    return n


def ffprobe_duration(path: Path) -> float:
    p = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "json", str(path)])
    return float(json.loads(p.stdout)["format"]["duration"])


def try_piped(errors: list[str]) -> str | None:
    instances = ["pipedapi.adminforge.de", "pipedapi.leptons.xyz",
                 "pipedapi.reallyaweso.me", "api-piped.mha.fi",
                 "pipedapi-libre.kavin.rocks", "pipedapi.nosebs.ru"]
    for host in instances:
        try:
            data = json.loads(http_get(f"https://{host}/streams/{VIDEO_ID}"))
            streams = data.get("audioStreams") or []
            if not streams:
                errors.append(f"piped {host}: no audioStreams")
                continue
            streams.sort(key=lambda s: s.get("bitrate") or 0, reverse=True)
            got = download_file(streams[0]["url"], AUDIO)
            if got > 1_000_000 and 1200 < ffprobe_duration(AUDIO) < 2200:
                return f"piped {host} ({streams[0].get('codec')} {streams[0].get('bitrate')})"
            errors.append(f"piped {host}: bad file ({got} bytes)")
        except Exception as e:  # noqa: BLE001
            errors.append(f"piped {host}: {type(e).__name__}: {str(e)[:120]}")
    return None


def try_invidious(errors: list[str]) -> str | None:
    instances = ["inv.tux.pizza", "iv.melmac.space", "invidious.nerdvpn.de",
                 "yewtu.be", "inv.zzls.xyz"]
    for host in instances:
        try:
            data = json.loads(http_get(f"https://{host}/api/v1/videos/{VIDEO_ID}"))
            fmts = [f for f in (data.get("adaptiveFormats") or [])
                    if f.get("type", "").startswith("audio/")]
            if not fmts:
                errors.append(f"invidious {host}: no audio formats")
                continue
            fmts.sort(key=lambda f: f.get("bitrate") or 0, reverse=True)
            got = download_file(fmts[0]["url"], AUDIO)
            if got > 1_000_000 and 1200 < ffprobe_duration(AUDIO) < 2200:
                return f"invidious {host} (itag {fmts[0].get('itag')})"
            errors.append(f"invidious {host}: bad file ({got} bytes)")
        except Exception as e:  # noqa: BLE001
            errors.append(f"invidious {host}: {type(e).__name__}: {str(e)[:120]}")
    return None


def try_cobalt(errors: list[str]) -> str | None:
    instances = ["https://cobalt-api.kwiatekmiki.com/api/json",
                 "https://cobalt-api.meowbalt.workers.dev/api/json",
                 "https://api.cobalt.tools/api/json"]
    for api in instances:
        try:
            resp = http_post_json(api, {"url": WATCH_URL, "downloadMode": "audio",
                                        "audioFormat": "mp3"})
            url = resp.get("url")
            if resp.get("status") in ("stream", "redirect") and url:
                got = download_file(url, AUDIO)
                if got > 1_000_000 and 1200 < ffprobe_duration(AUDIO) < 2200:
                    return f"cobalt {api} ({resp.get('filename', '')[:40]})"
                errors.append(f"cobalt {api}: bad file ({got} bytes)")
            else:
                errors.append(f"cobalt {api}: {str(resp)[:150]}")
        except Exception as e:  # noqa: BLE001
            errors.append(f"cobalt {api}: {type(e).__name__}: {str(e)[:120]}")
    return None


def ar_norm(s: str) -> str:
    s = "".join(c for c in unicodedata.normalize("NFD", s)
                if unicodedata.category(c) != "Mn")
    s = (s.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ٱ", "ا")
          .replace("ة", "ه").replace("ى", "ي").replace("ؤ", "و").replace("ئ", "ي"))
    s = re.sub(r"[^\u0600-\u06FF\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def transcribe_and_match(report: dict) -> None:
    from faster_whisper import WhisperModel
    log("loading faster-whisper small (Arabic)...")
    model = WhisperModel("small", device="cpu", compute_type="int8")
    segments, _info = model.transcribe(
        str(AUDIO), language="ar", task="transcribe", beam_size=1,
        word_timestamps=True, vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 400})
    words: list[dict] = []
    for seg in segments:
        for w in (seg.words or []):
            words.append({"t0": round(w.start, 2), "t1": round(w.end, 2), "w": w.word})
    TRANSCRIPT.write_text(json.dumps(words, ensure_ascii=False), encoding="utf-8")
    log(f"transcribed {len(words)} words")

    norm_words = [ar_norm(w["w"]) for w in words]
    # char-offset index -> word index
    joined, owner = [], []
    for i, nw in enumerate(norm_words):
        for ch in nw:
            joined.append(ch)
            owner.append(i)
        joined.append(" ")
        owner.append(i)
    text = "".join(joined)

    found = {}
    for ayah, phrase in CANDIDATES.items():
        idx = text.find(phrase)
        if idx < 0:
            continue
        wi = owner[idx]
        wj = owner[min(idx + len(phrase), len(owner) - 1)]
        # expand to breath pauses around the hit (<= 30 s span)
        t0 = words[max(0, wi - 30)]["t0"]
        t1 = words[min(len(words) - 1, wj + 30)]["t1"]
        # tighten: walk out to gaps >= 0.5 s, max 12 s each side
        lo, hi = wi, wj
        while lo > 0 and words[lo]["t0"] - words[lo - 1]["t1"] < 0.5 \
                and words[wi]["t0"] - words[lo]["t0"] < 12:
            lo -= 1
        while hi < len(words) - 1 and words[hi + 1]["t0"] - words[hi]["t1"] < 0.5 \
                and words[hi]["t1"] - words[wj]["t1"] < 12:
            hi += 1
        span = words[hi]["t1"] - words[lo]["t0"]
        found[ayah] = {
            "hit_t": [words[wi]["t0"], words[wj]["t1"]],
            "window": [round(words[lo]["t0"] - 0.4, 2), round(words[hi]["t1"] + 0.4, 2)],
            "window_dur": round(span + 0.8, 2),
            "context": " ".join(w["w"] for w in words[max(0, lo - 3):hi + 4])[:160],
        }
    report["transcript_words"] = len(words)
    report["candidates"] = found
    log(f"matched {len(found)}/{len(CANDIDATES)} candidate phrases")


def audio_fingerprint(report: dict) -> None:
    p = run(["ffmpeg", "-hide_banner", "-i", str(AUDIO),
             "-af", "loudnorm=print_format=summary", "-f", "null", "-"])
    loud = {}
    for line in p.stderr.splitlines():
        m = re.match(r"Input (Integrated|True Peak|LRA)\s*:\s*(.+)", line.strip())
        if m:
            loud[m.group(1)] = m.group(2).strip()
    report["loudness"] = loud
    pcm = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(AUDIO),
         "-ac", "2", "-ar", "8000", "-f", "f32le", "pipe:1"],
        capture_output=True, timeout=900).stdout
    stereo = np.frombuffer(pcm, dtype=np.float32).reshape(-1, 2)
    c = np.corrcoef(stereo[::10, 0], stereo[::10, 1])[0, 1]
    report["stereo_corr"] = round(float(c), 4)
    mono = stereo.mean(axis=1)
    hop = 4000
    frames = [mono[i:i + hop] for i in range(0, len(mono) - hop, hop)]
    rms = np.array([float(np.sqrt(np.mean(f ** 2) + 1e-12)) for f in frames])
    sr = 8000
    freqs = np.fft.rfftfreq(hop, 1 / sr)
    bands = [(20, 120), (120, 500), (500, 2000), (2000, 4000)]
    beds = []
    for idx in np.argsort(rms)[:60]:
        t = idx * 0.5
        if t < 5 or t > len(mono) / sr - 5 or len(beds) >= 10:
            continue
        spec = np.abs(np.fft.rfft(frames[idx].astype(np.float64) * np.hanning(hop))) ** 2 + 1e-18
        flat = float(np.exp(np.mean(np.log(spec))) / np.mean(spec))
        e = [float(spec[(freqs >= lo) & (freqs < hi)].sum()) for lo, hi in bands]
        tot = sum(e) + 1e-18
        beds.append({"t": round(t, 1),
                     "rms_db": round(float(20 * np.log10(rms[idx] + 1e-9)), 1),
                     "flatness": round(flat, 4),
                     "bands": [round(x / tot, 3) for x in e]})
    report["pause_bed"] = beds
    med_db = float(np.median([b["rms_db"] for b in beds])) if beds else -99
    med_flat = float(np.median([b["flatness"] for b in beds])) if beds else 0
    report["bed_verdict"] = (
        "digital-silence pauses (clean recitation, no rain/music bed)" if med_db < -70
        else "noise-like bed in pauses (rain/hiss ambience likely)" if med_flat > 0.45
        else "tonal/low bed in pauses (music/echo tail possible — inspect)")


def sheet_clip010(report: dict, errors: list[str]) -> None:
    clip = WORK / "clip010_full.mp4"
    try:
        with clip.open("wb") as out:
            subprocess.run(["git", "show", CLIP010_BLOB_PATH], stdout=out,
                           stderr=subprocess.DEVNULL, check=True, timeout=300)
        if clip.stat().st_size < 50_000_000:
            raise RuntimeError(f"clip010 too small: {clip.stat().st_size}")
        p = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "json", str(clip)])
        fdur = float(json.loads(p.stdout)["format"]["duration"])
        step = fdur / 16.0
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(clip),
             "-vf", f"select='isnan(prev_selected_t)+gte(t-prev_selected_t\\,{step:.2f})',"
                    "scale=180:320,tile=4x4:margin=4:color=black",
             "-frames:v", "1", str(SHEET010)], timeout=600)
        stills = []
        for i in range(8):
            out = WORK / f"still010_{i}.png"
            run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                 "-ss", f"{(i + 0.5) * fdur / 8:.1f}", "-i", str(clip),
                 "-frames:v", "1", "-vf", "scale=360:-1", str(out)])
            if out.exists():
                stills.append(out.name)
        report["clip010"] = {"duration_s": round(fdur, 2),
                             "bytes": clip.stat().st_size,
                             "sheet": SHEET010.name, "stills": stills}
        log(f"clip010 sheet done ({fdur:.0f}s)")
    except Exception as e:  # noqa: BLE001
        errors.append(f"clip010: {type(e).__name__}: {str(e)[:150]}")
    finally:
        if clip.exists():
            clip.unlink()


def main() -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    report: dict = {"video_id": VIDEO_ID, "status": "failed"}

    used = try_piped(errors) or try_invidious(errors) or try_cobalt(errors)
    if not used:
        report["errors"] = errors[-20:]
        REPORT.write_text(json.dumps(report, indent=1), encoding="utf-8")
        log("all audio fetch methods failed")
        return
    report["audio_via"] = used
    report["audio_bytes"] = AUDIO.stat().st_size
    report["audio_dur"] = round(ffprobe_duration(AUDIO), 1)
    log(f"audio OK: {used}, {report['audio_dur']}s")

    try:
        transcribe_and_match(report)
    except Exception as e:  # noqa: BLE001
        errors.append(f"transcribe: {type(e).__name__}: {str(e)[:200]}")
    try:
        audio_fingerprint(report)
    except Exception as e:  # noqa: BLE001
        errors.append(f"fingerprint: {type(e).__name__}: {str(e)[:150]}")
    sheet_clip010(report, errors)

    report["errors"] = errors[-14:]
    report["status"] = "ok" if report.get("candidates") else "partial"
    REPORT.write_text(json.dumps(report, indent=1), encoding="utf-8")
    log(f"media done status={report['status']}")


if __name__ == "__main__":
    main()
