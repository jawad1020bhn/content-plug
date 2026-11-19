#!/usr/bin/env python3
"""Remove captions from a clip — soft (track) or burned-in (pixels).

This is the *front door* for caption removal. It does the part that is reliable
and cheap on its own, and hands the burned-in part to an external neural
inpainter (VSR) instead of pretending OpenCV can do it.

  soft subtitles  -> ffmpeg stream copy, no quality loss, done here, instantly
  burned-in text  -> detect the caption bands here, then run VSR on them

Why hand off: measured on real footage, cv2.inpaint (TELEA/NS) and every
feathered/multi-scale variant leave a visible grey band under burned-in text.
There is no pixel data behind opaque text to recover. Only a learned inpainter
produces a usable fill. See clip-desk/skills/dewatermark/SKILL.md.

VSR = https://github.com/YaoFANGUK/video-subtitle-remover (Apache-2.0).
It is NOT vendored here and NOT installed by setup.sh: it is a ~1.7 GB checkout
plus torch, and it must run wherever you have the CPU/GPU budget. Point at it
with --vsr-home / --vsr-python (or VSR_HOME / VSR_PYTHON).

Usage:
  remove_captions.py clip.mp4 --detect            # where are the captions?
  remove_captions.py clip.mp4 --strip-soft        # remove subtitle tracks
  remove_captions.py clip.mp4 --rights own        # detect bands + run VSR
  remove_captions.py clip.mp4 --rights own --inpaint-mode lama --out out.mp4
"""

import argparse
import json
import os
import shutil
import subprocess
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import save_json, tool  # noqa: E402

def probe(src):
    """ffprobe with stream indices — common.ffprobe drops them."""
    r = subprocess.run([tool("ffprobe"), "-v", "error", "-show_entries",
                        "format=duration:stream=index,codec_type,codec_name,"
                        "width,height", "-of", "json", src],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"ffprobe failed: {r.stderr[-300:]}")
    return json.loads(r.stdout)


# --------------------------------------------------------------------------
# caption detection (burned-in)
# --------------------------------------------------------------------------

# Tuned on 720x1280 vertical footage. Letters are small, high value and low
# saturation; the outline/shadow behind them is dark, which is what separates
# real caption text from white clouds and bright walls.
WHITE_V, WHITE_S = 185, 80
H_MIN, H_MAX = 5, 48
W_MIN, W_MAX = 3, 70
AREA_MIN = 25
RING_MEAN_MAX = 112
LINE_MAX_DY = 12
LINE_MAX_GAP = 45
LINE_MIN_LETTERS = 3
LINE_MIN_WIDTH = 60


def white_mask(fr):
    hsv = cv2.cvtColor(fr, cv2.COLOR_BGR2HSV)
    v, s = hsv[:, :, 2], hsv[:, :, 1]
    return ((v >= WHITE_V) & (s <= WHITE_S)).astype(np.uint8) * 255


def letters(fr, g):
    """Candidate glyphs: small white blobs sitting on a dark ring."""
    m = white_mask(fr)
    n, _, stats, cent = cv2.connectedComponentsWithStats(m, connectivity=8)
    ring_k = np.ones((5, 5), np.uint8)
    out = []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if not (H_MIN <= h <= H_MAX and W_MIN <= w <= W_MAX and area >= AREA_MIN):
            continue
        box = np.zeros(g.shape, np.uint8)
        box[y:y + h, x:x + w] = 255
        ring = cv2.dilate(box, ring_k) & (255 - box)
        if not ring.any():
            continue
        if float(g[ring > 0].mean()) <= RING_MEAN_MAX:
            out.append((int(x), int(y), int(w), int(h)))
    return out


def group_lines(glyphs):
    """Group glyphs into caption lines."""
    glyphs = sorted(glyphs, key=lambda b: (b[1], b[0]))
    lines = []
    for x, y, w, h in glyphs:
        cy = y + h / 2
        for ln in lines:
            if abs(ln["cy"] - cy) <= LINE_MAX_DY and x - ln["x1"] <= LINE_MAX_GAP:
                ln["x0"], ln["x1"] = min(ln["x0"], x), max(ln["x1"], x + w)
                ln["y0"], ln["y1"] = min(ln["y0"], y), max(ln["y1"], y + h)
                ln["n"] += 1
                ln["cy"] = (ln["y0"] + ln["y1"]) / 2
                break
        else:
            lines.append({"x0": x, "x1": x + w, "y0": y, "y1": y + h,
                          "n": 1, "cy": cy})
    keep = []
    for ln in lines:
        w = ln["x1"] - ln["x0"]
        if ln["n"] >= LINE_MIN_LETTERS and w >= LINE_MIN_WIDTH:
            keep.append((ln["x0"], ln["y0"], w, ln["y1"] - ln["y0"]))
    return keep


