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
