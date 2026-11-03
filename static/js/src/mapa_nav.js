/**
 * Mapa navegador con OSRM local + voz.
 * Solo se ejecuta en /panel/mapa/.
 */
import L from 'leaflet';

const TIPO_ES = {
  'turn': 'Gira',
  'new name': 'Continúa',
  'end of road': 'Al final de la vía',
  'continue': 'Continúa',
  'arrive': 'Has llegado',
  'depart': 'Comienza',
  'merge': 'Incorpórate',
  'on ramp': 'Toma la rampa',
  'off ramp': 'Sal por la rampa',
  'fork': 'En la bifurcación',
  'roundabout': 'En la rotonda',
  'rotary': 'En la rotonda',
  'exit roundabout': 'Sal de la rotonda',
  'exit rotary': 'Sal de la rotonda',
};
const MOD_ES = {
  'uturn': 'y da la vuelta',
  'sharp right': 'fuerte a la derecha',
  'right': 'a la derecha',
  'slight right': 'ligeramente a la derecha',
  'straight': 'recto',
  'slight left': 'ligeramente a la izquierda',
  'left': 'a la izquierda',
  'sharp left': 'fuerte a la izquierda',
};

function instruccionEs(step) {
  const tipo = TIPO_ES[step.maneuver.type] || step.maneuver.type;
  const mod = MOD_ES[step.maneuver.modifier] || '';
  const calle = step.name ? ` en ${step.name}` : '';
  const dist = step.distance > 1000
    ? `${(step.distance / 1000).toFixed(1)} km`
    : `${Math.round(step.distance)} m`;
  return { texto: `${tipo} ${mod}${calle}`.trim(), distancia: dist };
}

function hablar(texto) {
  if (!('speechSynthesis' in window)) return;
  const u = new SpeechSynthesisUtterance(texto);
  u.lang = 'es-VE';
  u.rate = 1.0;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(u);
}

let mapa = null;
let markers = {};
let polylines = [];
let markerUsuario = null;
let ultimaUbicacion = null;
let vozActiva = false;
let recognition = null;

function init() {
  const el = document.getElementById('mapa-nav');
  if (!el) return;

  let puntos = [];
  try { puntos = JSON.parse(el.dataset.puntos || '[]'); } catch (e) { puntos = []; }

  mapa = L.map('mapa-nav', {
    center: [10.4806, -66.9036],
    zoom: 12,
    scrollWheelZoom: true,
  });

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap',
    maxZoom: 19,
  }).addTo(mapa);

  puntos.forEach((p) => agregarPunto(p));
  if (puntos.length > 0) {
    mapa.fitBounds(L.latLngBounds(puntos.map((p) => [p.lat, p.lng])), { padding: [40, 40] });
  }
  renderizarLista(puntos);

  document.querySelectorAll('.js-filtro').forEach((chk) => {
    chk.addEventListener('change', aplicarFiltros);
  });
  document.getElementById('btn-centrar')?.addEventListener('click', centrarEnMi);
  document.getElementById('btn-cerrar-ruta')?.addEventListener('click', limpiarRuta);
  document.getElementById('btn-voz')?.addEventListener('click', toggleVoz);
}

