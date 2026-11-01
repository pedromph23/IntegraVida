#!/usr/bin/env bash
# Falla si hay CDNs o cargas de recursos externos en templates/ o static/.
#
# §5.1: bloquea CARGAS (src, <link href>, @import, url(), fetch/import).
# NO bloquea navegación externa (<a href="https://...">, tel:, mailto:).
# Un footer puede enlazar a WhatsApp, X, Instagram, Telegram sin que
# ello constituya una carga externa.
set -e

FORBIDDEN=(
  "cdn.jsdelivr.net" "unpkg.com" "cdnjs.cloudflare.com"
  "fonts.googleapis.com" "cdn.tailwindcss.com" "fonts.gstatic.com"
  "code.jquery.com" "stackpath.bootstrapcdn.com" "maxcdn.bootstrapcdn.com"
  "ajax.googleapis.com" "kit.fontawesome.com" "use.fontawesome.com"
  "cdn.datatables.net" "cdn.skypack.dev" "esm.sh"
)

FOUND=0

# 1) Dominios CDN prohibidos — falla en cualquier contexto
for p in "${FORBIDDEN[@]}"; do
  HITS=$(grep -rIl "$p" templates/ static/js/src static/css/src 2>/dev/null || true)
  if [ -n "$HITS" ]; then
    echo "ERROR: CDN detectado ($p):"
    echo "$HITS"
    FOUND=1
  fi
done

# 2) src externo en templates (script, img, iframe, video, audio, source, embed, track)
SRC_EXT=$(grep -rEn 'src="https?://' templates/ 2>/dev/null | \
  grep -vE 'localhost|127\.0\.0\.1|example\.com' || true)
if [ -n "$SRC_EXT" ]; then
  echo "ERROR: src externo en template:"
  echo "$SRC_EXT"
  FOUND=1
fi

# 3) srcset externo (responsive images)
SRCSET_EXT=$(grep -rEn 'srcset="https?://' templates/ 2>/dev/null | \
  grep -vE 'localhost|127\.0\.0\.1|example\.com' || true)
if [ -n "$SRCSET_EXT" ]; then
  echo "ERROR: srcset externo en template:"
  echo "$SRCSET_EXT"
  FOUND=1
fi

# 4) <link> externo (stylesheet, preload, icon, manifest)
#    Patrón: <link ... href="https://    — distingue de <a href="https://
LINK_EXT=$(grep -rEn '<link[^>]+href="https?://' templates/ 2>/dev/null | \
  grep -vE 'localhost|127\.0\.0\.1|example\.com' || true)
if [ -n "$LINK_EXT" ]; then
  echo "ERROR: <link> externo en template:"
  echo "$LINK_EXT"
  FOUND=1
fi

# 5) <object data> externo
OBJ_EXT=$(grep -rEn '<object[^>]+data="https?://' templates/ 2>/dev/null | \
  grep -vE 'localhost|127\.0\.0\.1|example\.com' || true)
if [ -n "$OBJ_EXT" ]; then
  echo "ERROR: <object data> externo en template:"
  echo "$OBJ_EXT"
  FOUND=1
fi

# 6) url() o @import con http(s) en CSS
CSS_EXT=$(grep -rEn '(url\(|@import).*https?://' static/css/src 2>/dev/null | \
  grep -vE 'localhost|127\.0\.0\.1|example\.com' || true)
if [ -n "$CSS_EXT" ]; then
  echo "ERROR: url()/@import externo en CSS:"
  echo "$CSS_EXT"
  FOUND=1
fi

# 7) fetch(...) o import(...) externos en JS
JS_EXT=$(grep -rEn '(fetch|import)[[:space:]]*\([[:space:]]*["'\'']https?://' static/js/src 2>/dev/null | \
  grep -vE 'localhost|127\.0\.0\.1|example\.com' || true)
if [ -n "$JS_EXT" ]; then
  echo "ERROR: fetch/import externo en JS:"
  echo "$JS_EXT"
  FOUND=1
fi

if [ "$FOUND" -eq 1 ]; then
  echo ""
  echo "Revisa las líneas marcadas. Las anclas <a href=\"https://...\">"
  echo "para navegación (WhatsApp, redes sociales) son legítimas y no"
  echo "cuentan como carga externa."
  exit 1
fi
echo "OK: sin CDNs ni cargas externas (navegación externa permitida)"
