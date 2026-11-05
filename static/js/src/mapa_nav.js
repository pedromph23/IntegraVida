/**
 * Mapa navegador con OSRM local + navegación turn-by-turn en tiempo real.
 * Solo se ejecuta en /panel/mapa/.
 */
import L from 'leaflet';

const TIPO_ES = {
  'turn': 'Gira', 'new name': 'Continúa', 'end of road': 'Al final de la vía',
  'continue': 'Continúa', 'arrive': 'Has llegado', 'depart': 'Comienza',
  'merge': 'Incorpórate', 'on ramp': 'Toma la rampa', 'off ramp': 'Sal por la rampa',
  'fork': 'En la bifurcación', 'roundabout': 'En la rotonda', 'rotary': 'En la rotonda',
  'exit roundabout': 'Sal de la rotonda', 'exit rotary': 'Sal de la rotonda',
};
const MOD_ES = {
  'uturn': 'y da la vuelta', 'sharp right': 'fuerte a la derecha', 'right': 'a la derecha',
  'slight right': 'ligeramente a la derecha', 'straight': 'recto',
  'slight left': 'ligeramente a la izquierda', 'left': 'a la izquierda',
  'sharp left': 'fuerte a la izquierda',
};

// ── Estado global ──────────────────────────────────────────────
let mapa = null;
let markers = {};
let markerUsuario = null;
let ultimaUbicacion = null;
let vozActiva = false;
let recognition = null;

// Estado de navegación activa
let rutaActual = null;
let pasoActual = 0;
let watchId = null;
let navegacionActiva = false;
let ultimoPasoAnunciado = -1;
let polylineRuta = null;

// ── Helpers ────────────────────────────────────────────────────
function instruccionEs(step) {
  const tipo = TIPO_ES[step.maneuver.type] || step.maneuver.type;
  const mod = MOD_ES[step.maneuver.modifier] || '';
  const calle = step.name ? ` en ${step.name}` : '';
  return `${tipo} ${mod}${calle}`.trim();
}

function formatearDistancia(m) {
  if (m < 1000) return `${Math.round(m / 10) * 10} m`;
  return `${(m / 1000).toFixed(1)} km`;
}

function formatearTiempo(seg) {
  if (seg < 60) return '<1 min';
  const min = Math.round(seg / 60);
  if (min < 60) return `${min} min`;
  const h = Math.floor(min / 60);
  const m = min % 60;
  return `${h}h ${m}m`;
}

function iconoParaPaso(step) {
  if (!step || !step.maneuver) return '●';
  const mod = step.maneuver.modifier || '';
  const type = step.maneuver.type || '';
  if (type === 'arrive') return '⚑';
  if (type === 'roundabout' || type === 'rotary') return '⟳';
  if (mod === 'right' || mod === 'sharp right') return '↱';
  if (mod === 'left' || mod === 'sharp left') return '↰';
  if (mod === 'slight right') return '↗';
  if (mod === 'slight left') return '↖';
  if (mod === 'uturn') return '↺';
  return '↑';
}

function hablar(texto) {
  if (!('speechSynthesis' in window)) return;
  const u = new SpeechSynthesisUtterance(texto);
  u.lang = 'es-VE';
  u.rate = 1.0;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(u);
}

function mostrarEstado(msg) {
  const el = document.getElementById('estado-voz');
  if (el) el.textContent = msg;
}

// ── Init ───────────────────────────────────────────────────────
function init() {
  const el = document.getElementById('mapa-nav');
  if (!el) return;

  let puntos = [];
  try { puntos = JSON.parse(el.dataset.puntos || '[]'); } catch (e) { puntos = []; }

  mapa = L.map('mapa-nav', {
    center: [10.4806, -66.9036], zoom: 12, scrollWheelZoom: true,
  });

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap', maxZoom: 19,
  }).addTo(mapa);

  puntos.forEach((p) => agregarPunto(p));
  if (puntos.length > 0) {
    mapa.fitBounds(L.latLngBounds(puntos.map((p) => [p.lat, p.lng])), { padding: [40, 40] });
  }
  renderizarLista(puntos);

  document.querySelectorAll('.js-filtro').forEach((chk) => chk.addEventListener('change', aplicarFiltros));
  document.getElementById('btn-centrar')?.addEventListener('click', centrarEnMi);
  document.getElementById('btn-cerrar-ruta')?.addEventListener('click', detenerNavegacion);
  document.getElementById('btn-voz')?.addEventListener('click', toggleVoz);
}

