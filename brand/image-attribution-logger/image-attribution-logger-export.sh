#!/usr/bin/env bash
# Image Attribution Logger export pipeline
# Rebuilds exports/*.png and *.ico from the vector sources in exports/svg/.
# Run from anywhere:  bash image-attribution-logger-export.sh
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

echo "Image Attribution Logger exports -> $OUT"
ras "card-1280x640.svg" "github-social-1280x640.png" 1280 640
ras "card-1200x630.svg" "og-image-1200x630.png" 1200 630
echo "── Complete: 2 exports ──"
