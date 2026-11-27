#!/usr/bin/env python3
"""Night variants of the OAT cornerstone, built from the daylight photo.

    python3 scripts/cornerstone-night.py spotlight OUT_DIR [--frames 96]
    python3 scripts/cornerstone-night.py storm     OUT_DIR [--frames 144]

Each run writes OUT_DIR/<variant>.png (the still) and, with --frames > 0,
OUT_DIR/<variant>.mp4 (a seamless loop, H.264, 24 fps). Needs numpy, scipy,
Pillow and ffmpeg. The source is brand/oat-cornerstone/oatCornerstoneBuilding.png;
nothing is painted over the stone itself: every variant relights the original
pixels, so the cornerstone, its lettering and its texture stay the photo's own.

Colours come from the OAT design system (oat-standards, standards/design-system.md):
ink #1E2226 for the night sky, brass #B8860B / #D9A93A for the warm light,
water-light #94D2BD for the neon.
"""
import argparse
import math
import os
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '..', 'brand', 'oat-cornerstone', 'oatCornerstoneBuilding.png')
FPS = 24


def hex_rgb(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)


INK = hex_rgb('#1E2226')
NAVY = hex_rgb('#0B1424')
WARM = hex_rgb('#FFE2B0')       # tungsten uplight
BRASS_LIGHT = hex_rgb('#D9A93A')
NEON = hex_rgb('#94D2BD')       # water-light
NEON_CORE = hex_rgb('#E8FFF7')


def load():
    im = np.asarray(Image.open(SRC).convert('RGB')).astype(np.float32) / 255
    h, w, _ = im.shape
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    mx, mn = im.max(-1), im.min(-1)
    sat = (mx - mn) / (mx + 1e-6)
    xx = np.arange(w)[None, :].repeat(h, 0)
    yy = np.arange(h)[:, None].repeat(w, 1)
    gold = (r > g) & (g > b) & (sat > 0.45) & (r > 0.35) & (xx < 1200)
    gold = ndimage.binary_opening(gold, iterations=1)
    # Sky and the foliage beyond the building edge: everything right of the
    # building's last column that is bright blue or green.
    outside = ((b > r + 0.08) & (b > 0.55)) | ((g > r) & (g > b) & (xx > 1450))
    outside = ndimage.binary_closing(outside, iterations=3)
    outside = ndimage.binary_dilation(outside, iterations=2) & (xx > 1380)
    outside_soft = ndimage.gaussian_filter(outside.astype(np.float32), 2.0)
    gold_soft = ndimage.gaussian_filter(gold.astype(np.float32), 1.2)
    return im, gold, gold_soft, outside_soft, xx.astype(np.float32), yy.astype(np.float32)


def night_base(im, ambient, tint):
    lum = (im * np.array([0.299, 0.587, 0.114], np.float32)).sum(-1, keepdims=True)
    desat = im * 0.45 + lum * 0.55
    return desat * ambient * tint


def sky(h, w, yy, top, bottom):
    t = (yy / h)[..., None]
    return top * (1 - t) + bottom * t


def cone(xx, yy, cx, base_y, spread, half_width, reach):
    """Uplight from a fixture at (cx, base_y) pointing straight up."""
    d = np.clip(base_y - yy, 0, None)
    width = half_width + spread * d
    across = np.exp(-((xx - cx) / width) ** 2)
    along = np.exp(-d / reach) * (d > 0)
    hotspot = np.exp(-((xx - cx) ** 2 + (yy - base_y) ** 2) / (2 * 140 ** 2))
    return across * along + 0.6 * hotspot


def vignette(h, w, strength):
    y = np.linspace(-1, 1, h)[:, None]
    x = np.linspace(-1, 1, w)[None, :]
    return (1 - strength * np.clip(x ** 2 * 0.6 + y ** 2 * 0.8, 0, 1))[..., None]


def to_img(a):
    return Image.fromarray((np.clip(a, 0, 1) ** (1 / 1.0) * 255 + 0.5).astype(np.uint8))


# ---------------------------------------------------------------- spotlight