def detect_frame(fr):
    g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
    return group_lines(letters(fr, g))


def sample_times(info, step):
    dur = float(info.get("format", {}).get("duration", 0) or 0)
    t, out = 0.5, []
    while t < dur:
        out.append(round(t, 2))
        t += step
    return out


def grab(src, t):
    ff = tool("ffmpeg")
    cmd = [ff, "-v", "error", "-ss", str(t), "-i", src, "-frames:v", "1",
           "-f", "image2pipe", "-vcodec", "png", "-"]
    p = subprocess.run(cmd, capture_output=True)
    if p.returncode != 0 or not p.stdout:
        return None
    return cv2.imdecode(np.frombuffer(p.stdout, np.uint8), cv2.IMREAD_COLOR)


def lines_at(src, times):
    """[(t, [(x,y,w,h), ...]), ...] for the sampled times."""
    out = []
    for t in times:
        fr = grab(src, t)
        if fr is None:
            continue
        out.append((t, detect_frame(fr)))
    return out


def bands(samples, frame_w, frame_h, min_hits=3):
    """Collapse per-frame lines into stable caption bands.

    A band must be seen on >=min_hits sampled frames: a one-off hit is a sign,
    a wall of text, or a reaction graphic, and handing it to an inpainter
    would erase content instead of captions. Bands are returned as VSR region
    tuples (ymin, ymax, xmin, xmax) with padding, because VSR's region filter
    keeps only boxes fully inside the region.
    """
    hits = {}
    for _, lines in samples:
        for x, y, w, h in lines:
            mid = y + h / 2
            for key in list(hits):
                if abs(key - mid) <= 40:
                    hits[key].append((x, y, w, h))
                    break
            else:
                hits[mid] = [(x, y, w, h)]
    out = []
    for _, boxes in hits.items():
        if len(boxes) < min_hits:
            continue
        x0 = min(b[0] for b in boxes)
        y0 = min(b[1] for b in boxes)
        x1 = max(b[0] + b[2] for b in boxes)
        y1 = max(b[1] + b[3] for b in boxes)
        pad = 6
        out.append({
            "ymin": max(0, y0 - pad), "ymax": min(frame_h - 1, y1 + pad),
            "xmin": max(0, x0 - pad), "xmax": min(frame_w - 1, x1 + pad),
            "hits": len(boxes),
        })
    # same caption line drifting a few px vertically lands in two groups
    out.sort(key=lambda b: b["ymin"])
    merged = []
    for b in out:
        if merged and b["ymin"] <= merged[-1]["ymax"]:
            m = merged[-1]
            m["ymax"] = max(m["ymax"], b["ymax"])
            m["xmin"] = min(m["xmin"], b["xmin"])
            m["xmax"] = max(m["xmax"], b["xmax"])
            m["hits"] += b["hits"]
        else:
            merged.append(dict(b))
    return merged


# --------------------------------------------------------------------------
# soft subtitle tracks
# --------------------------------------------------------------------------

def subtitle_streams(info):
    return [s for s in info.get("streams", []) if s.get("codec_type") == "subtitle"]


def strip_soft(src, out):
    ff = tool("ffmpeg")
    cmd = [ff, "-y", "-v", "error", "-i", src, "-map", "0", "-map", "-0:s",
           "-c", "copy", out]
    subprocess.run(cmd, check=True)
    return out


# --------------------------------------------------------------------------
# self-test: does the detector see captions and ignore lookalikes?
# --------------------------------------------------------------------------