// ── Marcadores ────────────────────────────────────────────────
function agregarPunto(p) {
  const color = { HOSPITAL: '#2b6cb0', REFUGIO: '#2f855a', emergencia: '#c53030', punto: '#d69e2e' }[p.categoria] || '#4a5568';
  const icon = L.divIcon({
    className: 'iv-marker',
    html: `<div style="width:16px;height:16px;border-radius:50%;background:${color};border:2px solid #fff;box-shadow:0 1px 3px rgba(0,0,0,.4);"></div>`,
    iconSize: [16, 16], iconAnchor: [8, 8],
  });
  const marker = L.marker([p.lat, p.lng], { icon }).addTo(mapa);
  const popup = document.createElement('div');
  popup.innerHTML = `
    <strong>${p.titulo}</strong><br>
    <span style="font-size:11px;color:#666">${p.subtitulo || ''}</span><br>
    <button class="btn-ir" style="margin-top:6px;padding:4px 10px;background:#7a1f2b;color:#fff;border-radius:6px;border:none;cursor:pointer;font-size:12px">Ir aquí</button>
    <a href="${p.url}" style="display:inline-block;margin-left:6px;font-size:12px;color:#7a1f2b">Ver ficha</a>
  `;
  marker.bindPopup(popup);
  marker.on('popupopen', () => {
    popup.querySelector('.btn-ir')?.addEventListener('click', () => navegarA(p));
  });
  markers[p.id] = { data: p, marker };
}

function renderizarLista(puntos) {
  const ul = document.getElementById('lista-destinos');
  if (!ul) return;
  ul.innerHTML = '';
  puntos.forEach((p) => {
    const li = document.createElement('li');
    li.dataset.categoria = p.categoria;
    li.className = 'cursor-pointer rounded px-2 py-1 hover:bg-surface flex items-center justify-between gap-2';
    li.innerHTML = `<span class="truncate">${p.titulo}</span><button type="button" class="text-xs text-primary hover:underline shrink-0">Ir →</button>`;
    li.querySelector('button').addEventListener('click', () => navegarA(p));
    li.addEventListener('click', () => { mapa.setView([p.lat, p.lng], 16); markers[p.id].marker.openPopup(); });
    ul.appendChild(li);
  });
}

function aplicarFiltros() {
  const activos = Array.from(document.querySelectorAll('.js-filtro:checked')).map((c) => c.value);
  Object.values(markers).forEach(({ data, marker }) => {
    const match = activos.includes(data.categoria) || activos.includes(data.tipo);
    if (match && !mapa.hasLayer(marker)) marker.addTo(mapa);
    if (!match && mapa.hasLayer(marker)) mapa.removeLayer(marker);
  });
  document.querySelectorAll('#lista-destinos li').forEach((li) => {
    li.style.display = activos.includes(li.dataset.categoria) ? '' : 'none';
  });
}

// ── Marcador del usuario ──────────────────────────────────────
function actualizarMarkerUsuario(lat, lng, recenter) {
  ultimaUbicacion = { lat, lng };
  if (markerUsuario) mapa.removeLayer(markerUsuario);
  markerUsuario = L.marker([lat, lng], {
    icon: L.divIcon({
      className: 'iv-marker-user',
      html: '<div style="width:20px;height:20px;border-radius:50%;background:#4285f4;border:3px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,.3);"></div>',
      iconSize: [20, 20], iconAnchor: [10, 10],
    }),
    zIndexOffset: 1000,
  }).addTo(mapa);
  if (recenter) mapa.panTo([lat, lng], { animate: true, duration: 0.5 });
}

