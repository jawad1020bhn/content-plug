#!/usr/bin/env python3
"""Build Reel 2 (launch-day news) for Leonida Keys — REAL footage edition.

Six segments over real official-trailer clips (sourced via fetch_reel2_footage.sh)
in the plugin's blur layout (16:9 centered over a blurred darkened copy),
cinematic slow-motion to fill each segment, crossfades, plugin-style burned
captions with launch-day verified numbers, narrator VO + synthwave bed.
Output: media/edits/reel2_launch_news.mp4 (1080x1920@30, -14 LUFS).
"""
import subprocess, sys
from pathlib import Path

PAGE = Path(__file__).resolve().parent.parent
RAW, ASSETS = PAGE / "media" / "raw", PAGE / "assets"
EDITS = PAGE / "media" / "edits"
JOBS = PAGE / "jobs" / "reel2"
JOBS.mkdir(parents=True, exist_ok=True)
FF = str(next(d for d in (Path(sys.executable).parent, Path(sys.prefix) / "bin")
            if (d / "ffmpeg").exists()) / "ffmpeg")
FFPR = str(Path(FF).parent / "ffprobe")
W, H, FPS, XF = 1080, 1920, 30, 0.4

FOOT = [RAW / "gasp_out2.mp4", RAW / "gasp_out1.mp4", RAW / "gasp_out3.mp4",
        RAW / "gasp_postcard.mp4", RAW / "gasp_out2.mp4"]      # out2 twice: seg0 + cropped seg4
CTA = ASSETS / "reel1" / "reel1_cta.jpg"
VOS = [ASSETS / "reel2" / f"vo_{i}.mp3" for i in range(1, 7)]
OUT = EDITS / "reel2_launch_news.mp4"


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"FAILED: {' '.join(map(str, cmd))[:220]}\n{r.stderr[-1800:]}")