def _synth(text=None, clouds=False):
    """720x1280 test frame: textured grey background, optional bold caption."""
    g = np.linspace(70, 150, 1280, dtype=np.uint8)[:, None]
    fr = np.repeat(np.repeat(g, 720, axis=1)[:, :, None], 3, axis=2).copy()
    noise = np.random.default_rng(7).integers(-12, 12, fr.shape[:2] + (1,))
    fr = np.clip(fr.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    if clouds:  # white blobs with no dark ring: must NOT count as text
        for cx, cy, ax, ay in ((200, 380, 90, 40), (420, 400, 120, 45), (560, 360, 70, 30)):
            cv2.ellipse(fr, (cx, cy), (ax, ay), 0, 0, 360, (245, 245, 245), -1)
    if text:
        cv2.putText(fr, text, (150, 410), cv2.FONT_HERSHEY_DUPLEX, 1.15,
                    (0, 0, 0), 6, cv2.LINE_AA)      # outline first
        cv2.putText(fr, text, (150, 410), cv2.FONT_HERSHEY_DUPLEX, 1.15,
                    (255, 255, 255), 3, cv2.LINE_AA)
    return fr


def selftest():
    ok = True

    def check(name, frame, want):
        nonlocal ok
        lines = detect_frame(frame)
        got = len(lines) >= 1
        mark = "PASS" if got == want else "FAIL"
        if got != want:
            ok = False
        detail = f"{len(lines)} line(s)"
        if lines:
            detail += " " + ",".join(f"{x},{y},{w},{h}" for x, y, w, h in lines[:3])
        print(f"  {mark}  {name}: expected {'text' if want else 'none'}, got {detail}")

    print("SELFTEST caption detector (720x1280 synthetic frames)")
    check("bold caption on grey", _synth("ALWAYS TALK"), True)
    check("empty background", _synth(), False)
    check("white clouds, no caption", _synth(clouds=True), False)
    print("PASS" if ok else "FAIL")
    return ok


# --------------------------------------------------------------------------
# external backend: VSR
# --------------------------------------------------------------------------

VSR_MODES = ["sttn-auto", "sttn-det", "lama", "propainter", "opencv"]
SHIM = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vsr_shim")


def vsr_env():
    """VSR's CLI needs three things on a plain Linux box that it does not ask for."""
    env = dict(os.environ)
    # paddle 3.x phones home to check model hosters before using local weights
    env["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
    # qfluentwidgets/Qt stand-in so the CLI starts without libGL
    env["PYTHONPATH"] = SHIM + (os.pathsep + env["PYTHONPATH"]
                                if env.get("PYTHONPATH") else "")
    env.setdefault("OMP_NUM_THREADS", str(min(4, os.cpu_count() or 2)))
    return env


def find_vsr(home, python):
    home = home or os.environ.get("VSR_HOME")
    python = python or os.environ.get("VSR_PYTHON")
    if not home:
        return None
    main = os.path.join(home, "backend", "main.py")
    if not os.path.isfile(main):
        return None
    if not python:
        for cand in (os.path.join(home, ".venv", "bin", "python"),
                     os.path.join(home, "venv", "bin", "python")):
            if os.path.isfile(cand):
                python = cand
                break
    if not python:
        python = shutil.which("python3")
    if not python or not os.path.isfile(main):
        return None
    return {"home": home, "main": main, "python": python}


def vsr_cmd(vsr, src, out, regions, mode):
    cmd = [vsr["python"], vsr["main"], "-i", src, "-o", out,
           "--inpaint-mode", mode]
    for b in regions:
        cmd += ["-c", str(b["ymin"]), str(b["ymax"]),
                str(b["xmin"]), str(b["xmax"])]
    return cmd


SETUP = """\
VSR is not set up, so the burned-in captions were NOT removed.

  git clone --depth 1 https://github.com/YaoFANGUK/video-subtitle-remover ~/vsr   # ~1.7 GB
  python3 -m venv ~/vsr/.venv
  ~/vsr/.venv/bin/pip install torch torchvision            # CPU box: --index-url https://download.pytorch.org/whl/cpu
  ~/vsr/.venv/bin/pip install opencv-python-headless numpy av einops tqdm \\
      scikit-image filesplit requests darkdetect pillow scipy matplotlib \\
      "paddlepaddle==3.0.0" paddleocr

Then re-run with --vsr-home ~/vsr (or export VSR_HOME=~/vsr).

Pin paddlepaddle 3.0.0: 3.3.x dies on CPU with
"ConvertPirAttribute2RuntimeAttribute not support". VSR's source also needs
Python 3.12+ (PEP 701 f-strings) or one line patched on 3.11.
On a CPU-only machine prefer --inpaint-mode lama; sttn-auto fills at 432x240
and upscales, which smears wide caption lines.
"""


# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Remove soft or burned-in captions.")
    ap.add_argument("src", nargs="?", default="")
    ap.add_argument("--out")
    ap.add_argument("--rights", choices=["own", "licensed"], default=None)
    ap.add_argument("--detect", action="store_true",
                    help="report caption bands and stop")
    ap.add_argument("--strip-soft", action="store_true",
                    help="remove embedded subtitle tracks (lossless)")
    ap.add_argument("--engine", choices=["vsr", "none"], default="vsr")
    ap.add_argument("--vsr-home", default=None)
    ap.add_argument("--vsr-python", default=None)
    ap.add_argument("--inpaint-mode", choices=VSR_MODES, default="lama")
    ap.add_argument("--selftest", action="store_true",
                    help="check the caption detector on synthetic frames")
    ap.add_argument("--sample-step", type=float, default=2.0)
    ap.add_argument("--min-band-hits", type=int, default=3,
                    help="samples a band must appear in (default 3)")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the VSR command and stop")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(0 if selftest() else 1)

    src = os.path.abspath(args.src)   # VSR runs with cwd=its own checkout
    if not os.path.isfile(src):
        sys.exit(f"no such file: {src}")
    info = probe(src)
    vid = next((s for s in info.get("streams", [])
                if s.get("codec_type") == "video"), {})
    w = int(vid.get("width") or 0)
    h = int(vid.get("height") or 0)
    dur = float(info.get("format", {}).get("duration", 0) or 0)
    print(f"{os.path.basename(src)}  {w}x{h}  {dur:.2f}s")

    subs = subtitle_streams(info)
    print(f"subtitle tracks: {len(subs)}"
          + ("" if not subs else "  " + ", ".join(
              f"#{s.get('index')}:{s.get('codec_name')}" for s in subs)))

    if args.strip_soft or (subs and args.engine == "none" and not args.detect):
        if not subs:
            print("no soft subtitle tracks to strip")
            return
        out = os.path.abspath(args.out or os.path.splitext(src)[0] + ".nosubs.mp4")
        if os.path.exists(out) and not args.force:
            sys.exit(f"{out} exists (use --force)")
        strip_soft(src, out)
        print(f"stripped {len(subs)} subtitle track(s) -> {out}")
        return

    times = sample_times(info, args.sample_step)
    samples = lines_at(src, times)
    found = [(t, ls) for t, ls in samples if ls]
    print(f"sampled {len(samples)} frames: {len(found)} with caption text")
    b = bands(samples, w, h, args.min_band_hits)
    for x in b:
        print(f"  band y {x['ymin']}-{x['ymax']}  x {x['xmin']}-{x['xmax']}"
              f"  ({x['hits']} hits / {len(samples)} frames)")
    if not b:
        print("no stable caption band found — nothing to hand to an inpainter")
        if not found:
            print("(no burned-in text detected at all)")
        return

    if args.detect:
        return

    if not args.rights:
        sys.exit("refusing to alter a clip without --rights own|licensed")
    if args.rights == "licensed":
        print("note: licensed material — removing its captions may breach the "
              "licence; your call, recorded in the sidecar")

    if args.engine == "none":
        print("engine=none: bands printed, nothing run")
        return

    vsr = find_vsr(args.vsr_home, args.vsr_python)
    if not vsr:
        print()
        print(SETUP)
        sys.exit(3)
    print(f"vsr: {vsr['home']}  python {vsr['python']}  mode {args.inpaint_mode}")

    out = os.path.abspath(args.out or
                          os.path.splitext(src)[0] + f".nocap.{args.inpaint_mode}.mp4")
    if os.path.exists(out) and not args.force:
        sys.exit(f"{out} exists (use --force)")
    cmd = vsr_cmd(vsr, src, out, b, args.inpaint_mode)
    print("run:", " ".join(cmd))
    if args.dry_run:
        print("(dry run)")
        return
    rc = subprocess.run(cmd, env=vsr_env(), cwd=vsr["home"]).returncode
    if rc != 0:
        sys.exit(f"vsr exited {rc}")

    side = os.path.splitext(out)[0] + ".json"
    save_json(side, {
        "source": src, "output": out, "task": "caption removal (burned-in)",
        "rights": args.rights, "engine": "vsr", "vsr_home": vsr["home"],
        "inpaint_mode": args.inpaint_mode, "regions": b,
        "sampled": len(samples), "frames_with_text": len(found),
        "min_band_hits": args.min_band_hits,
        "tracks_stripped": len(subs),
    })
    print(f"done -> {out}\nsidecar -> {side}")


if __name__ == "__main__":
    main()
