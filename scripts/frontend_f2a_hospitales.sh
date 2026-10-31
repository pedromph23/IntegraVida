#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

echo "▶ 1. Extender frontend/views/public.py con hospitales"

python3 - << 'PY'
from pathlib import Path
p = Path("frontend/views/public.py")
text = p.read_text(encoding="utf-8")

# ── Añadir imports si faltan ──
if "from django.utils import timezone" not in text:
    needle = "from django.views.decorators.http import require_GET"
    text = text.replace(needle, "from django.utils import timezone\n" + needle, 1)

if "from django.http import Http404" not in text and "from django.http import Http404" not in text.split("from django.shortcuts import")[0]:
    # Http404 se importa dentro de design_system, moverlo arriba
    needle = "from django.conf import settings"
    text = text.replace(needle, "from django.http import Http404\n" + needle, 1)

# ── Añadir vistas ──
if "def hospitals_list(" not in text:
    text = text.rstrip() + '''


@require_GET
def hospitals_list(request):
    """Lista pública de hospitales con filtros server-side."""
    from apps.hospitales.views import _queryset_publico

    queryset = _queryset_publico()

    tipo = request.GET.get("tipo", "").strip()
    if tipo:
        queryset = queryset.filter(tipo=tipo)

    nivel = request.GET.get("nivel", "").strip()
    if nivel:
        queryset = queryset.filter(nivel=nivel)

    estado = request.GET.get("estado_operativo", "").strip()
    if estado:
        queryset = queryset.filter(estado_operativo=estado)

    municipio = request.GET.get("municipio", "").strip()
    if municipio:
        queryset = queryset.filter(municipio__nombre__icontains=municipio)

    servicio = request.GET.get("servicio", "").strip()
    if servicio:
        queryset = queryset.filter(
            servicios_through__servicio__codigo=servicio,
            servicios_through__disponible=True,
            servicios_through__servicio__activo=True,
        ).distinct()

    q = request.GET.get("q", "").strip()[:100]
    if q:
        from django.db.models import Q
        queryset = queryset.filter(
            Q(nombre__icontains=q) | Q(direccion__icontains=q)
        )

    queryset = queryset.order_by("nombre")[:60]
    ahora = timezone.now()

    from apps.hospitales.views import _serializar_hospital
    hospitales = [_serializar_hospital(h, ahora) for h in queryset]

    return render(request, "public/hospitals_list.html", {
        "hospitales": hospitales,
        "total": len(hospitales),
        "filtros": {
            "tipo": tipo,
            "nivel": nivel,
            "estado_operativo": estado,
            "municipio": municipio,
            "servicio": servicio,
            "q": q,
        },
        "opciones_tipo": [
            ("HOSPITAL", "Hospital"),
            ("CLINICA", "Clínica"),
            ("CENTRO_SALUD", "Centro de salud"),
            ("AMBULATORIO", "Ambulatorio"),
        ],
        "opciones_nivel": [
            ("NIVEL_I", "Nivel I"),
            ("NIVEL_II", "Nivel II"),
            ("NIVEL_III", "Nivel III"),
            ("NIVEL_IV", "Nivel IV"),
        ],
        "opciones_estado": [
            ("DISPONIBLE", "Disponible"),
            ("SATURADO", "Saturado"),
        ],
    })


@require_GET
def hospital_detail(request, codigo):
    """Detalle público de un hospital por código (slug)."""
    from apps.hospitales.views import _queryset_publico, _serializar_hospital
    try:
        hospital = _queryset_publico().get(codigo=codigo)
    except Hospital.DoesNotExist:
        raise Http404("Hospital no encontrado")

    return render(request, "public/hospital_detail.html", {
        "hospital": _serializar_hospital(hospital, timezone.now()),
    })
'''
    p.write_text(text, encoding="utf-8")
    print("OK: hospitals_list y hospital_detail añadidas")
else:
    print("ya aplicado: hospitals_list ya existe")
PY

echo ""
echo "▶ 2. Actualizar frontend/urls/public.py"
python3 - << 'PY'
from pathlib import Path
p = Path("frontend/urls/public.py")
text = p.read_text(encoding="utf-8")

if 'name="hospitals-list"' not in text:
    needle = '    path("design-system/", public.design_system, name="design-system"),'
    addition = (
        needle + "\n"
        '    path("hospitales/", public.hospitals_list, name="hospitals-list"),\n'
        '    path(\n'
        '        "hospitales/<slug:codigo>/",\n'
        '        public.hospital_detail,\n'
        '        name="hospital-detail",\n'
        '    ),'
    )
    if needle in text:
        text = text.replace(needle, addition, 1)
        p.write_text(text, encoding="utf-8")
        print("OK: URLs de hospitales añadidas")
    else:
        raise SystemExit("ERROR: marker design-system no encontrado")
