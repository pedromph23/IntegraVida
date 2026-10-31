#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

echo "▶ 1. Instalar postcss-import (para resolver leaflet.css)"
if ! npm ls postcss-import >/dev/null 2>&1; then
    npm install -D postcss-import@16.1.1
    echo "OK: postcss-import instalado"
else
    echo "ya instalado: postcss-import"
fi

echo ""
echo "▶ 2. Actualizar postcss.config.js"
cat > postcss.config.js << 'EOF'
export default {
  plugins: {
    'postcss-import': {},
    tailwindcss: {},
    autoprefixer: {},
    ...(process.env.NODE_ENV === 'production' ? { cssnano: {} } : {}),
  },
}
EOF
echo "OK: postcss.config.js actualizado"

echo ""
echo "▶ 3. Añadir vendor.css con leaflet"
cat > static/css/src/vendor.css << 'EOF'
/* Vendor CSS — dependencias npm que deben bundlearse localmente */

/* Leaflet 1.9.4 — estilos para el mapa (F2.e) */
@import "leaflet/dist/leaflet.css";

/* Override: Leaflet usa z-index alto por defecto; ajustar para no
   tapar modales y otros overlays del sistema de diseño. */
.leaflet-pane { z-index: 10; }
.leaflet-top, .leaflet-bottom { z-index: 20; }
.leaflet-container {
  background: var(--color-surface-raised);
  border-radius: 0.75rem;
}
EOF

# Añadir import al inicio de main.css si no está
python3 - << 'PY'
from pathlib import Path
p = Path("static/css/src/main.css")
text = p.read_text(encoding="utf-8")
if "@import './vendor.css';" not in text:
    text = "@import './vendor.css';\n" + text
    p.write_text(text, encoding="utf-8")
    print("OK: main.css importa vendor.css")
else:
    print("ya aplicado: main.css")
PY

echo ""
echo "▶ 4. Añadir TILE_SERVER_URL a settings.py"
python3 - << 'PY'
from pathlib import Path
p = Path("config/settings.py")
text = p.read_text(encoding="utf-8")
if "TILE_SERVER_URL" not in text:
    needle = 'FIELD_ENCRYPTION_KEY = os.environ.get("FIELD_ENCRYPTION_KEY", "")\n'
    addition = (
        needle
        + '\n# Servidor de tiles para Leaflet (F2.e).\n'
        + '# Default VACÍO = sin requests externos (mapa con marcadores sobre fondo neutro).\n'
        + '# En producción configurar p.ej. https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png\n'
        + 'TILE_SERVER_URL = os.environ.get("TILE_SERVER_URL", "")\n'
        + 'TILE_SERVER_ATTRIBUTION = os.environ.get(\n'
        + '    "TILE_SERVER_ATTRIBUTION", ""\n'
        + ')\n'
    )
    text = text.replace(needle, addition, 1)
    p.write_text(text, encoding="utf-8")
    print("OK: TILE_SERVER_URL + TILE_SERVER_ATTRIBUTION añadidos")
else:
    print("ya aplicado: TILE_SERVER_URL")

# Añadir TILE_SERVER_URL al context processor
p = Path("config/settings.py")
text = p.read_text(encoding="utf-8")
if "context_processors.map_config" not in text:
    needle = "        'context_processors': [\n"
    if needle in text:
        # Insertar un context processor custom al final de la lista
        # Buscar el cierre del bloque de context_processors
        import re
        m = re.search(
            r"(context_processors': \[\n(?:.*\n)*?)(\s+\],)",
            text,
        )
        if m:
            insert = "                'frontend.context_processors.map_config',\n"
            text = text[:m.end(1)] + insert + text[m.end(1):]
            p.write_text(text, encoding="utf-8")
            print("OK: context processor añadido a TEMPLATES")
        else:
            print("NOTA: no se pudo insertar context processor, revisar manualmente")
    else:
        print("NOTA: bloque context_processors no encontrado")
else:
    print("ya aplicado: context processor")
PY

echo ""
echo "▶ 5. Crear context_processor"
cat > frontend/context_processors.py << 'EOF'
"""Context processors del frontend."""
from django.conf import settings


