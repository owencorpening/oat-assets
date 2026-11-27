#!/usr/bin/env python3
"""Snow variant of the OAT cornerstone, built from the daylight photo.

    python3 cornerstone_snow.py SOURCE_PNG OUT_DIR [--frames 144]

SOURCE_PNG is brand/oat-cornerstone/oatCornerstoneBuilding.png (1536x1024).
Writes OUT_DIR/cornerstone-snow.png (the still) and, with --frames > 0,
OUT_DIR/cornerstone-snow.mp4: a 6 s seamless loop, H.264, 24 fps, no audio.

Winter dusk: the stone is relit cool, the sky goes to a dusk blue, the brass
letters and the wall lantern glow warm, and snow falls at three depths with a
slight drift. Snow lies on the cushion moulding, the shelf above the block, the
plinth and the walkway: those caps are painted in, following the stone's own
edges (measured from the photo), so the lettering and texture stay the photo's.
Companion to scripts/cornerstone-night.py; needs numpy, scipy, Pillow, ffmpeg.
"""
import argparse, math, os, subprocess

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

FPS = 24
W, H = 1536, 1024
SNOW = np.array([0.94, 0.96, 0.99], np.float32)
WARM = np.array([1.0, 0.886, 0.69], np.float32)
BRASS_LIGHT = np.array([0.851, 0.663, 0.227], np.float32)


def load(src):
    im = np.asarray(Image.open(src).convert('RGB')).astype(np.float32) / 255
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    mx, mn = im.max(-1), im.min(-1)
    sat = (mx - mn) / (mx + 1e-6)
    xx = np.arange(W)[None, :].repeat(H, 0)
    gold = (r > g) & (g > b) & (sat > 0.45) & (r > 0.35) & (xx < 1200)
    gold = ndimage.binary_opening(gold, iterations=1)
    outside = ((b > r + 0.08) & (b > 0.55)) | ((g > r) & (g > b) & (xx > 1450))
    outside = ndimage.binary_closing(outside, iterations=3)
    outside = ndimage.binary_dilation(outside, iterations=2) & (xx > 1380)
    return im, gold, ndimage.gaussian_filter(gold.astype(np.float32), 1.2), \
        ndimage.gaussian_filter(outside.astype(np.float32), 2.0)


def band(x0, x1, ytop, depth_fn, up, rng, lump=4.0):
    """A snow cap following the edge y = ytop(x): from `up` px above it
    (with a lumpy top) to depth_fn(x) px below it (with a ragged lower edge),
    thinning to nothing at both ends."""
    m = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(m)
    xs = np.arange(x0, x1 + 1, 3, dtype=np.float32)
    taper = np.clip(np.minimum(xs - x0, x1 - xs) / 60, 0, 1) ** 0.6
    bumps = np.abs(ndimage.gaussian_filter1d(rng.standard_normal(len(xs)).astype(np.float32), 3)) * lump * 2
    drips = ndimage.gaussian_filter1d(rng.standard_normal(len(xs)).astype(np.float32), 1.5) * lump
    top = [(x, ytop(x) - (up + bb) * t) for x, bb, t in zip(xs, bumps, taper)]
    bot = [(x, ytop(x) + (depth_fn(x) + dr) * t) for x, dr, t in zip(xs[::-1], drips[::-1], taper[::-1])]
    d.polygon(top + bot, fill=255)
    return np.asarray(m).astype(np.float32) / 255


def caps(rng):
    # Edges measured from the photo's luminance (see notes): groove above the
    # cushion moulding, the shelf above the block, the block's base on the plinth.
    cushion = band(150, 995, lambda x: 146 - 0.157 * (x - 300), lambda x: 9, 6, rng)
    shelf = band(120, 995, lambda x: 271 - 0.12 * (x - 300), lambda x: 7, 4, rng, 3)
    plinth = band(45, 1150, lambda x: 826 + 0.08 * (x - 300),
                  lambda x: (866 + 0.10 * (x - 300)) - (826 + 0.08 * (x - 300)) - 2, 5, rng)
    m = np.maximum(np.maximum(cushion, shelf), plinth)
    g = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(g)
    d.polygon([(1452, 694), (W, 684), (W, H), (1326, H)], fill=255)      # walkway, right
    ground = np.asarray(g).astype(np.float32) / 255
    m = ndimage.gaussian_filter(m, 1.3)
    ground = ndimage.gaussian_filter(ground, 3.0)
    return np.clip(m, 0, 1), ground


def flakes(n, r, alpha, seed, speed, sway):
    rng = np.random.default_rng(seed)
    return dict(x=rng.uniform(-40, W + 40, n), y=rng.uniform(0, H, n), r=rng.uniform(*r, n),
                a=rng.uniform(*alpha, n), v=speed, ph=rng.uniform(0, 1, n),
                k=rng.choice((1, 2), n), amp=rng.uniform(*sway, n))


