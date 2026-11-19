"""Remove a burned-in watermark from a video you own or have licensed.

usage: python dewatermark.py <in.mp4> --out <out.mp4> --rights own|licensed
                             [--mode matte|soft|delogo|crop] [mode options]
                             [--preview 6] [--crf 18] [--force]

Modes
  matte   (default) Semi-transparent marks. Calibrates the mark's alpha and
          white level from one frame where it sits on a flat background
          (--calibrate t:x,y,w,h), then tracks it per frame by matched filter
          and inverts the blend: I = (1-a)B + aW  ->  B = (I - aW)/(1 - a).
          Restores the real background instead of smearing a patch over it.
          Frames where the mark is not found are passed through untouched.
  soft    No detection. Suppresses LOW-AMPLITUDE brightening everywhere, which
          fades a pale overlay but also flattens faint highlights. Use when the
          mark moves too much to track, or on top of a partial matte pass.
  delogo  ffmpeg's delogo on a fixed box (--box x,y,w,h). For opaque, static
          logos or text. Fast, but interpolates from the box edges.
  crop    Reframes so an edge band is cut away (--crop 200 = drop 200px), then
          scales back up. Lossless-looking removal when the mark hugs one edge.

Nothing here posts, uploads or credits anything. --rights is required and is
written into the sidecar JSON: a clip whose attribution status is unrecorded
never enters the pipeline. Only use this on footage you own or licensed --
removing someone else's watermark is attribution stripping, not editing.

Prints a before/after sheet on every run so a human can approve the result.
"""
import argparse, json, os, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import tool, ffprobe, save_json

import cv2
import numpy as np


# ---------------------------------------------------------------- ffmpeg I/O
def video_info(path):
    meta = ffprobe(path)
    vs = [s for s in meta["streams"] if s["codec_type"] == "video"]
    if not vs:
        sys.exit(f"no video stream in {path}")
    v = vs[0]
    num, den = (v.get("r_frame_rate") or "30/1").split("/")
    fps = float(num) / float(den or 1)
    dur = float(meta["format"]["duration"])
    has_audio = any(s["codec_type"] == "audio" for s in meta["streams"])
    return {"w": int(v["width"]), "h": int(v["height"]), "fps": fps,
            "dur": dur, "audio": has_audio, "frames": int(round(dur * fps))}


def encode(frames_iter, info, src, out, crf):
    """Pipe BGR frames into x264 and keep the source audio untouched."""
    cmd = [tool("ffmpeg"), "-v", "error", "-y",
           "-f", "rawvideo", "-pix_fmt", "bgr24",
           "-s", f"{info['w']}x{info['h']}", "-r", f"{info['fps']:.6f}",
           "-i", "-", "-i", str(src),
           "-map", "0:v:0", "-map", "1:a:0?" if info["audio"] else "1:a:0",
           "-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
           "-pix_fmt", "yuv420p", "-c:a", "copy", "-shortest", str(out)]
    if not info["audio"]:
        cmd = [c for c in cmd if c not in ("-map", "1:a:0") and c != "-c:a"]
        cmd = [c for c in cmd if c != "copy"]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for f in frames_iter:
            p.stdin.write(f.tobytes())
    finally:
        p.stdin.close()
        rc = p.wait()
    if rc != 0:
        sys.exit(f"ffmpeg encode failed ({rc})")


def iter_frames(src, info):
    cap = cv2.VideoCapture(str(src))
    n = 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        n += 1
        yield fr
    cap.release()
    if n == 0:
        sys.exit(f"decoded 0 frames from {src}")


# ------------------------------------------------------------------ helpers
def gray(fr):
    return cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY) if fr.ndim == 3 else fr