function agregarPunto(p) {
  const color = {
    HOSPITAL: '#2b6cb0',
    REFUGIO: '#2f855a',
    emergencia: '#c53030',
    punto: '#d69e2e',
  }[p.categoria] || '#4a5568';

  const icon = L.divIcon({
    className: 'iv-marker',
    html: `<div style="width:16px;height:16px;border-radius:50%;background:${color};border:2px solid #fff;box-shadow:0 1px 3px rgba(0,0,0,.4);"></div>`,
    iconSize: [16, 16],
    iconAnchor: [8, 8],
  });

  const marker = L.marker([p.lat, p.lng], { icon }).addTo(mapa);

  const popup = document.createElement('div');
  popup.innerHTML = `
    <strong>${p.titulo}</strong><br>
    <span style="font-size:11px;color:#666">${p.subtitulo || ''}</span><br>
    <button class="btn-ir" style="margin-top:6px;padding:4px 10px;background:#7a1f2b;color:#fff;border-radius:6px;border:none;cursor:pointer;font-size:12px">
      Ir aquí
    </button>
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
    li.innerHTML = `
      <span class="truncate">${p.titulo}</span>
      <button type="button" class="text-xs text-primary hover:underline shrink-0">Ir →</button>
    `;
    li.querySelector('button').addEventListener('click', () => navegarA(p));
    li.addEventListener('click', () => {
      mapa.setView([p.lat, p.lng], 16);
      markers[p.id].marker.openPopup();
    });
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
      dibujarRuta(data, p);
    })
    .catch((err) => {
      mostrarEstado('Error de red al consultar el motor de rutas.');
      console.error(err);
    });
}

function dibujarRuta(data, destino) {
  limpiarRuta();
  const ruta = data.routes[0];
  const coords = ruta.geometry.coordinates.map((c) => [c[1], c[0]]);

  const linea = L.polyline(coords, { color: '#7a1f2b', weight: 6, opacity: 0.85 }).addTo(mapa);
  polylines.push(linea);
  mapa.fitBounds(linea.getBounds(), { padding: [40, 40] });

  const km = (ruta.distance / 1000).toFixed(1);
  const min = Math.round(ruta.duration / 60);
  document.getElementById('resumen-ruta').innerHTML =
    `<strong>${destino.titulo}</strong><br>${km} km · ${min} min aprox.`;

  const ol = document.getElementById('pasos-ruta');
  ol.innerHTML = '';
  ruta.legs[0].steps.forEach((s, i) => {
    const { texto, distancia } = instruccionEs(s);
    const li = document.createElement('li');
    li.className = 'flex gap-2 border-b border-border pb-1';
    li.innerHTML = `
      <span class="font-mono text-xs text-text-muted shrink-0">${i + 1}.</span>
      <span class="flex-1">${texto}</span>
      <span class="text-xs text-text-muted shrink-0">${distancia}</span>
    `;
    ol.appendChild(li);
  });

  document.getElementById('panel-ruta').classList.remove('hidden');
  hablar(`Ruta a ${destino.titulo}. Son ${km} kilómetros, aproximadamente ${min} minutos.`);
  mostrarEstado('');
}

function limpiarRuta() {
  polylines.forEach((p) => mapa.removeLayer(p));
  polylines = [];
  document.getElementById('panel-ruta')?.classList.add('hidden');
}

function activarGPS(callback) {
  if (!navigator.geolocation) { callback(false); return; }
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      marcarUbicacionManual(pos.coords.latitude, pos.coords.longitude);
      callback(true);
    },
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

function marcarUbicacionManual(lat, lng) {
  ultimaUbicacion = { lat: lat, lng: lng };
  if (markerUsuario) mapa.removeLayer(markerUsuario);
  markerUsuario = L.marker([lat, lng], {
    icon: L.divIcon({
      className: 'iv-marker-user',
      html: '<div style="width:18px;height:18px;border-radius:50%;background:#2b6cb0;border:3px solid #fff;box-shadow:0 0 8px rgba(43,108,176,.6);"></div>',
      iconSize: [18, 18],
      iconAnchor: [9, 9],
    }),
  }).addTo(mapa).bindPopup('Tu ubicación');
  mapa.setView([lat, lng], 16);
}

function activarClickMapa(destinoPendiente) {
  mostrarEstado('Haz clic en el mapa para indicar tu posición actual.');
  mapa.getContainer().style.cursor = 'crosshair';
  const handler = (e) => {
    mapa.off('click', handler);
    mapa.getContainer().style.cursor = '';
    marcarUbicacionManual(e.latlng.lat, e.latlng.lng);
    mostrarEstado('Posición establecida. Calculando ruta...');
    if (destinoPendiente) navegarA(destinoPendiente);
    else mostrarEstado('');
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
    mostrarEstado('Escuchando... di por ejemplo "llévame al hospital central".');
  };
  recognition.onresult = (event) => {
    const texto = event.results[0][0].transcript;
    mostrarEstado(`Escuché: "${texto}"`);
    procesarComando(texto);
  };
  recognition.onerror = (event) => {
    mostrarEstado('Error de voz: ' + event.error);
    detenerVoz();
  };
  recognition.onend = () => { detenerVoz(); };
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
  if (recognition) {
    try { recognition.stop(); } catch (e) {}
    recognition = null;
  }
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
  const candidatos = Object.values(markers).map((m) => m.data)
    .filter((p) => p.titulo.toLowerCase().includes(objetivo));
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

function mostrarEstado(msg) {
  const el = document.getElementById('estado-voz');
  if (el) el.textContent = msg;
}

document.addEventListener('DOMContentLoaded', init);
