#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

echo "▶ 1. Extender frontend/views/public.py con refugios"
python3 - << 'PY'
from pathlib import Path
p = Path("frontend/views/public.py")
text = p.read_text(encoding="utf-8")

if "def shelters_list(" not in text:
    text = text.rstrip() + '''


@require_GET
def shelters_list(request):
    """Lista pública de refugios con filtros server-side."""
    from apps.refugios.views import _queryset_publico

    queryset = _queryset_publico()

    tipo = request.GET.get("tipo", "").strip()
    if tipo:
        queryset = queryset.filter(tipo=tipo)

    estado = request.GET.get("estado_operativo", "").strip()
    if estado:
        queryset = queryset.filter(estado_operativo=estado)

    municipio = request.GET.get("municipio", "").strip()
    if municipio:
        queryset = queryset.filter(municipio__nombre__icontains=municipio)

    # Filtro de disponibilidad: refugios con capacidad libre > 0
    solo_con_lugar = request.GET.get("con_lugar") == "1"
    if solo_con_lugar:
        from django.db.models import F
        queryset = queryset.filter(capacidad_total__gt=F("ocupacion_actual"))

    q = request.GET.get("q", "").strip()[:100]
    if q:
        from django.db.models import Q
        queryset = queryset.filter(
            Q(nombre__icontains=q) | Q(direccion__icontains=q)
        )

    queryset = queryset.order_by("nombre")[:60]

    from apps.refugios.views import _serializar_refugio
    refugios = [_serializar_refugio(r) for r in queryset]

    return render(request, "public/shelters_list.html", {
        "refugios": refugios,
        "total": len(refugios),
        "filtros": {
            "tipo": tipo,
            "estado_operativo": estado,
            "municipio": municipio,
            "con_lugar": solo_con_lugar,
            "q": q,
        },
        "opciones_tipo": [
            ("REFUGIO", "Refugio"),
            ("CENTRO_ACOPIO", "Centro de acopio"),
            ("ALBERGUE_TEMPORAL", "Albergue temporal"),
            ("OTRO", "Otro"),
        ],
        "opciones_estado": [
            ("ACTIVO", "Activo"),
            ("LLENO", "Lleno"),
        ],
    })


@require_GET
def shelter_detail(request, codigo):
    """Detalle público de un refugio por código (slug)."""
    from apps.refugios.views import _queryset_publico, _serializar_refugio
    try:
        refugio = _queryset_publico().get(codigo=codigo)
    except Refugio.DoesNotExist:
        raise Http404("Refugio no encontrado")

    return render(request, "public/shelter_detail.html", {
        "refugio": _serializar_refugio(refugio),
    })
'''
    p.write_text(text, encoding="utf-8")
    print("OK: shelters_list y shelter_detail añadidas")
else:
    print("ya aplicado: shelters_list")
PY

echo ""
echo "▶ 2. URLs de refugios"
python3 - << 'PY'
from pathlib import Path
p = Path("frontend/urls/public.py")
text = p.read_text(encoding="utf-8")

if 'name="shelters-list"' not in text:
    needle = '    path("hospitales/", public.hospitals_list, name="hospitals-list"),'
    addition = (
        needle + "\n"
        '    path("refugios/", public.shelters_list, name="shelters-list"),\n'
        '    path(\n'
        '        "refugios/<slug:codigo>/",\n'
        '        public.shelter_detail,\n'
        '        name="shelter-detail",\n'
        '    ),'
    )
    text = text.replace(needle, addition, 1)
    p.write_text(text, encoding="utf-8")
    print("OK: URLs de refugios añadidas")
else:
    print("ya aplicado: URLs de refugios")
PY

echo ""
echo "▶ 3. Componente ocupacion_bar.html"
cat > templates/components/ocupacion_bar.html << 'EOF'
{% comment %}
Uso:
  {% include "components/ocupacion_bar.html" with refugio=refugio %}
Parámetros:
  refugio (dict) — salida de _serializar_refugio()