def map_config(request):
    """Expone la config de Leaflet a los templates (F2.e)."""
    return {
        "TILE_SERVER_URL": settings.TILE_SERVER_URL,
        "TILE_SERVER_ATTRIBUTION": settings.TILE_SERVER_ATTRIBUTION,
    }
EOF
echo "OK: frontend/context_processors.py creado"

echo ""
echo "▶ 6. Crear maps.js"
cat > static/js/src/maps.js << 'EOF'
/**
 * Mapa Leaflet para las 3 listas del portal (F2.e).
 * Uso: elemento con id="map" y atributos data-markers y data-tile-server.
 * Carga lazy desde main.js.
 */
import L from 'leaflet';

function parseMarkers(el) {
  const raw = el.dataset.markers || '[]';
  try {
    return JSON.parse(raw);
  } catch (e) {
    console.warn('markers inválidos', e);
    return [];
  }
}

function markerColorForCategory(cat) {
  // Colores por categoría de emergencia o tipo de recurso
  const map = {
    INUNDACION: '#2b6cb0',
    INCENDIO: '#c53030',
    ACCIDENTE: '#d69e2e',
    DESLIZAMIENTO: '#7b341e',
    ESTRUCTURAL: '#4a5568',
    MEDICA: '#9c4221',
    VIAS: '#718096',
    VIOLENCIA: '#742a2a',
    SERVICIOS: '#2c5282',
    OTRA: '#4a5568',
    HOSPITAL: '#2b6cb0',
    REFUGIO: '#2f855a',
  };
  return map[cat] || '#4a5568';
}

