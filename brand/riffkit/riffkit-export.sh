#!/usr/bin/env bash
# riffkit export pipeline
# Rebuilds exports/*.png and *.ico from the vector sources in exports/svg/.
# Run from anywhere:  bash riffkit-export.sh
# Needs rsvg-convert (librsvg) or cairosvg, and ImageMagick for the .ico files.
# To change the artwork itself, use the brand kit (see notes.txt).

set -e
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$HERE/exports/svg"
OUT="$HERE/exports"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT

ras() {   # ras SOURCE.svg OUT.png WIDTH HEIGHT   (empty WIDTH keeps the aspect)
  local src="$SRC/$1" out="$OUT/$2" w=$3 h=$4
  mkdir -p "$(dirname "$out")"
  if command -v rsvg-convert >/dev/null; then
    if [ -n "$w" ]; then rsvg-convert -w "$w" -h "$h" "$src" -o "$out"
    else rsvg-convert -h "$h" "$src" -o "$out"; fi
  else
    if [ -n "$w" ]; then cairosvg "$src" --output-width "$w" --output-height "$h" -o "$out"
    else cairosvg "$src" --output-height "$h" -o "$out"; fi
  fi
  echo "  ✓ $2"
}

ico() {   # ico SOURCE.svg OUT.ico SIZE...
  local src=$1 out=$2; shift 2
  local parts=()
  for n in "$@"; do
    SRC_SAVE="$OUT"; OUT="$TMP"; ras "$src" "ico-$n.png" "$n" "$n" >/dev/null; OUT="$SRC_SAVE"
    parts+=("$TMP/ico-$n.png")
  done
  if command -v magick >/dev/null; then magick "${parts[@]}" "$OUT/$out"; else convert "${parts[@]}" "$OUT/$out"; fi
  echo "  ✓ $out"
}

echo "riffkit exports -> $OUT"
ras "card-1280x640.svg" "github-social-1280x640.png" 1280 640
ras "card-1200x630.svg" "og-image-1200x630.png" 1200 630
ico "icon.svg" "favicon.ico" 16 32 48
mkdir -p "$(dirname "$OUT/favicon.svg")"; cp "$SRC/favicon.svg" "$OUT/favicon.svg"; echo "  ✓ favicon.svg"
ras "icon.svg" "favicon-32.png" 32 32
ras "icon.svg" "apple-touch-icon-180.png" 180 180
ras "icon.svg" "icon-192.png" 192 192
ras "icon.svg" "icon-512.png" 512 512
ras "icon-maskable.svg" "icon-maskable-512.png" 512 512
ras "icon.svg" "linux-hicolor/16x16/apps/riffkit.png" 16 16
ras "icon.svg" "linux-hicolor/24x24/apps/riffkit.png" 24 24
ras "icon.svg" "linux-hicolor/32x32/apps/riffkit.png" 32 32
ras "icon.svg" "linux-hicolor/48x48/apps/riffkit.png" 48 48
ras "icon.svg" "linux-hicolor/64x64/apps/riffkit.png" 64 64
ras "icon.svg" "linux-hicolor/128x128/apps/riffkit.png" 128 128
ras "icon.svg" "linux-hicolor/256x256/apps/riffkit.png" 256 256
ras "icon.svg" "linux-hicolor/512x512/apps/riffkit.png" 512 512
mkdir -p "$(dirname "$OUT/linux-hicolor/scalable/apps/riffkit.svg")"; cp "$SRC/icon.svg" "$OUT/linux-hicolor/scalable/apps/riffkit.svg"; echo "  ✓ linux-hicolor/scalable/apps/riffkit.svg"
ico "icon.svg" "windows-riffkit.ico" 16 24 32 48 64 128 256
echo "── Complete: 19 exports ──"
