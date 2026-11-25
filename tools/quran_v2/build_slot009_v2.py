#!/usr/bin/env python3
"""Rebuild slot 009 v2 from the original timing/audio and a replacement popup."""
import argparse
import json
import math
import subprocess
from pathlib import Path

import cv2
import numpy as np

import build_video_template as card

SLOT = '009_aal-e-imran_3-193-194_minshawi'
ROOT = card.ROOT
ASSETS = ROOT / 'assets' / 'quran' / SLOT
JOB = ROOT / 'jobs' / f'{SLOT}_v2'
V1 = ROOT / 'outputs' / f'quran-{SLOT}_en_1080x1920_v1.mp4'
V2 = V1.with_name(V1.name.replace('_v1.mp4', '_v2.mp4'))
SHIFT_Y = 17


def atmosphere():
    rng = np.random.default_rng(9009)
    sprites = [card.make_mote_sprite(n) for n in (120, 90, 140, 70)]
    orbs = [(rng.uniform(100, 980), rng.uniform(150, 1750), rng.uniform(5,11), rng.uniform(0, 6.28)) for _ in sprites]
    stars = [(rng.integers(20,1060), rng.integers(20,1900), rng.uniform(.4,1.3), rng.uniform(0,6.28)) for _ in range(50)]
    meteors = [(6.0, 880, 240, 32, 900), (22.5, 200, 1500, -28, 820), (38.0, 920, 1560, -35, 950)]

    def draw(canvas, t, voice):
        for sprite, (x, y, speed, phase) in zip(sprites, orbs):
            size = sprite.shape[0]
            x0 = int(x + 25 * math.sin(.55*t + phase)) - size//2
            y0 = int((y - speed*t) % 1750 + 70) - size//2
            patch = (sprite[...,None] * (np.array([190,204,218]) * (.04+.03*voice))).astype(np.uint8)
            roi = canvas[y0:y0+size, x0:x0+size]
            np.maximum(roi, patch, out=roi)
        for x,y,f,phase in stars:
            value = int(100 * (.5 + .5*math.sin(2*math.pi*f*t+phase))**2)
            canvas[y,x] = np.maximum(canvas[y,x], value)
        for start,x,y,angle,speed in meteors:
            dt = t-start
            if not 0 <= dt < .8:
                continue
            a = math.radians(angle)
            vx, vy = math.cos(a), math.sin(a)
            for u in range(12):
                lead = speed*dt - u*(130/12)
                tail = lead - 130/12
                value = int(165*math.sin(math.pi*dt/.8)*(1-u/12)**1.6)
                cv2.line(canvas, (round(x+vx*lead),round(y+vy*lead)),
                         (round(x+vx*tail),round(y+vy*tail)), (value,)*3, 2, cv2.LINE_AA)
    return draw


def setup():
    job_data = json.loads((ASSETS / 'beats009.json').read_text())
    beats = job_data['beats']
    for b in beats:
        b['english'] = b['english'].replace('ﷺ', r'{\fnAmiri\fs44}ﷺ{\r}')
    card.BEATS = beats
    card.BEAT_STARTS = [b['start'] for b in beats]
    card.AYAH_SPANS = job_data['ayah_spans']
    card.DURATION_S = job_data['render_s']
    card.TOTAL_FRAMES = job_data['render_frames']
    card.REC_START_S, card.REC_END_S = job_data['rec_start_s'], job_data['rec_end_s']
    card.POP_W, card.POP_H, card.POP_X, card.POP_Y, card.POP_R = 860, 1040, 110, 250, 64
    card.CROP_CENTER_Y = 0.0
    card.KEN_BURNS_GROWTH = 0.020
    card.HEADER_TEXT = 'Surah Aal-e-Imran'
    card.ARABIC_SIZE = 80
    card.ARABIC_Y, card.ENGLISH_Y = (1395,1350), (1570,1480)
    card.REF_Y, card.FILAMENT_Y = 1700,1770
    card.MOTE_SEED = card.GRAIN_SEED = 2026009
    card.BACKGROUND_EFFECTS = atmosphere()
    card.JOB_DIR = JOB
    card.PIN_CLIP = JOB / 'looped_pin.mp4'
    card.VISUAL_BASE = JOB / 'visual_base.mp4'
    card.ASS_PATH = JOB / 'captions.ass'
    card.HEADER_ASS = JOB / 'header.ass'
    card.HEADER_PNG = JOB / 'header.png'
    card.ENV_NPY = JOB / 'env.npy'