else:
    print("ya aplicado: URLs de hospitales")
PY

echo ""
echo "▶ 3. Componente estado_recurso.html"
cat > templates/components/estado_recurso.html << 'EOF'
{% comment %}
Uso:
  {% include "components/estado_recurso.html" with label="UCI" recurso=hospital.recursos.uci %}
Parámetros:
  label   (str)  — nombre del recurso (UCI, Urgencia, etc.)
  recurso (dict) — {estado: 'disponible'|'no_disponible'|'sin_datos', actualizado_en: str|null}
{% endcomment %}
{% with estado=recurso.estado|default:"sin_datos" %}
<span class="badge
  {% if estado == 'disponible' %}badge-success
  {% elif estado == 'no_disponible' %}badge-danger
  {% else %}badge-info{% endif %}"
  {% if recurso.actualizado_en %}title="Actualizado: {{ recurso.actualizado_en }}"{% endif %}>
  <span aria-hidden="true">
    {% if estado == 'disponible' %}✓{% elif estado == 'no_disponible' %}✗{% else %}—{% endif %}
  </span>
  <span class="ml-1">{{ label }}</span>
</span>
{% endwith %}
EOF

echo "OK: estado_recurso.html creado"

echo ""
echo "▶ 4. Componente hospital_card.html"
cat > templates/components/hospital_card.html << 'EOF'
{% comment %}
Uso:
  {% include "components/hospital_card.html" with hospital=hospital %}
Parámetros:
  hospital (dict) — salida de _serializar_hospital() del backend
{% endcomment %}
<article class="card card-hover p-5 flex flex-col h-full">
  <header class="mb-3">
    <h2 class="text-lg font-semibold text-primary leading-tight">
      <a href="{% url 'public:hospital-detail' codigo=hospital.codigo %}">
        {{ hospital.nombre }}
      </a>
    </h2>
    <p class="text-sm text-text-muted mt-1">
      {{ hospital.tipo_texto }} · {{ hospital.nivel_texto }}
    </p>
  </header>

  <div class="text-sm text-text space-y-1 flex-1">
    <p>📍 {{ hospital.direccion }}</p>
    {% if hospital.municipio or hospital.parroquia %}
      <p class="text-text-muted">
        {% if hospital.parroquia %}{{ hospital.parroquia }}{% endif %}
        {% if hospital.parroquia and hospital.municipio %}, {% endif %}
        {% if hospital.municipio %}{{ hospital.municipio }}{% endif %}
      </p>
    {% endif %}
    {% if hospital.telefono_publico %}
      <p>📞 <a href="tel:{{ hospital.telefono_publico }}" class="underline">{{ hospital.telefono_publico }}</a></p>
    {% endif %}
  </div>

  <div class="mt-4 pt-3 border-t" style="border-color: color-mix(in srgb, var(--color-text) 10%, transparent);">
    <div class="flex flex-wrap gap-1.5">
      {% include "components/estado_recurso.html" with label="UCI" recurso=hospital.recursos.uci %}
      {% include "components/estado_recurso.html" with label="Urgencia" recurso=hospital.recursos.urgencia %}
      {% include "components/estado_recurso.html" with label="Quirófano" recurso=hospital.recursos.quirofano %}
      {% include "components/estado_recurso.html" with label="Hospitalización" recurso=hospital.recursos.hospitalizacion %}
    </div>
    {% if hospital.estado_operativo %}
      <div class="mt-2">
        <span class="badge {% if hospital.estado_operativo == 'DISPONIBLE' %}badge-success{% elif hospital.estado_operativo == 'SATURADO' %}badge-warning{% else %}badge-info{% endif %}">
          {{ hospital.estado_operativo_texto }}
        </span>
      </div>
    {% endif %}
  </div>
</article>
EOF

echo "OK: hospital_card.html creado"

echo ""
echo "▶ 5. Template hospitals_list.html"
cat > templates/public/hospitals_list.html << 'EOF'
{% extends "base/base_public.html" %}

{% block title %}Hospitales y centros de salud — IntegraVida{% endblock %}

