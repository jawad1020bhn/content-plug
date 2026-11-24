#!/usr/bin/env python3
"""Scan Pinterest clip 010 for cuts (runs in GitHub Actions; results committed).

Clip 010 is a 248 s travel MONTAGE, not one scene. This finds every hard cut
(1 fps frame-diffs, full array committed) and extracts 12 evenly-spaced stills
so a clean >=20 s segment can be chosen for the slot 005 popup window.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np

BLOB = ("422b92c177ef5bd40a0761db318d1a7626a553f9:assets/al-baqarah-2-152-153/"
        "pinterest_candidates/010_e1_AfqPShw8bwXQoW1ZpriWAQUldapMdZi7nE5QXT1Gb78O0tRAksu7kw.mp4")
WORK = Path("scan010")
CLIP = WORK / "clip010_full.mp4"


def log(msg: str) -> None:
    print(f"[scan010] {msg}", flush=True)


def main() -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    with CLIP.open("wb") as out:
        subprocess.run(["git", "show", BLOB], stdout=out, check=True, timeout=300)
    log(f"clip010 {CLIP.stat().st_size / 1e6:.1f} MB")
    probe = json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration:stream=codec_name,width,height,r_frame_rate",
         "-of", "json", str(CLIP)],
        capture_output=True, text=True, check=True, timeout=120).stdout)
    dur = float(probe["format"]["duration"])

    raw = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(CLIP),
         "-vf", "fps=1,scale=160:90,format=gray", "-f", "rawvideo", "pipe:1"],
        capture_output=True, timeout=900).stdout
    fr = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 90, 160).astype(np.float32)
    diffs = [round(float(np.mean(np.abs(fr[i] - fr[i - 1]))), 1) for i in range(1, len(fr))]
    cuts55 = [i for i, d in enumerate(diffs, 1) if d > 55.0]
    cuts40 = [i for i, d in enumerate(diffs, 1) if d > 40.0]

    # segments between >55 cuts
    bounds = [0] + cuts55 + [len(diffs)]
    segs = sorted(
        [{"start": bounds[i], "end": bounds[i + 1], "len": bounds[i + 1] - bounds[i]}
         for i in range(len(bounds) - 1)],
        key=lambda s: s["len"], reverse=True)

    stills = []
    for i in range(12):
        out = WORK / f"still010b_{i:02d}.png"
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             "-ss", f"{(i + 0.5) * dur / 12:.1f}", "-i", str(CLIP),
             "-frames:v", "1", "-vf", "scale=360:-1", str(out)],
            check=True, timeout=120)
        stills.append(out.name)

    report = {"duration_s": round(dur, 2), "probe": probe,
              "diffs_1fps": diffs,
              "cuts_gt55_s": cuts55, "cuts_gt40_s": cuts40,
              "segments_top": segs[:8], "stills": stills}
    (WORK / "report010.json").write_text(json.dumps(report), encoding="utf-8")
    CLIP.unlink(missing_ok=True)  # never commit the 104 MB source
    log(f"done: {len(diffs)} diffs, {len(cuts55)} cuts>55, top seg {segs[0]['len']}s")


if __name__ == "__main__":
    main()