def render(source):
    JOB.mkdir(parents=True, exist_ok=True)
    # Normalize PTS and frame rate before the crossfades; discard the clip soundtrack.
    normal = JOB / 'normalized_pin.mp4'
    subprocess.run([card.FFMPEG,'-v','error','-y','-i',str(source),'-map','0:v:0','-an',
                    '-vf','fps=30,setsar=1','-c:v','libx264','-crf','16','-pix_fmt','yuv420p',str(normal)],check=True)
    cap = cv2.VideoCapture(str(normal))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); cap.release()
    assert n >= 30, 'Expected at least one second of popup footage'
    fade = 12  # frames, 0.4 seconds
    repeats = max(1, round((card.TOTAL_FRAMES-fade)/(n-fade)))
    if repeats == 1:
        subprocess.run([card.FFMPEG,'-v','error','-y','-i',str(normal),'-map','0:v','-c','copy',str(card.PIN_CLIP)],check=True)
    else:
        inputs = ['-i',str(normal)]*repeats
        graph=[]; prev='0:v'
        for k in range(1,repeats):
            dst=f'x{k}'
            graph.append(f'[{prev}][{k}:v]xfade=duration={fade/30:.6f}:offset={k*(n-fade)/30:.6f}[{dst}]')
            prev=dst
        subprocess.run([card.FFMPEG,'-v','error','-y',*inputs,'-filter_complex_threads','2','-filter_complex',
                        ';'.join(graph),'-map',f'[{prev}]','-an','-c:v','libx264','-crf','16',
                        '-pix_fmt','yuv420p',str(card.PIN_CLIP)],check=True)
    print(f'Popup source: {n/30:.2f} s, {repeats} run(s)', flush=True)
    buf=subprocess.check_output([card.FFMPEG,'-v','error','-i',str(ASSETS/'recitation_raw.m4a'),
                                 '-map','0:a:0','-ac','1','-ar','44100','-f','f32le','-'])
    pcm=np.frombuffer(buf,dtype=np.float32)[:card.TOTAL_FRAMES*1470].reshape(-1,1470)
    rms=np.sqrt(np.mean(pcm**2,axis=1)); smoothed=np.zeros_like(rms); value=0.
    for i,v in enumerate(rms):
        value+=(.38 if v>value else .14)*(v-value); smoothed[i]=value
    np.save(card.ENV_NPY,np.clip(smoothed/(np.percentile(smoothed,95) or 1),0,1))
    card.write_captions_ass()
    card.render_visual_base()
    # Move the composited image, including every subtitle and the opening/closing frames.
    # Shift in 4:4:4 so the odd 17 px offset does not round to 16 in 4:2:0.
    filt=(f'ass=filename={card.ff_escape(card.ASS_PATH)}:fontsdir={card.ff_escape(card.FONT_DIR)}:shaping=1,'
          f'format=yuv444p,pad=1080:{1920+SHIFT_Y}:0:0:color=black,crop=1080:1920:0:{SHIFT_Y}:exact=1')
    subprocess.run([card.FFMPEG,'-v','error','-y','-i',str(card.VISUAL_BASE),'-i',str(V1),
                    '-map','0:v:0','-map','1:a:0','-vf',filt,'-c:v','libx264','-crf','18','-preset','medium',
                    '-pix_fmt','yuv420p','-c:a','copy','-movflags','+faststart',str(V2)],check=True)
    print(V2, flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    args=parser.parse_args()
    setup()
    render(args.source)