def spotlight_frame(S, phase):
    im, gold, gold_soft, outside, xx, yy = S
    h, w, _ = im.shape
    base = night_base(im, 0.075, np.array([0.55, 0.66, 1.0], np.float32))
    # Two uplights in the pavement, sweeping slowly in opposite directions.
    s1 = 140 * math.sin(2 * math.pi * phase)
    s2 = 140 * math.sin(2 * math.pi * phase + math.pi * 0.85)
    light = (cone(xx, yy, 420 + s1, 1010, 0.26, 55, 620) * 1.15 +
             cone(xx, yy, 1010 + s2, 1010, 0.26, 55, 620) * 1.05)
    light = light[..., None]
    lit = im * light * WARM * 1.35
    # Brass catches the light: extra specular where the letters sit under a beam.
    glint = (gold_soft[..., None] * light * 0.9) * BRASS_LIGHT
    out = base + lit + glint
    # Soft bloom around the brightest lettering.
    bloom = ndimage.gaussian_filter((gold_soft * light[..., 0]), 9)[..., None] * BRASS_LIGHT * 0.55
    out = out + bloom
    # Night sky where the daylight sky and trees were.
    night = sky(h, w, yy, NAVY * 0.9, INK)
    o = outside[..., None]
    out = out * (1 - o) + night * o
    # Faint haze in the beams, above the cornerstone.
    haze = (cone(xx, yy, 420 + s1, 1010, 0.55, 90, 900) + cone(xx, yy, 1010 + s2, 1010, 0.55, 90, 900))
    out = out + (haze * (yy < 260) * 0.05)[..., None] * WARM
    return out * vignette(h, w, 0.55)


# -------------------------------------------------------------------- storm

def rain_layer(h, w, n, length, angle_deg, alpha, seed, width=1):
    rng = np.random.default_rng(seed)
    layer = Image.new('L', (w, h), 0)
    d = ImageDraw.Draw(layer)
    dx = math.cos(math.radians(angle_deg))
    dy = math.sin(math.radians(angle_deg))
    for _ in range(n):
        x = rng.uniform(-100, w + 100)
        y = rng.uniform(0, h)
        L = rng.uniform(*length)
        a = int(255 * rng.uniform(*alpha))
        for off in (0, -h):   # draw a wrapped copy so the layer tiles vertically
            d.line([(x, y + off), (x + dx * L, y + dy * L + off)], fill=a, width=width)
    arr = np.asarray(layer).astype(np.float32) / 255
    return ndimage.gaussian_filter(arr, 0.6)


def bolt(h, w, seed, x0, x1, y_end):
    rng = np.random.default_rng(seed)
    layer = Image.new('L', (w, h), 0)
    d = ImageDraw.Draw(layer)
    pts = [(x0, -10)]
    x, y = x0, -10
    while y < y_end:
        y += rng.uniform(18, 40)
        x += rng.uniform(-28, 22) + (x1 - x0) / 12
        pts.append((x, y))
        if rng.random() < 0.18:   # side branch
            bx, by = x, y
            for _ in range(int(rng.integers(2, 5))):
                nbx, nby = bx + rng.uniform(-40, 10), by + rng.uniform(15, 30)
                d.line([(bx, by), (nbx, nby)], fill=150, width=2)
                bx, by = nbx, nby
    d.line(pts, fill=255, width=4)
    core = np.asarray(layer).astype(np.float32) / 255
    return core, ndimage.gaussian_filter(core, 10)


def storm_setup(S):
    im, gold, gold_soft, outside, xx, yy = S
    h, w, _ = im.shape
    edge = ndimage.binary_dilation(gold, iterations=3) & ~ndimage.binary_erosion(gold, iterations=1)
    tube = ndimage.gaussian_filter(edge.astype(np.float32), 1.0)
    glow = ndimage.gaussian_filter(edge.astype(np.float32), 14) * 6
    wide = ndimage.gaussian_filter(edge.astype(np.float32), 45) * 18
    # Wet pavement: the neon reflected, smeared, in the strip below the plinth.
    refl = np.zeros_like(glow)
    rows = np.arange(h)
    ground = rows > 905
    src_rows = np.clip(2 * 905 - rows, 0, h - 1)
    refl[ground] = glow[src_rows[ground]]
    refl = ndimage.gaussian_filter(refl, (6, 22)) * 0.55
    layers = [
        rain_layer(h, w, 900, (28, 46), 78, (0.10, 0.22), 1),
        rain_layer(h, w, 450, (50, 80), 76, (0.18, 0.32), 2, width=2),
        rain_layer(h, w, 160, (90, 130), 74, (0.20, 0.35), 3, width=2),
    ]
    b1 = bolt(h, w, 7, 1475, 1430, 260)
    return dict(gold_soft=gold_soft, tube=tube, glow=glow, wide=wide, refl=refl, rain=layers, bolt=b1)


NEON_FLICKER = {i: v for i, v in [(80, 0.15), (81, 1.0), (82, 0.0), (83, 0.0), (84, 0.6), (85, 1.0), (86, 0.3)]}