function marcarUbicacionManual(lat, lng) {
  actualizarMarkerUsuario(lat, lng, true);
}

function activarGPS(callback) {
  if (!navigator.geolocation) { callback(false); return; }
  navigator.geolocation.getCurrentPosition(
    (pos) => { actualizarMarkerUsuario(pos.coords.latitude, pos.coords.longitude, true); callback(true); },
    (err) => {
      let razon = 'desconocida';
      if (err.code === err.PERMISSION_DENIED) razon = 'permiso denegado';
      else if (err.code === err.POSITION_UNAVAILABLE) razon = 'posición no disponible';
      else if (err.code === err.TIMEOUT) razon = 'timeout';
      console.warn('GPS:', razon, err);
      mostrarEstado(`GPS no disponible (${razon}). Puedes hacer clic en el mapa para indicar tu posición.`);
      callback(false);
    },
    { enableHighAccuracy: false, timeout: 10000, maximumAge: 60000 },
  );
}

function activarClickMapa(destinoPendiente) {
  mostrarEstado('Haz clic en el mapa para indicar tu posición actual.');
  mapa.getContainer().style.cursor = 'crosshair';
  const handler = (e) => {
    mapa.off('click', handler);
    mapa.getContainer().style.cursor = '';
    marcarUbicacionManual(e.latlng.lat, e.latlng.lng);
    mostrarEstado('');
    if (destinoPendiente) navegarA(destinoPendiente);
  };
  mapa.on('click', handler);
}

function centrarEnMi() {
  mostrarEstado('Obteniendo tu ubicación...');
  activarGPS((ok) => {
    if (ok) { mostrarEstado(''); return; }
    activarClickMapa(null);
  });
}

// ── Navegación ────────────────────────────────────────────────
function navegarA(p) {
  if (!ultimaUbicacion) {
    mostrarEstado('Activando GPS...');
    activarGPS((ok) => {
      if (ok) navegarA(p);
      else activarClickMapa(p);
    });
    return;
  }

  mostrarEstado(`Calculando ruta hacia ${p.titulo}...`);
  const url = `/panel/api/ruta/?origin_lat=${ultimaUbicacion.lat}&origin_lng=${ultimaUbicacion.lng}&dest_lat=${p.lat}&dest_lng=${p.lng}`;

  fetch(url, { credentials: 'same-origin' })
    .then((r) => r.json())
    .then((data) => {
      if (data.error) {
        mostrarEstado('Error: ' + data.error);
        hablar('No pude calcular la ruta.');
        return;
      }
      iniciarNavegacion(data, p);
    })
    .catch((err) => {
      mostrarEstado('Error de red al consultar el motor de rutas.');
      console.error(err);
    });
}

function iniciarNavegacion(data, destino) {
  // Detener navegación previa si existe
  if (navegacionActiva) detenerNavegacion(true);

  rutaActual = {
    coords: data.routes[0].geometry.coordinates.map((c) => [c[1], c[0]]),
    pasos: data.routes[0].legs[0].steps,
    destino: destino,
    distancia: data.routes[0].distance,
    duracion: data.routes[0].duration,
  };
  pasoActual = 0;
  navegacionActiva = true;
  ultimoPasoAnunciado = -1;

  // Dibujar ruta
  if (polylineRuta) mapa.removeLayer(polylineRuta);
  polylineRuta = L.polyline(rutaActual.coords, { color: '#7a1f2b', weight: 6, opacity: 0.85 }).addTo(mapa);
  mapa.fitBounds(polylineRuta.getBounds(), { padding: [40, 40] });

  // Mostrar panel
  document.getElementById('panel-ruta').classList.remove('hidden');
  actualizarPanel();

  // Iniciar tracking GPS
  iniciarWatchPosition();

  // Anuncio inicial
  const km = (rutaActual.distancia / 1000).toFixed(1);
  const min = Math.round(rutaActual.duracion / 60);
  hablar(`Navegación iniciada hacia ${destino.titulo}. Distancia ${km} kilómetros, aproximadamente ${min} minutos.`);
  mostrarEstado('');
}

