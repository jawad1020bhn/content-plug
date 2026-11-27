"""Deterministic black-background effects first used in Slot 009 v5."""
import math

import cv2
import numpy as np

from build_video_template import make_mote_sprite


def atmosphere():
    rng = np.random.default_rng(9009)
    sprites = [make_mote_sprite(n) for n in (120, 90, 140, 70)]
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