Renderiza una barra visual con % de ocupación + capacidad.
{% endcomment %}
{% with pct=refugio.porcentaje_ocupacion|default:0 total=refugio.capacidad_total|default:0 disp=refugio.capacidad_disponible|default:0 %}
<div class="space-y-1">
  <div class="flex justify-between text-xs text-text-muted">
    <span>Ocupación</span>
    <span>{{ pct }}%</span>
  </div>
  <div class="h-2 rounded-full overflow-hidden"
       style="background-color: color-mix(in srgb, var(--color-text) 10%, transparent);"
       role="progressbar"
       aria-valuenow="{{ pct }}"
       aria-valuemin="0"
       aria-valuemax="100"
       aria-label="Ocupación del refugio">
    <div class="h-full"
         style="
           width: {{ pct }}%;
           background: {% if pct >= 90 %}var(--gradient-emergency){% elif pct >= 70 %}var(--gradient-hero){% else %}var(--gradient-calm){% endif %};
           transition: width 300ms ease;
         "></div>
  </div>
  <div class="text-xs text-text-muted">
    {{ refugio.capacidad_disponible }} de {{ refugio.capacidad_total }} lugares disponibles
    {% if refugio.esta_lleno %}<span class="text-danger ml-1">· lleno</span>{% endif %}
  </div>
</div>
{% endwith %}
EOF

echo "OK: ocupacion_bar.html creado"

echo ""
echo "▶ 4. Componente shelter_card.html"
cat > templates/components/shelter_card.html << 'EOF'
{% comment %}
Uso:
  {% include "components/shelter_card.html" with refugio=refugio %}
{% endcomment %}
<article class="card card-hover p-5 flex flex-col h-full">
  <header class="mb-3">
    <h2 class="text-lg font-semibold text-primary leading-tight">
      <a href="{% url 'public:shelter-detail' codigo=refugio.codigo %}">
        {{ refugio.nombre }}
      </a>
    </h2>
    <p class="text-sm text-text-muted mt-1">
      {{ refugio.tipo_texto }}
      {% if refugio.estado_operativo %}
        · <span class="badge {% if refugio.estado_operativo == 'ACTIVO' %}badge-success{% elif refugio.estado_operativo == 'LLENO' %}badge-warning{% else %}badge-info{% endif %}">
          {{ refugio.estado_operativo_texto }}
        </span>
      {% endif %}
    </p>
  </header>

  <div class="text-sm text-text space-y-1 flex-1">
    <p>📍 {{ refugio.direccion }}</p>
    {% if refugio.municipio or refugio.parroquia %}
      <p class="text-text-muted">
        {% if refugio.parroquia %}{{ refugio.parroquia }}{% endif %}
        {% if refugio.parroquia and refugio.municipio %}, {% endif %}
        {% if refugio.municipio %}{{ refugio.municipio }}{% endif %}
      </p>
    {% endif %}
    {% if refugio.telefono_publico %}
      <p>📞 <a href="tel:{{ refugio.telefono_publico }}" class="underline">{{ refugio.telefono_publico }}</a></p>
    {% endif %}
  </div>

  <div class="mt-4 pt-3 border-t" style="border-color: color-mix(in srgb, var(--color-text) 10%, transparent);">
    {% include "components/ocupacion_bar.html" with refugio=refugio %}
    {% if refugio.servicios %}
      <div class="mt-2 flex flex-wrap gap-1">
        {% for s in refugio.servicios|slice:":5" %}
          <span class="badge badge-info text-xs">{{ s }}</span>
        {% endfor %}
        {% if refugio.servicios|length > 5 %}
          <span class="text-xs text-text-muted">+{{ refugio.servicios|length|add:"-5" }} más</span>
        {% endif %}
      </div>
    {% endif %}
  </div>
</article>
EOF

echo "OK: shelter_card.html creado"

echo ""
echo "▶ 5. Template shelters_list.html"
cat > templates/public/shelters_list.html << 'EOF'
{% extends "base/base_public.html" %}

{% block title %}Refugios — IntegraVida{% endblock %}