{% block content %}
<section class="mx-auto max-w-7xl px-4 py-8">

  <header class="mb-6">
    <nav aria-label="Migas de pan" class="text-sm mb-2">
      <a href="{% url 'public:home' %}" class="text-text-muted hover:text-primary">← Inicio</a>
    </nav>
    <h1 class="text-3xl font-bold text-primary">Hospitales y centros de salud</h1>
    <p class="text-text-muted mt-1">
      {{ total }} centro{{ total|pluralize }} activo{{ total|pluralize }}.
      Solo se muestran datos públicos autorizados.
    </p>
  </header>

  <form method="get" class="card p-4 mb-6" aria-label="Filtros de hospitales">
    <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
      <div>
        <label for="f-q" class="block text-sm font-medium text-text mb-1">Buscar</label>
        <input type="search" id="f-q" name="q" value="{{ filtros.q }}"
               placeholder="Nombre o dirección" class="input">
      </div>
      <div>
        <label for="f-tipo" class="block text-sm font-medium text-text mb-1">Tipo</label>
        <select id="f-tipo" name="tipo" class="input">
          <option value="">Todos</option>
          {% for v, l in opciones_tipo %}
            <option value="{{ v }}" {% if v == filtros.tipo %}selected{% endif %}>{{ l }}</option>
          {% endfor %}
        </select>
      </div>
      <div>
        <label for="f-nivel" class="block text-sm font-medium text-text mb-1">Nivel</label>
        <select id="f-nivel" name="nivel" class="input">
          <option value="">Todos</option>
          {% for v, l in opciones_nivel %}
            <option value="{{ v }}" {% if v == filtros.nivel %}selected{% endif %}>{{ l }}</option>
          {% endfor %}
        </select>
      </div>
      <div>
        <label for="f-estado" class="block text-sm font-medium text-text mb-1">Estado</label>
        <select id="f-estado" name="estado_operativo" class="input">
          <option value="">Todos</option>
          {% for v, l in opciones_estado %}
            <option value="{{ v }}" {% if v == filtros.estado_operativo %}selected{% endif %}>{{ l }}</option>
          {% endfor %}
        </select>
      </div>
      <div>
        <label for="f-municipio" class="block text-sm font-medium text-text mb-1">Municipio</label>
        <input type="text" id="f-municipio" name="municipio" value="{{ filtros.municipio }}"
               placeholder="Nombre del municipio" class="input">
      </div>
      <div class="flex items-end gap-2">
        <button type="submit" class="btn btn-primary w-full">Filtrar</button>
        {% if filtros.q or filtros.tipo or filtros.nivel or filtros.estado_operativo or filtros.municipio %}
          <a href="{% url 'public:hospitals-list' %}" class="btn btn-ghost">Limpiar</a>
        {% endif %}
      </div>
    </div>
  </form>

  {% if hospitales %}
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {% for hospital in hospitales %}
        {% include "components/hospital_card.html" with hospital=hospital %}
      {% endfor %}
    </div>
  {% else %}
    {% include "components/empty-state.html" with icon="🏥" title="Sin resultados" description="No hay hospitales que coincidan con tu búsqueda." action_label="Ver todos" action_url="/hospitales/" %}
  {% endif %}

</section>
{% endblock %}
EOF

echo "OK: hospitals_list.html creado"

echo ""
echo "▶ 6. Template hospital_detail.html"
cat > templates/public/hospital_detail.html << 'EOF'
{% extends "base/base_public.html" %}

{% block title %}{{ hospital.nombre }} — IntegraVida{% endblock %}