def dur(p):
    r = subprocess.run([FFPR, "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    return float(r.stdout.strip())


def ts(t):
    t = max(0.0, t); h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


# ---- 1. synthwave pulse bed (same as Reel 1: 108 BPM brand sound) ---------------
BEAT = JOBS / "beat.wav"
B = 0.5556
env = f"pow(max(0,1-mod(t,{B})/{B}),2.2)"
hat = f"pow(max(0,1-mod(t+{B/2},{B})/0.09),3)"
expr = (f"(0.30*sin(2*PI*55*t)+0.18*sin(2*PI*110*t))*{env}"
        f"+0.085*(sin(2*PI*220*t)+sin(2*PI*261.63*t)+sin(2*PI*329.63*t))*(0.55+0.45*sin(2*PI*0.22*t))"
        f"+0.045*(2*random(0)-1)*{hat}")
e = expr.replace(",", "\\,")
run([FF, "-y", "-v", "error", "-f", "lavfi", "-t", "30",
     "-i", f"aevalsrc={e}|{e}:s=48000", "-c:a", "pcm_s16le", str(BEAT)])

# ---- 2. timeline ------------------------------------------------------------------
vd = [dur(p) for p in VOS]
seg = [d + 0.62 for d in vd]
starts, acc = [], 0.0
for k, d in enumerate(seg):
    starts.append(acc - XF * k if k else 0.0)
    acc += d
T = acc - XF * (len(seg) - 1)
print(f"VO durations: {[round(d,2) for d in vd]}  -> total {T:.2f}s")

# ---- 3. ASS captions (plugin styles + yellow number highlights) -------------------
HDR = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Arial Black,88,&H00FFFFFF,&H0000E5FF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,7,3,5,60,60,0,1
Style: Hook,Arial Black,68,&H00000000,&H00000000,&H00FFFFFF,&H00FFFFFF,-1,0,0,0,100,100,0,0,3,18,0,8,70,70,170,1
Style: CTA,Arial Black,84,&H00000000,&H00000000,&H00FFFFFF,&H00FFFFFF,-1,0,0,0,100,100,0,0,3,16,0,5,50,50,0,1
Style: Mark,Arial,40,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,0,-1,0,0,100,100,0,0,1,5,1,5,40,40,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
c, w = "{\\c&H0000E5FF&}", "{\\c&H00FFFFFF&}"
ev = [
    f"Dialogue: 0,{ts(0)},{ts(T)},Mark,,0,0,0,,{{\\pos(540,80)\\alpha&H30&}}@LeonidaKeysHQ",
    f"Dialogue: 1,{ts(0)},{ts(starts[0]+seg[0]-0.15)},Hook,,0,0,0,,{{\\fad(150,220)}}GTA 6 BROKE THE INTERNET",
    f"Dialogue: 0,{ts(starts[1]+0.35)},{ts(starts[1]+seg[1]-0.25)},Cap,,0,0,0,,{{\\pos(540,1380)}}{c}7.91M{w} watching at once —\\Nan ALL-TIME record",
    f"Dialogue: 0,{ts(starts[2]+0.35)},{ts(starts[2]+seg[2]-0.25)},Cap,,0,0,0,,{{\\pos(540,1380)}}{c}99{w} on Metacritic —\\Nhighest-rated EVER",
    f"Dialogue: 0,{ts(starts[3]+0.35)},{ts(starts[3]+seg[3]-0.25)},Cap,,0,0,0,,{{\\pos(540,1380)}}{c}9.7M{w} preorders —\\Nthe biggest in history",
    f"Dialogue: 0,{ts(starts[4]+0.35)},{ts(starts[4]+seg[4]-0.25)},Cap,,0,0,0,,{{\\pos(540,1380)}}IShowSpeed: {c}4.5M hours{w}\\Nwatched in ONE day",
    f"Dialogue: 1,{ts(starts[5]+0.45)},{ts(T-0.1)},CTA,,0,0,0,,{{\\pos(540,890)\\fad(220,0)}}EVERY KEY TO LEONIDA",
    f"Dialogue: 0,{ts(starts[5]+0.6)},{ts(T-0.1)},Mark,,0,0,0,,{{\\pos(540,1160)\\fs46}}follow @LeonidaKeysHQ · secrets · cars · news",
]
ASS = JOBS / "captions.ass"
ASS.write_text(HDR + "\n".join(ev) + "\n", encoding="utf-8")

# ---- 4. render --------------------------------------------------------------------
fc = []
def blur_layout(idx, D, pre=""):
    """Plugin blur layout on input idx, slowed to fill D seconds. pre = extra crop chain."""
    f = max(1.0, D / dur(FOOT[idx]))
    fc.append(f"[{idx}:v]{pre}setpts={f:.4f}*PTS,fps={FPS},split[a{idx}][b{idx}];"
              f"[a{idx}]scale=-2:{H},crop={W}:{H},boxblur=24:2,eq=brightness=-0.08[bg{idx}];"
              f"[b{idx}]scale={W}:-2[fg{idx}];"
              f"[bg{idx}][fg{idx}]overlay=(W-w)/2:(H-h)/2-80,format=yuv420p,setsar=1,"
              f"trim=0:{D:.3f},setpts=PTS-STARTPTS[v{idx}]")

blur_layout(0, seg[0])                                            # hook: out2 full
blur_layout(1, seg[1])                                            # 7.91M: out1
blur_layout(2, seg[2])                                            # 99: out3
blur_layout(3, seg[3])                                            # 9.7M: postcard
blur_layout(4, seg[4], pre=f"crop=iw*0.55:ih*0.55:0:ih*0.15,")    # Speed: out2 re-framed
F5 = int(round(seg[5] * FPS))                                     # CTA: key art
fc.append(f"[5:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
          f"zoompan=z='max(1.12-0.0009*on,1.0)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
          f"d={F5}:s={W}x{H}:fps={FPS},format=yuv420p,setsar=1[v5]")

prev = "v0"
for k in range(1, 6):
    fc.append(f"[{prev}][v{k}]xfade=transition=fade:duration={XF}:offset={starts[k]:.3f}[x{k}]")
    prev = f"x{k}"
sub = str(ASS).replace("\\", "/").replace(":", "\\:")
fc.append(f"[{prev}]subtitles='{sub}'[vout]")

amix_in = []
for k in range(6):
    d = int((starts[k] + 0.31) * 1000)
    fc.append(f"[{6+k}:a]adelay={d}|{d}[a{k}]")
    amix_in.append(f"[a{k}]")
fc.append(f"[6:a]atrim=0:{T:.3f},volume=0.5,afade=t=in:st=0:d=0.4,"
           f"afade=t=out:st={T-1.4:.3f}:d=1.4[beat]")
fc.append("".join(amix_in) + "[beat]amix=inputs=7:duration=longest:normalize=0,"
          "loudnorm=I=-14:TP=-1.5:LRA=11[aout]")

cmd = [FF, "-y", "-v", "error"]
for p in [FOOT[0], FOOT[1], FOOT[2], FOOT[3], FOOT[4], CTA]:
    cmd += ["-i", str(p)]
cmd += ["-i", str(BEAT)]
for p in VOS:
    cmd += ["-i", str(p)]
cmd += ["-filter_complex", ";".join(fc), "-map", "[vout]", "-map", "[aout]",
        "-t", f"{T:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
        "-movflags", "+faststart", "-shortest", str(OUT)]
run(cmd)
print(f"OK -> {OUT}  ({T:.2f}s, {OUT.stat().st_size/1e6:.1f} MB)")