{% block content %}
<section class="mx-auto max-w-7xl px-4 py-8">

  <header class="mb-6">
    <nav aria-label="Migas de pan" class="text-sm mb-2">
      <a href="{% url 'public:home' %}" class="text-text-muted hover:text-primary">← Inicio</a>
    </nav>
    <h1 class="text-3xl font-bold text-primary">Refugios y centros de acopio</h1>
    <p class="text-text-muted mt-1">
      {{ total }} refugio{{ total|pluralize }} activo{{ total|pluralize }}.
      La ocupación se actualiza conforme reportan los operadores.
    </p>
  </header>

  <form method="get" class="card p-4 mb-6" aria-label="Filtros de refugios">
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
      <div class="flex items-center">
        <label class="inline-flex items-center gap-2 text-sm">
          <input type="checkbox" name="con_lugar" value="1"
                 {% if filtros.con_lugar %}checked{% endif %}
                 class="rounded">
          <span>Solo con lugares disponibles</span>
        </label>
      </div>
      <div class="flex items-end gap-2">
        <button type="submit" class="btn btn-primary w-full">Filtrar</button>
        {% if filtros.q or filtros.tipo or filtros.estado_operativo or filtros.municipio or filtros.con_lugar %}
          <a href="{% url 'public:shelters-list' %}" class="btn btn-ghost">Limpiar</a>
        {% endif %}
      </div>
    </div>
  </form>

  {% if refugios %}
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {% for refugio in refugios %}
        {% include "components/shelter_card.html" with refugio=refugio %}
      {% endfor %}
    </div>
  {% else %}
    {% include "components/empty-state.html" with icon="🏠" title="Sin resultados" description="No hay refugios que coincidan con tu búsqueda." action_label="Ver todos" action_url="/refugios/" %}
  {% endif %}

</section>
{% endblock %}
EOF

echo "OK: shelters_list.html creado"

echo ""
echo "▶ 6. Template shelter_detail.html"
cat > templates/public/shelter_detail.html << 'EOF'
{% extends "base/base_public.html" %}

{% block title %}{{ refugio.nombre }} — IntegraVida{% endblock %}

{% block content %}
<article class="mx-auto max-w-4xl px-4 py-8">

  <nav aria-label="Migas de pan" class="text-sm mb-4">
    <a href="{% url 'public:home' %}" class="text-text-muted hover:text-primary">Inicio</a>
    <span class="text-text-muted mx-1">/</span>
    <a href="{% url 'public:shelters-list' %}" class="text-text-muted hover:text-primary">Refugios</a>
    <span class="text-text-muted mx-1">/</span>
    <span class="text-text">{{ refugio.nombre }}</span>
  </nav>

  <header class="mb-6">
    <h1 class="text-3xl font-bold text-primary">{{ refugio.nombre }}</h1>
    <p class="text-text-muted mt-1">
      {{ refugio.tipo_texto }}
      {% if refugio.estado_operativo %}
        · <span class="badge {% if refugio.estado_operativo == 'ACTIVO' %}badge-success{% elif refugio.estado_operativo == 'LLENO' %}badge-warning{% else %}badge-info{% endif %}">{{ refugio.estado_operativo_texto }}</span>
      {% endif %}
    </p>
  </header>

  <div class="grid md:grid-cols-2 gap-6">

    <section class="card p-5">
      <h2 class="text-lg font-semibold mb-3">Ubicación y contacto</h2>
      <dl class="space-y-2 text-sm">
        <div>
          <dt class="text-text-muted">Dirección</dt>
          <dd>{{ refugio.direccion }}</dd>
        </div>
        {% if refugio.referencia_lugar %}
          <div>
            <dt class="text-text-muted">Referencia</dt>
            <dd>{{ refugio.referencia_lugar }}</dd>
          </div>
        {% endif %}
        {% if refugio.municipio or refugio.parroquia %}
          <div>
            <dt class="text-text-muted">Ubicación administrativa</dt>
            <dd>
              {% if refugio.parroquia %}{{ refugio.parroquia }}{% endif %}
              {% if refugio.parroquia and refugio.municipio %}, {% endif %}
              {% if refugio.municipio %}{{ refugio.municipio }}{% endif %}
            </dd>
          </div>
        {% endif %}
        {% if refugio.telefono_publico %}
          <div>
            <dt class="text-text-muted">Teléfono</dt>
            <dd><a href="tel:{{ refugio.telefono_publico }}" class="underline text-primary">{{ refugio.telefono_publico }}</a></dd>
          </div>
        {% endif %}
        {% if refugio.correo_publico %}
          <div>
            <dt class="text-text-muted">Correo</dt>
            <dd><a href="mailto:{{ refugio.correo_publico }}" class="underline text-primary">{{ refugio.correo_publico }}</a></dd>
          </div>
        {% endif %}
      </dl>
    </section>

    <section class="card p-5">
      <h2 class="text-lg font-semibold mb-3">Ocupación</h2>
      {% include "components/ocupacion_bar.html" with refugio=refugio %}
      {% if refugio.ocupacion_actualizada_en %}
        <p class="text-xs text-text-muted mt-3">
          Última actualización: {{ refugio.ocupacion_actualizada_en }}
        </p>
      {% else %}
        <p class="text-xs text-text-muted mt-3">
          Sin actualización reciente de ocupación.
        </p>
      {% endif %}
    </section>

    {% if refugio.servicios %}
      <section class="card p-5 md:col-span-2">
        <h2 class="text-lg font-semibold mb-3">Servicios disponibles</h2>
        <div class="flex flex-wrap gap-2">
          {% for s in refugio.servicios %}
            <span class="badge badge-info">{{ s }}</span>
          {% endfor %}
        </div>
      </section>
    {% endif %}

  </div>

  <div class="mt-8 pt-6 border-t" style="border-color: color-mix(in srgb, var(--color-text) 10%, transparent);">
    <a href="{% url 'public:shelters-list' %}" class="btn btn-ghost">← Volver a la lista</a>
  </div>