{% block content %}
<article class="mx-auto max-w-4xl px-4 py-8">

  <nav aria-label="Migas de pan" class="text-sm mb-4">
    <a href="{% url 'public:home' %}" class="text-text-muted hover:text-primary">Inicio</a>
    <span class="text-text-muted mx-1">/</span>
    <a href="{% url 'public:hospitals-list' %}" class="text-text-muted hover:text-primary">Hospitales</a>
    <span class="text-text-muted mx-1">/</span>
    <span class="text-text">{{ hospital.nombre }}</span>
  </nav>

  <header class="mb-6">
    <h1 class="text-3xl font-bold text-primary">{{ hospital.nombre }}</h1>
    <p class="text-text-muted mt-1">
      {{ hospital.tipo_texto }} · {{ hospital.nivel_texto }}
      {% if hospital.estado_operativo %}
        · <span class="badge {% if hospital.estado_operativo == 'DISPONIBLE' %}badge-success{% elif hospital.estado_operativo == 'SATURADO' %}badge-warning{% else %}badge-info{% endif %}">{{ hospital.estado_operativo_texto }}</span>
      {% endif %}
    </p>
  </header>

  <div class="grid md:grid-cols-2 gap-6">

    <section class="card p-5">
      <h2 class="text-lg font-semibold mb-3">Ubicación y contacto</h2>
      <dl class="space-y-2 text-sm">
        <div>
          <dt class="text-text-muted">Dirección</dt>
          <dd>{{ hospital.direccion }}</dd>
        </div>
        {% if hospital.referencia_lugar %}
          <div>
            <dt class="text-text-muted">Referencia</dt>
            <dd>{{ hospital.referencia_lugar }}</dd>
          </div>
        {% endif %}
        {% if hospital.municipio or hospital.parroquia %}
          <div>
            <dt class="text-text-muted">Ubicación administrativa</dt>
            <dd>
              {% if hospital.parroquia %}{{ hospital.parroquia }}{% endif %}
              {% if hospital.parroquia and hospital.municipio %}, {% endif %}
              {% if hospital.municipio %}{{ hospital.municipio }}{% endif %}
            </dd>
          </div>
        {% endif %}
        {% if hospital.telefono_publico %}
          <div>
            <dt class="text-text-muted">Teléfono</dt>
            <dd><a href="tel:{{ hospital.telefono_publico }}" class="underline text-primary">{{ hospital.telefono_publico }}</a></dd>
          </div>
        {% endif %}
        {% if hospital.correo_publico %}
          <div>
            <dt class="text-text-muted">Correo</dt>
            <dd><a href="mailto:{{ hospital.correo_publico }}" class="underline text-primary">{{ hospital.correo_publico }}</a></dd>
          </div>
        {% endif %}
      </dl>
    </section>

    <section class="card p-5">
      <h2 class="text-lg font-semibold mb-3">Disponibilidad de recursos</h2>
      <p class="text-xs text-text-muted mb-3">
        Estado agregado. Datos desactualizados (&gt; 2h) se muestran como "sin datos".
      </p>
      <div class="space-y-2">
        {% include "components/estado_recurso.html" with label="UCI" recurso=hospital.recursos.uci %}
        {% include "components/estado_recurso.html" with label="Urgencias" recurso=hospital.recursos.urgencia %}
        {% include "components/estado_recurso.html" with label="Quirófano" recurso=hospital.recursos.quirofano %}
        {% include "components/estado_recurso.html" with label="Hospitalización" recurso=hospital.recursos.hospitalizacion %}
      </div>
    </section>

    {% if hospital.servicios %}
      <section class="card p-5 md:col-span-2">
        <h2 class="text-lg font-semibold mb-3">Servicios disponibles</h2>
        <div class="flex flex-wrap gap-2">
          {% for s in hospital.servicios %}
            <span class="badge {% if s.disponible %}badge-success{% else %}badge-info{% endif %}">
              {{ s.nombre }}{% if not s.disponible %} (no disponible){% endif %}
            </span>
          {% endfor %}
        </div>
      </section>
    {% endif %}

  </div>

  <div class="mt-8 pt-6 border-t" style="border-color: color-mix(in srgb, var(--color-text) 10%, transparent);">
    <a href="{% url 'public:hospitals-list' %}" class="btn btn-ghost">← Volver a la lista</a>
  </div>

</article>
{% endblock %}
EOF

echo "OK: hospital_detail.html creado"

echo ""
echo "▶ 7. Actualizar home.html con enlace a hospitales"
python3 - << 'PY'
from pathlib import Path
p = Path("templates/public/home.html")
text = p.read_text(encoding="utf-8")

# Reemplazar el link externo /api/publico/hospitales/ por /hospitales/
old = '<a href="/api/publico/hospitales/" class="btn btn-ghost">'
new = '<a href="/hospitales/" class="btn btn-ghost">'

if old in text:
    text = text.replace(old, new, 1)
    p.write_text(text, encoding="utf-8")
    print("OK: home.html apunta a /hospitales/")
elif '/hospitales/' in text:
    print("ya aplicado: home.html")
else:
    print("NOTA: no se encontró el link exacto, verificar manualmente")
PY

echo ""
echo "▶ 8. Rebuild CSS (nuevas clases en templates)"
NODE_ENV=production npx tailwindcss \
  -i ./static/css/src/main.css \
  -o ./static/css/dist/main.css \
  --minify
echo "CSS gzip: $(gzip -c static/css/dist/main.css | wc -c) bytes"

echo ""
echo "▶ 9. Anti-CDN"
bash scripts/check-no-cdn.sh

echo ""
echo "▶ 10. Django check"
python3 manage.py check

echo ""
echo "▶ 11. Tests backend existentes"
python3 manage.py test apps.configuracion frontend -v 1 2>&1 | tail -4

echo ""
echo "▶ 12. Smoke manual de las rutas nuevas"
pkill -f "manage.py runserver" 2>/dev/null || true
sleep 1
python3 manage.py runserver 0.0.0.0:8000 --noreload &> /tmp/rs_f2a.log &
RS_PID=$!
sleep 3
echo "GET /hospitales/       → $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/hospitales/)"
echo "GET /hospitales/no-existe/ → $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/hospitales/no-existe/)"
kill $RS_PID 2>/dev/null; wait $RS_PID 2>/dev/null || true

echo ""
echo "✅ F2.a — Hospitales implementados"