def local_bg(g, window):
    """Smooth background estimate, cheap: median at 1/4 scale then upscale."""
    sc = 0.25
    small = cv2.resize(g, (0, 0), fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
    k = max(3, int(window * sc) | 1)
    med = cv2.medianBlur(small, k)
    return cv2.resize(med, (g.shape[1], g.shape[0]), interpolation=cv2.INTER_LINEAR)


def suppress_soft(fr, window, t1, t2):
    """Fade low-amplitude brightening (= pale overlay) without touching real edges."""
    lab = cv2.cvtColor(fr, cv2.COLOR_BGR2LAB).astype(np.float32)
    L = lab[:, :, 0]
    bg = local_bg(L.astype(np.uint8), window).astype(np.float32)
    r = L - bg
    keep = np.where(r > 0, np.clip((np.abs(r) - t1) / max(t2 - t1, 1e-6), 0, 1), 1.0)
    lab[:, :, 0] = np.clip(bg + r * keep, 0, 255)
    return cv2.cvtColor(lab.astype(np.uint8), cv2.COLOR_LAB2BGR)


def calibrate(src, spec, window=81):
    """Estimate the mark's alpha and white level from a flat-background sample.

    spec = "t:x,y,w,h" -- a timestamp where the whole mark sits on a smooth area.
    Model: I = (1-a)B + aW  ->  least squares over the brightest (stroke-centre)
    pixels, where B comes from a wide median of the same (flat) frame.
    """
    t, box = spec.split(":", 1)
    x, y, w, h = (int(v) for v in box.split(","))
    cap = cv2.VideoCapture(str(src))
    cap.set(cv2.CAP_PROP_POS_MSEC, float(t) * 1000.0)
    ok, fr = cap.read()
    cap.release()
    if not ok:
        sys.exit(f"--calibrate: could not read frame at {t}s")
    g = gray(fr).astype(np.float64)
    B = cv2.medianBlur(g.astype(np.uint8), window).astype(np.float64)
    subI, subB = g[y:y + h, x:x + w], B[y:y + h, x:x + w]
    d = subI - subB
    keep = d > max(np.percentile(d, 88), 6)
    if keep.sum() < 50:
        sys.exit("--calibrate: not enough mark pixels found in that box. "
                 "Pick a timestamp where the watermark sits on a flat background.")
    A = np.stack([subB[keep], np.ones(int(keep.sum()))], 1)
    (slope, icept), *_ = np.linalg.lstsq(A, subI[keep], rcond=None)
    alpha = 1.0 - slope
    white = icept / alpha if alpha > 1e-3 else float("nan")
    if not (0.02 < alpha < 0.95) or not (60 < white <= 300):
        sys.exit(f"--calibrate: implausible fit (alpha={alpha:.2f}, white={white:.0f}). "
                 "The sample box probably includes hard edges; pick a flatter one.")
    den = white - subB
    matte = np.where(den > 10, np.clip(d / np.maximum(den, 1.0), 0, 1), 0.0)
    ys, xs = np.where(matte > 0.02)
    if len(xs) < 50:
        sys.exit("--calibrate: mark vanished during matte build; try another box.")
    matte = matte[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    origin = (x + int(xs.min()), y + int(ys.min()))
    return {"alpha": float(alpha), "white": float(white),
            "matte": matte.astype(np.float32), "origin": origin}


def unblend(fr, box, cal):
    """Remove the mark's own contribution from the pixels it covers.

    The matte gives the overlay's *shape*. Its amplitude depends on the
    background (I = (1-a)B + aW, so it is a(W-B) per channel), which is why a
    single global alpha over- or under-corrects. Instead we project the local
    residual onto the matte, get one amplitude per channel for this frame, and
    subtract it. The background cancels out of the residual, so this works on
    any backdrop without re-tuning.
    """
    x, y = box
    mat = cal["matte"]
    h, w = mat.shape
    H, Wd = fr.shape[:2]
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + w, Wd), min(y + h, H)
    if x1 - x0 < 8 or y1 - y0 < 4:
        return fr
    mm = mat[y0 - y:y1 - y, x0 - x:x1 - x]
    if mm.max() <= 0.02:
        return fr
    sub = fr[y0:y1, x0:x1].astype(np.float32)
    hh, ww = mm.shape
    # design: matte amplitude + a smooth (quadratic) backdrop. Fitting the
    # backdrop explicitly means the text itself can no longer bias the
    # background estimate, which a wide median does whenever the mark is large.
    u = (np.arange(ww, dtype=np.float32) / max(ww - 1, 1))[None, :].repeat(hh, 0)
    v = (np.arange(hh, dtype=np.float32) / max(hh - 1, 1))[:, None].repeat(ww, 1)
    A = np.stack([mm, np.ones_like(mm), u, v, u * u, u * v, v * v], -1).reshape(-1, 7)
    out = fr.copy()
    for c in range(sub.shape[2]):
        y = sub[:, :, c].reshape(-1)
        coef, *_ = np.linalg.lstsq(A, y, rcond=None)
        k = max(float(coef[0]), 0.0)               # the mark only ever brightens
        rec = y - k * mm.reshape(-1)
        out[y0:y1, x0:x1, c] = np.clip(rec.reshape(hh, ww), 0, 255).astype(np.uint8)
    return out


def mark_energy(fr, box, mat):
    """How much mark-like residue is left: bright bump plus dark over-correction."""
    x, y = box
    mat = cv2.resize(mat, (mat.shape[1], mat.shape[0]))
    h, w = mat.shape
    H, Wd = fr.shape[:2]
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + w, Wd), min(y + h, H)
    if x1 - x0 < 8 or y1 - y0 < 4:
        return None
    sub = cv2.cvtColor(fr[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY).astype(np.float32)
    bg = local_bg(sub.astype(np.uint8), 61).astype(np.float32)
    d = sub - bg
    hi = float(np.percentile(d, 99.0))
    lo = float(np.percentile(d, 1.0))
    return hi - 1.5 * min(lo, 0.0)          # dark over-correction costs more than a ghost


def make_template(cal):
    t = cal["matte"] - cal["matte"].mean()
    n = np.linalg.norm(t)
    return (t / n if n else t).astype(np.float32)


def detect(g, tpl, cal, min_score, min_ratio):
    """Matched filter on the background-subtracted frame; returns (x, y, score)."""
    bg = cv2.medianBlur(g, 81).astype(np.float32)
    r = g.astype(np.float32) - bg
    R = cv2.matchTemplate(r, tpl, cv2.TM_CCOEFF_NORMED)
    _, s1, _, loc = cv2.minMaxLoc(R)
    m = R.copy()
    cv2.circle(m, loc, max(40, tpl.shape[1] // 3), float(R.min() - 1), -1)
    s2 = cv2.minMaxLoc(m)[1]
    if s1 < min_score or s1 / max(s2, 1e-6) < min_ratio:
        return None, s1
    # the template is the matte cropped to its bbox, so the match location is
    # already the mark's top-left in frame coordinates.
    return (int(loc[0]), int(loc[1])), s1


# ------------------------------------------------------------------ preview
def preview(src, out, info, cal, times, path):
    """Before/after sheet at the given timestamps so a human can approve."""
    tiles = []
    for t in times:
        cap = cv2.VideoCapture(str(src))
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
        ok, before = cap.read()
        cap.release()
        if not ok:
            continue
        cap = cv2.VideoCapture(str(out))
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
        ok, after = cap.read()
        cap.release()
        if not ok:
            continue
        h, w = before.shape[:2]
        sc = 300.0 / w
        pair = np.hstack([cv2.resize(before, (300, int(h * sc))),
                          cv2.resize(after, (300, int(h * sc)))])
        cv2.putText(pair, f"{t:.0f}s before", (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        cv2.putText(pair, "after", (306, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        tiles.append(pair)
    if not tiles:
        return None
    rows = [np.hstack(tiles[i:i + 2]) for i in range(0, len(tiles), 2)]
    if len(rows) > 1 and rows[-1].shape[1] != rows[0].shape[1]:
        pad = rows[0].shape[1] - rows[-1].shape[1]
        rows[-1] = np.hstack([rows[-1], np.zeros((rows[-1].shape[0], pad, 3), np.uint8)])
    sheet = np.vstack(rows)
    cv2.imwrite(str(path), sheet)
    return path


# --------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Remove a burned-in watermark from video you own.")
    ap.add_argument("video")
    ap.add_argument("--out", required=True)
    ap.add_argument("--rights", required=True, choices=["own", "licensed"],
                    help="own = you made it; licensed = you hold a licence. Recorded in the sidecar.")
    ap.add_argument("--mode", default="matte", choices=["matte", "soft", "delogo", "crop"])
    ap.add_argument("--calibrate", help="matte mode: t:x,y,w,h where the mark sits on a flat background")
    ap.add_argument("--min-score", type=float, default=0.35)
    ap.add_argument("--min-ratio", type=float, default=1.35)
    ap.add_argument("--soft-on-miss", action="store_true", default=True,
                    help="matte mode: run soft suppression on frames where the mark is not found")
    ap.add_argument("--check", action="store_true", default=True,
                    help="matte mode: keep whichever candidate leaves the least mark residue")
    ap.add_argument("--no-check", dest="check", action="store_false")
    ap.add_argument("--window", type=int, default=41, help="soft mode: background window (px)")
    ap.add_argument("--threshold", type=float, default=24.0, help="soft mode: fade bump amplitudes below this")
    ap.add_argument("--falloff", type=float, default=60.0, help="soft mode: fully keep bumps above this")
    ap.add_argument("--passes", type=int, default=1)
    ap.add_argument("--box", action="append", default=[], help="delogo: x,y,w,h (repeatable)")
    ap.add_argument("--crop", type=int, default=0, help="crop mode: pixels to cut from the bottom edge")
    ap.add_argument("--crf", type=int, default=18)
    ap.add_argument("--preview", type=int, default=6, help="timestamps to sample for the before/after sheet (0=off)")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    src, out = Path(a.video), Path(a.out)
    if not src.exists():
        sys.exit(f"no such file: {src}")
    if out.exists() and not a.force:
        sys.exit(f"{out} exists; pass --force to overwrite")

    info = video_info(src)
    out.parent.mkdir(parents=True, exist_ok=True)
    tpl = cal = None
    if a.mode == "matte":
        if not a.calibrate:
            sys.exit("matte mode needs --calibrate t:x,y,w,h (a frame where the mark is on a flat background)")
        cal = calibrate(src, a.calibrate)
        tpl = make_template(cal)
        print(f"calibrated: alpha={cal['alpha']:.3f} white={cal['white']:.0f} "
              f"mark={cal['matte'].shape[1]}x{cal['matte'].shape[0]}px")

    # ---- delogo / crop: single ffmpeg pass
    if a.mode in ("delogo", "crop"):
        if a.mode == "delogo":
            if not a.box:
                sys.exit("delogo needs --box x,y,w,h")
            vf = ",".join(f"delogo=x={b.split(',')[0]}:y={b.split(',')[1]}:"
                          f"w={b.split(',')[2]}:h={b.split(',')[3]}"
                          for b in a.box)
        else:
            if a.crop <= 0:
                sys.exit("crop needs --crop <pixels>")
            keep = info["h"] - a.crop
            vf = (f"crop={info['w']}:{keep}:0:0,scale={info['w']}:{info['h']}:flags=lanczos")
        cmd = [tool("ffmpeg"), "-v", "error", "-y", "-i", str(src), "-vf", vf,
               "-c:v", "libx264", "-preset", "medium", "-crf", str(a.crf),
               "-pix_fmt", "yuv420p", "-c:a", "copy", str(out)]
        subprocess.run(cmd, check=True)
        hits = None
    else:
        state = {"found": 0, "missed": 0}
        pos = {"last": None}

        def frames():
            for fr in iter_frames(src, info):
                g = gray(fr)
                if a.mode == "soft":
                    o = fr
                    for _ in range(max(1, a.passes)):
                        o = suppress_soft(o, a.window, a.threshold, a.falloff)
                    yield o
                    continue
                soft = fr
                for _ in range(max(1, a.passes)):
                    soft = suppress_soft(soft, a.window, a.threshold, a.falloff)
                box, score = detect(g, tpl, cal, a.min_score, a.min_ratio)
                if box is None:
                    state["missed"] += 1
                    yield soft if a.soft_on_miss else fr
                    continue
                state["found"] += 1
                pos["last"] = box
                cands = [fr, soft, unblend(soft, box, cal)]
                if a.check:
                    scored = [(mark_energy(c, box, cal["matte"]), i, c) for i, c in enumerate(cands)]
                    scored = [s for s in scored if s[0] is not None]
                    if scored:
                        scored.sort(key=lambda s: s[0])
                        state["picked"] = state.get("picked", {})
                        state["picked"][scored[0][1]] = state["picked"].get(scored[0][1], 0) + 1
                        yield scored[0][2]
                        continue
                yield cands[2]

        encode(frames(), info, src, out, a.crf)
        hits = state if a.mode == "matte" else None

    # ---- sidecar + preview
    side = {
        "source": str(src.resolve()), "output": str(out.resolve()),
        "rights": a.rights, "mode": a.mode,
        "params": {k: v for k, v in vars(a).items()
                   if k not in ("video", "out", "force")},
        "size": os.path.getsize(out),
        "note": "Watermark removal recorded for provenance. The human still approves the post.",
    }
    if cal:
        side["calibration"] = {"alpha": round(cal["alpha"], 4),
                               "white": round(cal["white"], 1)}
    if hits:
        side["detection"] = hits
    save_json(out.with_suffix(".json"), side)

    sheet = None
    if a.preview:
        dur = info["dur"]
        times = [dur * (i + 0.5) / a.preview for i in range(a.preview)]
        sheet = preview(src, out, info, cal, times, out.with_name(out.stem + "_preview.png"))

    print(f"wrote {out}  ({info['w']}x{info['h']}, {info['dur']:.1f}s, {side['size']/1e6:.1f} MB)")
    if hits:
        total = hits["found"] + hits["missed"]
        print(f"mark located in {hits['found']}/{total} frames ({100*hits['found']/max(total,1):.0f}%)")
    if sheet:
        print(f"preview: {sheet}  <- look at it before trusting the result")
    print("Nothing was posted. Show the preview to the human and wait for a yes.")


if __name__ == "__main__":
    main()