</article>
{% endblock %}
EOF

echo "OK: shelter_detail.html creado"

echo ""
echo "▶ 7. Actualizar home.html"
python3 - << 'PY'
from pathlib import Path
p = Path("templates/public/home.html")
text = p.read_text(encoding="utf-8")

old = '<a href="/api/publico/refugios/" class="btn btn-secondary">'
new = '<a href="/refugios/" class="btn btn-secondary">'

if old in text:
    text = text.replace(old, new, 1)
    p.write_text(text, encoding="utf-8")
    print("OK: home.html apunta a /refugios/")
elif '/refugios/' in text:
    print("ya aplicado: home.html")
else:
    raise SystemExit("ERROR: link no encontrado")
PY

echo ""
echo "▶ 8. Ajustar test del home"
python3 - << 'PY'
from pathlib import Path
p = Path("frontend/tests/test_public_views.py")
text = p.read_text(encoding="utf-8")

old = '        self.assertContains(r, "/api/publico/refugios/")'
new = '        self.assertContains(r, "/refugios/")'

if old in text:
    text = text.replace(old, new, 1)
    p.write_text(text, encoding="utf-8")
    print("OK: test_home_enlaza_a_api_publica ajustado para refugios")
elif '/refugios/' in text:
    print("ya aplicado: test ajustado")
else:
    print("NOTA: no se encontró el patrón, revisar manualmente")
PY

echo ""
echo "▶ 9. Rebuild CSS"
NODE_ENV=production npx tailwindcss \
  -i ./static/css/src/main.css \
  -o ./static/css/dist/main.css \
  --minify
echo "CSS gzip: $(gzip -c static/css/dist/main.css | wc -c) bytes"

echo ""
echo "▶ 10. Anti-CDN"
bash scripts/check-no-cdn.sh

echo ""
echo "▶ 11. Django check"
python3 manage.py check

echo ""
echo "▶ 12. BLOQUEO si tests fallan (§3.8)"
TEST_OUT=$(python3 manage.py test apps.configuracion frontend -v 1 2>&1 | tail -4)
echo "$TEST_OUT"
if ! echo "$TEST_OUT" | grep -q "^OK"; then
    echo ""
    echo "❌ ERROR: tests rojos. NO COMMITEAR. Arreglar antes."
    exit 1
fi
echo "✅ Tests OK, seguro para commit"

echo ""
echo "▶ 13. Smoke de refugios"
pkill -f "manage.py runserver" 2>/dev/null || true
sleep 1
python3 manage.py runserver 0.0.0.0:8000 --noreload &> /tmp/rs_f2b.log &
RS_PID=$!
sleep 3

CODE_LIST=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/refugios/)
CODE_404=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/refugios/no-existe/)
CODE_HOME=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/)
HOME_LINK=$(curl -s http://localhost:8000/ | grep -c 'href="/refugios/"' || true)

kill $RS_PID 2>/dev/null; wait $RS_PID 2>/dev/null || true

echo "GET /refugios/              → $CODE_LIST (esperado 200)"
echo "GET /refugios/no-existe/    → $CODE_404 (esperado 404)"
echo "GET /                       → $CODE_HOME (esperado 200)"
echo "home enlaza a /refugios/:   $HOME_LINK (esperado 1)"

if [ "$CODE_LIST" != "200" ] || [ "$CODE_404" != "404" ]; then
    echo "ERROR: rutas incorrectas"
    exit 1
fi

echo ""
echo "✅ F2.b — Refugios implementados"