function iniciarWatchPosition() {
  if (!navigator.geolocation) {
    mostrarEstado('GPS no disponible. Ruta visible pero sin seguimiento.');
    return;
  }
  if (watchId !== null) navigator.geolocation.clearWatch(watchId);
  watchId = navigator.geolocation.watchPosition(
    (pos) => {
      if (!navegacionActiva) return;
      actualizarMarkerUsuario(pos.coords.latitude, pos.coords.longitude, false);
      verificarAvancePaso(pos.coords.latitude, pos.coords.longitude);
      actualizarPanel();
    },
    (err) => {
      console.warn('GPS watch:', err);
      mostrarEstado('GPS sin señal.');
    },
    { enableHighAccuracy: true, timeout: 10000, maximumAge: 3000 },
  );
}

function verificarAvancePaso(lat, lng) {
  if (!rutaActual || pasoActual >= rutaActual.pasos.length - 1) return;

  const siguiente = rutaActual.pasos[pasoActual + 1];
  const [sLng, sLat] = siguiente.maneuver.location;
  const distancia = L.latLng(lat, lng).distanceTo(L.latLng(sLat, sLng));

  // Avanzar al siguiente paso cuando estamos a <20m del punto de giro
  if (distancia < 20) {
    pasoActual++;
    console.log(`→ Paso ${pasoActual}/${rutaActual.pasos.length - 1}`);
  }
}

function actualizarPanel() {
  if (!rutaActual) return;

  const proximo = rutaActual.pasos[pasoActual + 1];

  if (!proximo) {
    // Llegada
    document.getElementById('nav-icono').textContent = '⚑';
    document.getElementById('nav-texto').textContent = 'Has llegado a tu destino';
    document.getElementById('nav-subtexto').textContent = rutaActual.destino.titulo;
    document.getElementById('nav-distancia').textContent = '0 m';
    document.getElementById('nav-distancia-restante').textContent = '0 m';
    document.getElementById('nav-tiempo-restante').textContent = '0 min';
    if (ultimoPasoAnunciado !== -2) {
      hablar('Has llegado a tu destino.');
      ultimoPasoAnunciado = -2;
    }
    return;
  }

  const instruccion = instruccionEs(proximo);
  const [pLng, pLat] = proximo.maneuver.location;

  let distancia = 0;
  if (ultimaUbicacion) {
    distancia = L.latLng(ultimaUbicacion.lat, ultimaUbicacion.lng).distanceTo(L.latLng(pLat, pLng));
  }

  // Actualizar panel
  document.getElementById('nav-icono').textContent = iconoParaPaso(proximo);
  document.getElementById('nav-texto').textContent = instruccion;
  document.getElementById('nav-subtexto').textContent = proximo.name || '';
  document.getElementById('nav-distancia').textContent = formatearDistancia(distancia);

  // Distancia y tiempo restantes
  const restantes = rutaActual.pasos.slice(pasoActual).reduce((sum, p) => sum + p.distance, 0);
  document.getElementById('nav-distancia-restante').textContent = formatearDistancia(restantes);
  const duracionRestante = rutaActual.pasos.slice(pasoActual).reduce((sum, p) => sum + p.duration, 0);
  document.getElementById('nav-tiempo-restante').textContent = formatearTiempo(duracionRestante);

  // Lista de próximos 3 pasos
  const ol = document.getElementById('pasos-ruta');
  ol.innerHTML = '';
  for (let i = pasoActual + 1; i < Math.min(pasoActual + 4, rutaActual.pasos.length); i++) {
    const p = rutaActual.pasos[i];
    const li = document.createElement('li');
    li.className = 'flex gap-2 text-text-muted';
    li.innerHTML = `
      <span class="font-mono text-xs shrink-0">${iconoParaPaso(p)}</span>
      <span class="flex-1 truncate">${instruccionEs(p)}</span>
    `;
    ol.appendChild(li);
  }

  // Anuncio de voz al acercarse a un giro
  if (distancia < 200 && ultimoPasoAnunciado !== pasoActual + 1 && pasoActual + 1 !== -2) {
    const seg = Math.round(distancia / 10) * 10;
    if (seg > 0) {
      hablar(`En ${seg} metros, ${instruccion}.`);
      ultimoPasoAnunciado = pasoActual + 1;
    }
  }
}

