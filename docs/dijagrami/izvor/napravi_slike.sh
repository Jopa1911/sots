#!/bin/bash
# Pravi SVG i PNG za sve tri slike: bash docs/dijagrami/izvor/napravi_slike.sh (potreban Google Chrome ili Chromium)
set -e
cd "$(dirname "$0")"
OUT=..
python3 dijagrami.py "$OUT"
python3 arhitektura.py "$OUT"
CHROME=$(command -v google-chrome || command -v chromium || command -v chromium-browser)
render() {  # ime sirina visina
  printf '<!DOCTYPE html><html><head><meta charset="utf-8"><style>body{margin:0}</style></head><body>%s</body></html>' \
    "$(cat "$OUT/$1.svg")" > "/tmp/$1.html"
  "$CHROME" --headless=new --no-sandbox --hide-scrollbars --force-device-scale-factor=2 --window-size="$2,$3" \
    --screenshot="$OUT/$1.png" "file:///tmp/$1.html"
  rm "$OUT/$1.svg"
}
render memorija_agenta 1870 1010
render stanja_ljutnje 1530 660
render arhitektura_simulatora 1860 960