def flash_level(f, n):
    """Lightning: a double strike near 1.2 s and a softer one near 4.4 s."""
    t = f / FPS
    lvl = 0.0
    for t0, peak in ((1.2, 1.0), (1.42, 0.75), (4.4, 0.45)):
        dt = t - t0
        if 0 <= dt < 0.35:
            lvl = max(lvl, peak * math.exp(-dt * 11) * (1 if int(dt * FPS) != 2 else 0.35))
    return lvl


def storm_frame(S, X, f, n, still=False):
    im, gold, gold_soft, outside, xx, yy = S
    h, w, _ = im.shape
    flash = 0.5 if still else flash_level(f, n)
    neon_on = 1.0 if still else NEON_FLICKER.get(f % n, 1.0)
    tint = np.array([0.52, 0.62, 0.80], np.float32)
    base = night_base(im, 0.15, tint)
    # Wet stone reads darker and more contrasty.
    base = np.clip((base - 0.01) * 1.15, 0, 1)
    nsum = neon_on * (X['tube'][..., None] * NEON_CORE * 0.95 +
                      X['glow'][..., None] * NEON * 0.30 +
                      X['wide'][..., None] * NEON * 0.07)
    # Neon also lights the stone around it (relit original pixels, cool cast).
    spill = neon_on * np.clip(X['wide'] * 0.9 + X['glow'] * 0.12, 0, 1)[..., None] * im * NEON * 0.8
    refl = neon_on * X['refl'][..., None] * NEON
    goldlit = neon_on * X['gold_soft'][..., None] * im * 0.55
    out = base + spill + goldlit + nsum + refl
    # Storm sky
    stormsky = sky(h, w, yy, hex_rgb('#1A2433'), INK * 0.8)
    o = outside[..., None]
    out = out * (1 - o) + stormsky * o
    # Lightning: cold light from upper right over everything, plus the bolt.
    if flash > 0:
        dirl = np.clip(1.15 - (np.abs(xx - w) / w) * 0.6 - (yy / h) * 0.5, 0, 1)[..., None]
        out = out + im * flash * 1.1 * dirl * np.array([0.85, 0.92, 1.0], np.float32)
        core, halo = X['bolt']
        out = out + (core[..., None] * 1.2 + halo[..., None] * 0.9) * min(1.0, flash * 2) * np.array([0.9, 0.95, 1.0], np.float32)
    # Rain: three depths, each tiling vertically and moving a whole number of
    # screen heights per loop so the loop is seamless.
    for k, (layer, speed) in enumerate(zip(X['rain'], (1, 2, 3))):
        shift = int(round(h * speed * (f / n))) % h if not still else 0
        r = np.roll(layer, shift, axis=0)
        bright = 0.16 + 0.12 * k + flash * 0.7
        out = out + r[..., None] * bright * np.array([0.78, 0.86, 0.95], np.float32)
    return out * vignette(h, w, 0.6)


# ------------------------------------------------------------------ output

def write_video(frames_dir, n, out_mp4):
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS),
           '-i', os.path.join(frames_dir, 'f%04d.png'),
           '-vf', 'scale=1536:1024:flags=lanczos,format=yuv420p',
           '-c:v', 'libx264', '-preset', 'slow', '-crf', '21', '-tune', 'film',
           '-movflags', '+faststart', '-an', out_mp4]
    subprocess.run(cmd, check=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('variant', choices=['spotlight', 'storm'])
    p.add_argument('out_dir')
    p.add_argument('--frames', type=int, default=None)
    a = p.parse_args()
    n = a.frames if a.frames is not None else (96 if a.variant == 'spotlight' else 144)
    os.makedirs(a.out_dir, exist_ok=True)
    S = load()
    name = 'cornerstone-night-spotlight' if a.variant == 'spotlight' else 'cornerstone-night-storm'
    if a.variant == 'spotlight':
        to_img(spotlight_frame(S, 0.0)).save(os.path.join(a.out_dir, name + '.png'), optimize=True)
    else:
        X = storm_setup(S)
        to_img(storm_frame(S, X, 0, n, still=True)).save(os.path.join(a.out_dir, name + '.png'), optimize=True)
    if n > 0:
        with tempfile.TemporaryDirectory() as td:
            for f in range(n):
                fr = spotlight_frame(S, f / n) if a.variant == 'spotlight' else storm_frame(S, X, f, n)
                to_img(fr).save(os.path.join(td, 'f%04d.png' % f), compress_level=1)
                if f % 24 == 0:
                    print(f'{name}: frame {f}/{n}', file=sys.stderr)
            write_video(td, n, os.path.join(a.out_dir, name + '.mp4'))


if __name__ == '__main__':
    main()