function detenerNavegacion(silencioso) {
  navegacionActiva = false;
  if (watchId !== null) {
    navigator.geolocation.clearWatch(watchId);
    watchId = null;
  }
  if (polylineRuta) {
    mapa.removeLayer(polylineRuta);
    polylineRuta = null;
  }
  rutaActual = null;
  pasoActual = 0;
  ultimoPasoAnunciado = -1;
  document.getElementById('panel-ruta').classList.add('hidden');
  if (!silencioso) {
    hablar('Navegación detenida.');
    mostrarEstado('');
  }
}

// ── Voz (comandos) ────────────────────────────────────────────
function toggleVoz() {
  if (vozActiva) { detenerVoz(); return; }
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    mostrarEstado('Tu navegador no soporta reconocimiento de voz. Usa Chrome o Edge.');
    return;
  }
  recognition = new SR();
  recognition.lang = 'es-VE';
  recognition.interimResults = false;
  recognition.onstart = () => {
    vozActiva = true;
    const btn = document.getElementById('btn-voz');
    btn.textContent = '⏹ Detener';
    btn.classList.remove('iv-cta-bg');
    btn.classList.add('bg-danger', 'text-white');
    mostrarEstado('Escuchando... di "llévame al hospital central".');
  };
  recognition.onresult = (event) => {
    const texto = event.results[0][0].transcript;
    mostrarEstado(`Escuché: "${texto}"`);
    procesarComando(texto);
  };
  recognition.onerror = (event) => { mostrarEstado('Error de voz: ' + event.error); detenerVoz(); };
  recognition.onend = () => detenerVoz();
  recognition.start();
}

function detenerVoz() {
  vozActiva = false;
  const btn = document.getElementById('btn-voz');
  if (btn) {
    btn.textContent = '🎤 Hablar';
    btn.classList.add('iv-cta-bg');
    btn.classList.remove('bg-danger');
  }
  if (recognition) { try { recognition.stop(); } catch (e) {} recognition = null; }
}

function procesarComando(texto) {
  const t = texto.toLowerCase().trim();
  const patrones = [
    /(?:llévame|ir|vamos|llevar)\s+(?:al?|a la?)\s+(.+)/,
    /(?:dónde está|donde esta|busca|buscar|encuentra)\s+(.+)/,
    /(?:quiero ir a|necesito ir a)\s+(.+)/,
  ];
  let objetivo = null;
  for (const p of patrones) {
    const m = t.match(p);
    if (m) { objetivo = m[1].trim(); break; }
  }
  if (!objetivo) {
    mostrarEstado('No entendí. Di: "llévame al hospital X".');
    hablar('No entendí el comando.');
    return;
  }
  const candidatos = Object.values(markers).map((m) => m.data).filter((p) => p.titulo.toLowerCase().includes(objetivo));
  if (candidatos.length === 0) {
    mostrarEstado(`No encontré "${objetivo}".`);
    hablar(`No encontré ${objetivo}.`);
    return;
  }
  if (candidatos.length === 1) {
    const p = candidatos[0];
    mapa.setView([p.lat, p.lng], 16);
    markers[p.id].marker.openPopup();
    navegarA(p);
    return;
  }
  mostrarEstado(`Encontré ${candidatos.length} opciones. Elige una:`);
  const ul = document.getElementById('lista-destinos');
  ul.innerHTML = '';
  candidatos.forEach((p) => {
    const li = document.createElement('li');
    li.className = 'cursor-pointer rounded px-2 py-1 hover:bg-surface';
    li.textContent = p.titulo;
    li.addEventListener('click', () => navegarA(p));
    ul.appendChild(li);
  });
  hablar(`Encontré ${candidatos.length} opciones.`);
}

document.addEventListener('DOMContentLoaded', init);