function createMarker(markerData) {
  const color = markerColorForCategory(markerData.categoria);
  const icon = L.divIcon({
    className: 'iv-map-marker',
    html: `<div style="width:14px;height:14px;border-radius:50%;background:${color};border:2px solid #fff;box-shadow:0 1px 3px rgba(0,0,0,0.4);"></div>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  });

  const marker = L.marker(
    [markerData.lat, markerData.lng],
    { icon },
  );

  if (markerData.titulo) {
    const popupContent = document.createElement('div');
    const strong = document.createElement('strong');
    strong.textContent = markerData.titulo;
    popupContent.appendChild(strong);
    if (markerData.subtitulo) {
      const br = document.createElement('br');
      popupContent.appendChild(br);
      popupContent.appendChild(document.createTextNode(markerData.subtitulo));
    }
    if (markerData.url) {
      const br2 = document.createElement('br');
      popupContent.appendChild(br2);
      const link = document.createElement('a');
      link.href = markerData.url;
      link.textContent = 'Ver detalle →';
      popupContent.appendChild(link);
    }
    marker.bindPopup(popupContent);
  }

  return marker;
}

export function initMaps() {
  const el = document.getElementById('map');
  if (!el) return;

  const markers = parseMarkers(el);

  // Centro por defecto: Caracas si no hay markers
  let center = [10.4806, -66.9036];
  let zoom = 11;

  if (markers.length > 0) {
    const lats = markers.map((m) => m.lat);
    const lngs = markers.map((m) => m.lng);
    center = [
      (Math.min(...lats) + Math.max(...lats)) / 2,
      (Math.min(...lngs) + Math.max(...lngs)) / 2,
    ];
    zoom = markers.length === 1 ? 14 : 11;
  }

  const map = L.map(el, {
    center,
    zoom,
    scrollWheelZoom: false, // no bloquear el scroll de la página
  });

  const tileUrl = el.dataset.tileServer || '';
  const attribution = el.dataset.tileAttribution || '';

  if (tileUrl) {
    L.tileLayer(tileUrl, {
      attribution,
      maxZoom: 19,
    }).addTo(map);
  }
  // Si no hay tileUrl: mapa con fondo neutro (var --color-surface-raised)
  // y solo marcadores. Funciona offline sin requests externos.

  markers.forEach((m) => {
    if (typeof m.lat === 'number' && typeof m.lng === 'number') {
      createMarker(m).addTo(map);
    }
  });

  // Ajustar bounds si hay varios markers
  if (markers.length > 1) {
    const bounds = L.latLngBounds(markers.map((m) => [m.lat, m.lng]));
    map.fitBounds(bounds, { padding: [30, 30] });
  }

  // Re-calcular tamaño tras render (útil si el div estuvo hidden)
  setTimeout(() => map.invalidateSize(), 100);
}
EOF
echo "OK: maps.js creado"

echo ""
echo "▶ 7. Actualizar main.js — lazy import de maps"
python3 - << 'PY'
from pathlib import Path
p = Path("static/js/src/main.js")
text = p.read_text(encoding="utf-8")

if "initMaps" not in text:
    # Añadir al inicio del DOMContentLoaded
    needle = "document.addEventListener('DOMContentLoaded', () => {\n"
    addition = (
        "document.addEventListener('DOMContentLoaded', () => {\n"
        "  // Carga lazy de mapas: solo si existe #map en la página (F2.e)\n"
        "  if (document.getElementById('map')) {\n"
        "    import('./maps.js').then((mod) => {\n"
        "      mod.initMaps();\n"
        "    }).catch((err) => console.warn('maps.js error', err));\n"
        "  }\n"
        "  \n"
    )
    if needle in text:
        text = text.replace(needle, addition, 1)
        p.write_text(text, encoding="utf-8")
        print("OK: main.js lazy-importa maps.js")
    else:
        print("NOTA: DOMContentLoaded no encontrado")
else:
    print("ya aplicado: main.js")
PY

echo ""
echo "▶ 8. Actualizar vistas — pasar markers a templates"
python3 - << 'PY'
from pathlib import Path

# === 8.1 hospitals_list ===
p = Path("frontend/views/public.py")
text = p.read_text(encoding="utf-8")

if '"map_markers"' not in text or text.count('"map_markers"') < 3:
    # hospitals_list — añadir map_markers
    old = '''    from apps.hospitales.views import _serializar_hospital
    hospitales = [_serializar_hospital(h, ahora) for h in queryset]

    return render(request, "public/hospitals_list.html", {'''
    new = '''    from apps.hospitales.views import _serializar_hospital
    hospitales = [_serializar_hospital(h, ahora) for h in queryset]

    # Markers para el mapa (F2.e)
    map_markers = []
    for h in queryset:
        if h.ubicacion:
            map_markers.append({
                "lat": h.ubicacion.y,
                "lng": h.ubicacion.x,
                "titulo": h.nombre,
                "subtitulo": h.direccion,
                "url": f"/hospitales/{h.codigo}/",
                "categoria": "HOSPITAL",
            })

    return render(request, "public/hospitals_list.html", {
        "map_markers": map_markers,'''
    if old in text:
        text = text.replace(old, new, 1)
        print("OK: hospitals_list con map_markers")

    # shelters_list
    old = '''    from apps.refugios.views import _serializar_refugio
    refugios = [_serializar_refugio(r) for r in queryset]

    return render(request, "public/shelters_list.html", {'''
    new = '''    from apps.refugios.views import _serializar_refugio
    refugios = [_serializar_refugio(r) for r in queryset]

    # Markers para el mapa (F2.e)
    map_markers = []
    for r in queryset:
        if r.ubicacion:
            map_markers.append({
                "lat": r.ubicacion.y,
                "lng": r.ubicacion.x,
                "titulo": r.nombre,
                "subtitulo": r.direccion,
                "url": f"/refugios/{r.codigo}/",
                "categoria": "REFUGIO",
            })

    return render(request, "public/shelters_list.html", {
        "map_markers": map_markers,'''
    if old in text:
        text = text.replace(old, new, 1)
        print("OK: shelters_list con map_markers")

    # alerts_list
    old = '''    alertas = [_serializar_emergencia(e) for e in queryset]

    from apps.emergencias.models import Emergencia as EmergenciaModel
    return render(request, "public/alerts_list.html", {'''
    new = '''    alertas = [_serializar_emergencia(e) for e in queryset]

    # Markers para el mapa (F2.e)
    map_markers = []
    for e in queryset:
        if e.punto:
            map_markers.append({
                "lat": e.punto.y,
                "lng": e.punto.x,
                "titulo": e.titulo,
                "subtitulo": e.ubicacion_texto,
                "url": f"/alertas/{e.id}/",
                "categoria": e.categoria,
            })

    from apps.emergencias.models import Emergencia as EmergenciaModel
    return render(request, "public/alerts_list.html", {
        "map_markers": map_markers,'''
    if old in text:
        text = text.replace(old, new, 1)
        print("OK: alerts_list con map_markers")

    p.write_text(text, encoding="utf-8")
else:
    print("ya aplicado: vistas con map_markers")
PY

echo ""
echo "▶ 9. Insertar div#map en los 3 templates"
python3 - << 'PY'
from pathlib import Path
import json

def insert_map_before_placeholder(template_path, placeholder):
    p = Path(template_path)
    text = p.read_text(encoding="utf-8")
    if 'id="map"' in text:
        print(f"ya aplicado: {template_path}")
        return
    
    map_block = '''  {% if map_markers %}
    <section class="mb-6" aria-label="Mapa de resultados">
      <div id="map"
           data-markers='{{ map_markers|safe }}'
           data-tile-server="{{ TILE_SERVER_URL|default:'' }}"
           data-tile-attribution="{{ TILE_SERVER_ATTRIBUTION|default:'' }}"
           style="height: 400px; width: 100%;"
           class="rounded-xl overflow-hidden border"
           role="application"
           aria-label="Mapa con los resultados de la búsqueda">
      </div>
      <p class="text-xs text-text-muted mt-1">
        {{ map_markers|length }} punto{{ map_markers|length|pluralize }} en el mapa.
      </p>
    </section>
  {% endif %}

'''
    
    if placeholder in text:
        text = text.replace(placeholder, map_block + placeholder, 1)
        p.write_text(text, encoding="utf-8")
        print(f"OK: {template_path} +div#map")
    else:
        print(f"NOTA: no se encontró placeholder en {template_path}")

# Los templates usan `{% if hospitales %}` / `{% if refugios %}` / `{% if alertas %}`
insert_map_before_placeholder(
    "templates/public/hospitals_list.html",
    "  {% if hospitales %}\n",
)
insert_map_before_placeholder(
    "templates/public/shelters_list.html",
    "  {% if refugios %}\n",
)
insert_map_before_placeholder(
    "templates/public/alerts_list.html",
    "  {% if alertas %}\n",
)
PY

echo ""
echo "▶ 10. Rebuild CSS + JS"
NODE_ENV=production npx tailwindcss \
  -i ./static/css/src/main.css \
  -o ./static/css/dist/main.css \
  --minify
echo "CSS gzip: $(gzip -c static/css/dist/main.css | wc -c) bytes"

npx esbuild ./static/js/src/main.js --bundle --outfile=./static/js/dist/main.js --minify --sourcemap
echo "JS gzip:  $(gzip -c static/js/dist/main.js | wc -c) bytes"

echo ""
echo "▶ 11. Anti-CDN"
bash scripts/check-no-cdn.sh

echo ""
echo "▶ 12. Django check"
python3 manage.py check

echo ""
echo "▶ 13. BLOQUEO si tests fallan (§3.8)"
TEST_OUT=$(python3 manage.py test apps.configuracion frontend -v 1 2>&1 | tail -4)
echo "$TEST_OUT"
if ! echo "$TEST_OUT" | grep -q "^OK"; then
    echo ""
    echo "❌ ERROR: tests rojos. NO COMMITEAR."
    exit 1
fi
echo "✅ Tests OK, seguro para commit"

echo ""
echo "▶ 14. Smoke final"
pkill -f "manage.py runserver" 2>/dev/null || true
sleep 1
python3 manage.py runserver 0.0.0.0:8000 --noreload &> /tmp/rs_f2e.log &
RS_PID=$!
sleep 3

for path in / /hospitales/ /refugios/ /alertas/; do
    echo "$path → $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000$path)"
done

echo ""
echo "--- Leaflet CSS bundled ---"
grep -c "leaflet-container" static/css/dist/main.css || echo "0"
echo "--- Leaflet JS bundled ---"
grep -c "leaflet" static/js/dist/main.js || echo "0"

kill $RS_PID 2>/dev/null; wait $RS_PID 2>/dev/null || true

echo ""
echo "✅ F2.e — Mapas implementados"
echo "🎉 F2 COMPLETA — portal público con mapa Leaflet"