def draw_flakes(F, phase, blur):
    layer = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(layer)
    ys = (F['y'] + F['v'] * H * phase) % (H + 40) - 20
    xs = F['x'] + F['amp'] * np.sin(2 * math.pi * (F['k'] * phase + F['ph']))
    for x, y, r, a in zip(xs, ys, F['r'], F['a']):
        d.ellipse([x - r, y - r, x + r, y + r], fill=int(255 * a))
    arr = np.asarray(layer).astype(np.float32) / 255
    return ndimage.gaussian_filter(arr, blur) if blur else arr


def vignette(strength):
    y = np.linspace(-1, 1, H)[:, None]
    x = np.linspace(-1, 1, W)[None, :]
    return (1 - strength * np.clip(x ** 2 * 0.6 + y ** 2 * 0.8, 0, 1))[..., None].astype(np.float32)


def setup(src):
    im, gold, gold_soft, outside = load(src)
    rng = np.random.default_rng(5)
    cap, ground = caps(rng)
    noise = ndimage.gaussian_filter(rng.standard_normal((H, W)).astype(np.float32), 2.5)
    noise /= noise.std()
    yy = np.arange(H, dtype=np.float32)[:, None].repeat(W, 1)
    xx = np.arange(W, dtype=np.float32)[None, :].repeat(H, 0)
    lum = (im * np.array([0.299, 0.587, 0.114], np.float32)).sum(-1, keepdims=True)
    base = (im * 0.55 + lum * 0.45) * 0.62 * np.array([0.74, 0.83, 1.0], np.float32)
    lumn = lum / max(float(lum.mean()), 1e-6)
    snow_col = SNOW * (0.74 + 0.03 * np.clip(noise, -2, 2))[..., None] * (0.85 + 0.15 * lumn) * \
        np.array([0.88, 0.93, 1.0], np.float32)
    base = base * (1 - cap[..., None]) + snow_col * cap[..., None]
    gsnow = SNOW * (0.55 + 0.03 * np.clip(noise, -2, 2))[..., None] * (0.6 + 0.4 * lumn) * \
        np.array([0.86, 0.92, 1.0], np.float32)
    base = base * (1 - 0.8 * ground[..., None]) + gsnow * 0.8 * ground[..., None]
    t = (yy / H)[..., None]
    sky = np.array([0.17, 0.22, 0.33], np.float32) * (1 - t) + np.array([0.42, 0.50, 0.64], np.float32) * t
    o = outside[..., None]
    base = base * (1 - o) + sky * o
    lantern = np.exp(-((xx - 1497) ** 2 + (yy - 190) ** 2) / (2 * 28 ** 2))
    lantern_wide = np.exp(-((xx - 1497) ** 2 + (yy - 200) ** 2) / (2 * 150 ** 2))
    return dict(base=base, im=im, gold_soft=gold_soft,
                bloom=ndimage.gaussian_filter(gold_soft, 9),
                lantern=lantern, lantern_wide=lantern_wide,
                far=flakes(800, (0.9, 1.7), (0.35, 0.65), 21, 1, (6, 18)),
                mid=flakes(300, (1.8, 3.0), (0.55, 0.85), 22, 1, (12, 30)),
                near=flakes(80, (3.5, 6.5), (0.55, 0.9), 23, 2, (20, 45)))


def frame(S, phase):
    warm = 0.93 + 0.07 * math.sin(2 * math.pi * phase)
    out = S['base'] + S['gold_soft'][..., None] * S['im'] * 0.75 * warm
    out = out + S['bloom'][..., None] * BRASS_LIGHT * 0.50 * warm
    out = out + (S['lantern'] * 0.9 + S['lantern_wide'] * 0.18)[..., None] * WARM * warm
    for name, blur, lvl in (('far', 0, 0.55), ('mid', 0.6, 0.8), ('near', 1.8, 0.85)):
        L = draw_flakes(S[name], phase, blur)
        out = out * (1 - L[..., None] * lvl) + SNOW * L[..., None] * lvl
    return out * vignette(0.5)


def to_u8(a):
    return (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('source')
    ap.add_argument('out_dir')
    ap.add_argument('--frames', type=int, default=144)
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    S = setup(a.source)
    Image.fromarray(to_u8(frame(S, 0.0))).save(os.path.join(a.out_dir, 'cornerstone-snow.png'), optimize=True)
    if a.frames > 0:
        cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
               '-s', f'{W}x{H}', '-framerate', str(FPS), '-i', '-', '-vf', 'format=yuv420p',
               '-c:v', 'libx264', '-preset', 'slow', '-crf', '21', '-tune', 'film',
               '-movflags', '+faststart', '-an', os.path.join(a.out_dir, 'cornerstone-snow.mp4')]
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for f in range(a.frames):
            p.stdin.write(to_u8(frame(S, f / a.frames)).tobytes())
        p.stdin.close()
        if p.wait():
            raise SystemExit('ffmpeg failed')


if __name__ == '__main__':
    main()
