#!/usr/bin/env bash
# Falla si hay CDNs o URLs externas en templates/ o static/.
set -e
FORBIDDEN=(
  "cdn.jsdelivr.net" "unpkg.com" "cdnjs.cloudflare.com"
  "fonts.googleapis.com" "cdn.tailwindcss.com" "fonts.gstatic.com"
  "code.jquery.com" "stackpath.bootstrapcdn.com" "maxcdn.bootstrapcdn.com"
  "ajax.googleapis.com" "kit.fontawesome.com" "use.fontawesome.com"
  "cdn.datatables.net" "cdn.skypack.dev" "esm.sh"
)
FOUND=0
for p in "${FORBIDDEN[@]}"; do
  HITS=$(grep -rIl "$p" templates/ static/js/src static/css/src 2>/dev/null || true)
  if [ -n "$HITS" ]; then
    echo "ERROR: CDN detectado ($p):"
    echo "$HITS"
    FOUND=1
  fi
done

EXT=$(grep -rEn '(src|href)="https?://' templates/ 2>/dev/null | \
  grep -vE 'localhost|127\.0\.0\.1|example\.com' || true)
if [ -n "$EXT" ]; then
  echo "ERROR: Referencias externas:"
  echo "$EXT"
  FOUND=1
fi

if [ "$FOUND" -eq 1 ]; then exit 1; fi
echo "OK: sin CDNs ni referencias externas"
