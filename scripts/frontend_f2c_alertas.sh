#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

echo "▶ 1. Extender frontend/views/public.py con alertas"
python3 - << 'PY'
from pathlib import Path
p = Path("frontend/views/public.py")
text = p.read_text(encoding="utf-8")

if "def alerts_list(" not in text:
    text = text.rstrip() + '''


@require_GET
def alerts_list(request):
    """Lista pública de alertas (emergencias verificadas)."""
    from django.db.models import Q
    from apps.emergencias.views import (
        ESTADOS_PUBLICOS, _serializar_emergencia,
    )

    queryset = (
        Emergencia.objects
        .filter(estado__in=ESTADOS_PUBLICOS)
        .select_related("municipio", "parroquia")
    )

    categoria = request.GET.get("categoria", "").strip()
    if categoria:
        queryset = queryset.filter(categoria=categoria)

    gravedad = request.GET.get("gravedad", "").strip()
    if gravedad:
        try:
            queryset = queryset.filter(gravedad=int(gravedad))
        except (TypeError, ValueError):
            pass

    estado = request.GET.get("estado", "").strip()
    if estado and estado in ESTADOS_PUBLICOS:
        queryset = queryset.filter(estado=estado)

    municipio = request.GET.get("municipio", "").strip()
    if municipio:
        queryset = queryset.filter(municipio__nombre__icontains=municipio)

    q = request.GET.get("q", "").strip()[:100]
    if q:
        queryset = queryset.filter(
            Q(ubicacion_texto__icontains=q) | Q(titulo__icontains=q)
        )

    queryset = queryset.order_by("-ocurrida_en", "-creada_en")[:60]

    alertas = [_serializar_emergencia(e) for e in queryset]

    from apps.emergencias.models import Emergencia as EmergenciaModel
    return render(request, "public/alerts_list.html", {
        "alertas": alertas,
        "total": len(alertas),
        "filtros": {
            "categoria": categoria,
            "gravedad": gravedad,
            "estado": estado,
            "municipio": municipio,
            "q": q,
        },
        "opciones_categoria": [
            (v, l) for v, l in EmergenciaModel.Categoria.choices
        ],
        "opciones_gravedad": [
            ("1", "Baja"),
            ("2", "Moderada"),
            ("3", "Alta"),
            ("4", "Crítica"),
        ],
        "opciones_estado": [
            ("CONFIRMADA", "Confirmada"),
            ("EN_ATENCION", "En atención"),
            ("RESUELTA", "Resuelta"),
        ],
    })


@require_GET
def alert_detail(request, emergencia_id):
    """Detalle público de una alerta por UUID."""
    from apps.emergencias.views import (
        ESTADOS_PUBLICOS, _serializar_emergencia,
    )

    try:
        emergencia = (
            Emergencia.objects
            .select_related("municipio", "parroquia")
            .get(id=emergencia_id, estado__in=ESTADOS_PUBLICOS)
        )
    except Emergencia.DoesNotExist:
        raise Http404("Alerta no encontrada")

    return render(request, "public/alert_detail.html", {
        "alerta": _serializar_emergencia(emergencia),
    })
'''
    p.write_text(text, encoding="utf-8")
    print("OK: alerts_list y alert_detail añadidas")
else:
    print("ya aplicado: alerts_list")
PY

echo ""
echo "▶ 2. URLs de alertas"
python3 - << 'PY'
from pathlib import Path
p = Path("frontend/urls/public.py")
text = p.read_text(encoding="utf-8")

if 'name="alerts-list"' not in text:
    needle = '    path("refugios/", public.shelters_list, name="shelters-list"),'
    addition = (
        needle + "\n"
        '    path("alertas/", public.alerts_list, name="alerts-list"),\n'
        '    path(\n'
        '        "alertas/<uuid:emergencia_id>/",\n'
        '        public.alert_detail,\n'
        '        name="alert-detail",\n'
        '    ),'
    )
    text = text.replace(needle, addition, 1)
    p.write_text(text, encoding="utf-8")
    print("OK: URLs de alertas añadidas")
else:
    print("ya aplicado: URLs de alertas")
PY

echo ""
echo "▶ 3. Componente alert_card.html"
cat > templates/components/alert_card.html << 'EOF'
{% comment %}
Uso:
  {% include "components/alert_card.html" with alerta=alerta %}
Parámetros:
  alerta (dict) — salida de _serializar_emergencia()
{% endcomment %}
<article class="card card-hover p-5 flex flex-col h-full
  {% if alerta.gravedad == 4 %}border-l-4 border-l-danger{% elif alerta.gravedad == 3 %}border-l-4 border-l-accent{% endif %}">
  <header class="mb-3">
    <div class="flex items-start justify-between gap-2">
      <h2 class="text-lg font-semibold text-primary leading-tight flex-1">
        <a href="{% url 'public:alert-detail' emergencia_id=alerta.id %}">
          {{ alerta.titulo }}
        </a>
      </h2>
      <span class="badge
        {% if alerta.gravedad == 4 %}badge-danger
        {% elif alerta.gravedad == 3 %}badge-warning
        {% elif alerta.gravedad == 2 %}badge-info
        {% else %}badge-success{% endif %}">
        {{ alerta.gravedad_texto }}
      </span>
    </div>
    <p class="text-sm text-text-muted mt-1">
      {{ alerta.categoria_texto }}
      · <span class="badge
        {% if alerta.estado == 'CONFIRMADA' %}badge-danger
        {% elif alerta.estado == 'EN_ATENCION' %}badge-warning
        {% else %}badge-success{% endif %}">
        {{ alerta.estado_texto }}
      </span>
    </p>
  </header>

  <div class="text-sm text-text space-y-1 flex-1">
    <p>📍 {{ alerta.ubicacion }}</p>
    {% if alerta.municipio or alerta.parroquia %}
      <p class="text-text-muted">
        {% if alerta.parroquia %}{{ alerta.parroquia }}{% endif %}
        {% if alerta.parroquia and alerta.municipio %}, {% endif %}
        {% if alerta.municipio %}{{ alerta.municipio }}{% endif %}
      </p>
    {% endif %}
    {% if alerta.ocurrida_en %}
      <p class="text-xs text-text-muted">🕒 {{ alerta.ocurrida_en|slice:":16" }}</p>
    {% endif %}
  </div>

  <div class="mt-3 text-sm">
    <a href="{% url 'public:alert-detail' emergencia_id=alerta.id %}" class="text-primary underline">
      Ver detalle →
    </a>
  </div>
</article>
EOF

echo "OK: alert_card.html creado"

echo ""
echo "▶ 4. Template alerts_list.html"
cat > templates/public/alerts_list.html << 'EOF'
{% extends "base/base_public.html" %}

{% block title %}Alertas y emergencias — IntegraVida{% endblock %}

{% block content %}
<section class="mx-auto max-w-7xl px-4 py-8">

  <header class="mb-6">
    <nav aria-label="Migas de pan" class="text-sm mb-2">
      <a href="{% url 'public:home' %}" class="text-text-muted hover:text-primary">← Inicio</a>
    </nav>
    <h1 class="text-3xl font-bold text-primary">Alertas y emergencias</h1>
    <p class="text-text-muted mt-1">
      {{ total }} alerta{{ total|pluralize }} activa{{ total|pluralize }} verificada{{ total|pluralize }}.
      Solo se muestran eventos confirmados por las autoridades.
    </p>
  </header>

  <form method="get" class="card p-4 mb-6" aria-label="Filtros de alertas">
    <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
      <div>
        <label for="f-q" class="block text-sm font-medium text-text mb-1">Buscar</label>
        <input type="search" id="f-q" name="q" value="{{ filtros.q }}"
               placeholder="Título o ubicación" class="input">
      </div>
      <div>
        <label for="f-categoria" class="block text-sm font-medium text-text mb-1">Categoría</label>
        <select id="f-categoria" name="categoria" class="input">
          <option value="">Todas</option>
          {% for v, l in opciones_categoria %}
            <option value="{{ v }}" {% if v == filtros.categoria %}selected{% endif %}>{{ l }}</option>
          {% endfor %}
        </select>
      </div>
      <div>
        <label for="f-gravedad" class="block text-sm font-medium text-text mb-1">Gravedad</label>
        <select id="f-gravedad" name="gravedad" class="input">
          <option value="">Todas</option>
          {% for v, l in opciones_gravedad %}
            <option value="{{ v }}" {% if v == filtros.gravedad %}selected{% endif %}>{{ l }}</option>
          {% endfor %}
        </select>
      </div>
      <div>
        <label for="f-estado" class="block text-sm font-medium text-text mb-1">Estado</label>
        <select id="f-estado" name="estado" class="input">
          <option value="">Todos</option>
          {% for v, l in opciones_estado %}
            <option value="{{ v }}" {% if v == filtros.estado %}selected{% endif %}>{{ l }}</option>
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
        {% if filtros.q or filtros.categoria or filtros.gravedad or filtros.estado or filtros.municipio %}
          <a href="{% url 'public:alerts-list' %}" class="btn btn-ghost">Limpiar</a>
        {% endif %}
      </div>
    </div>
  </form>

  {% if alertas %}
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {% for alerta in alertas %}
        {% include "components/alert_card.html" with alerta=alerta %}
      {% endfor %}
    </div>
  {% else %}
    {% include "components/empty-state.html" with icon="⚠" title="Sin alertas activas" description="No hay alertas verificadas que coincidan con los filtros." action_label="Ver todas" action_url="/alertas/" %}
  {% endif %}

</section>
{% endblock %}
EOF

echo "OK: alerts_list.html creado"

echo ""
echo "▶ 5. Template alert_detail.html"
cat > templates/public/alert_detail.html << 'EOF'
{% extends "base/base_public.html" %}

{% block title %}{{ alerta.titulo }} — IntegraVida{% endblock %}

{% block content %}
<article class="mx-auto max-w-4xl px-4 py-8">

  <nav aria-label="Migas de pan" class="text-sm mb-4">
    <a href="{% url 'public:home' %}" class="text-text-muted hover:text-primary">Inicio</a>
    <span class="text-text-muted mx-1">/</span>
    <a href="{% url 'public:alerts-list' %}" class="text-text-muted hover:text-primary">Alertas</a>
    <span class="text-text-muted mx-1">/</span>
    <span class="text-text">{{ alerta.titulo }}</span>
  </nav>

  <header class="mb-6">
    <div class="flex items-start justify-between gap-3 flex-wrap">
      <h1 class="text-3xl font-bold text-primary">{{ alerta.titulo }}</h1>
      <div class="flex flex-wrap gap-2">
        <span class="badge
          {% if alerta.gravedad == 4 %}badge-danger
          {% elif alerta.gravedad == 3 %}badge-warning
          {% elif alerta.gravedad == 2 %}badge-info
          {% else %}badge-success{% endif %}">
          Gravedad: {{ alerta.gravedad_texto }}
        </span>
        <span class="badge
          {% if alerta.estado == 'CONFIRMADA' %}badge-danger
          {% elif alerta.estado == 'EN_ATENCION' %}badge-warning
          {% else %}badge-success{% endif %}">
          {{ alerta.estado_texto }}
        </span>
      </div>
    </div>
    <p class="text-text-muted mt-2">
      {{ alerta.categoria_texto }}
      {% if alerta.ocurrida_en %}· Ocurrió: {{ alerta.ocurrida_en|slice:":16" }}{% endif %}
    </p>
  </header>

  <div class="grid md:grid-cols-3 gap-6">

    <section class="card p-5 md:col-span-2">
      <h2 class="text-lg font-semibold mb-3">Descripción</h2>
      <p class="text-text whitespace-pre-line">{{ alerta.descripcion }}</p>
    </section>

    <section class="card p-5">
      <h2 class="text-lg font-semibold mb-3">Ubicación</h2>
      <dl class="space-y-2 text-sm">
        <div>
          <dt class="text-text-muted">Lugar</dt>
          <dd>{{ alerta.ubicacion }}</dd>
        </div>
        {% if alerta.referencia_lugar %}
          <div>
            <dt class="text-text-muted">Referencia</dt>
            <dd>{{ alerta.referencia_lugar }}</dd>
          </div>
        {% endif %}
        {% if alerta.parroquia or alerta.municipio %}
          <div>
            <dt class="text-text-muted">Ubicación administrativa</dt>
            <dd>
              {% if alerta.parroquia %}{{ alerta.parroquia }}{% endif %}
              {% if alerta.parroquia and alerta.municipio %}, {% endif %}
              {% if alerta.municipio %}{{ alerta.municipio }}{% endif %}
            </dd>
          </div>
        {% endif %}
      </dl>
    </section>

  </div>

  <div class="mt-8 pt-6 border-t" style="border-color: color-mix(in srgb, var(--color-text) 10%, transparent);">
    <a href="{% url 'public:alerts-list' %}" class="btn btn-ghost">← Volver a alertas</a>
  </div>

</article>
{% endblock %}
EOF

echo "OK: alert_detail.html creado"

echo ""
echo "▶ 6. Actualizar home.html — último botón a HTML"
python3 - << 'PY'
from pathlib import Path
p = Path("templates/public/home.html")
text = p.read_text(encoding="utf-8")

old = (
    '<a href="/api/publico/emergencias/" class="btn btn-primary">\n'
    '      Ver emergencias →\n'
    '    </a>'
)
new = (
    '<a href="/alertas/" class="btn btn-primary">\n'
    '      Ver alertas →\n'
    '    </a>'
)

if old in text:
    text = text.replace(old, new, 1)
    p.write_text(text, encoding="utf-8")
    print("OK: home.html apunta a /alertas/")
elif '/alertas/' in text:
    print("ya aplicado: home.html")
else:
    raise SystemExit("ERROR: bloque no encontrado en home.html")
PY

echo ""
echo "▶ 7. Ajustar test del home — las 3 secciones son HTML"
python3 - << 'PY'
from pathlib import Path
p = Path("frontend/tests/test_public_views.py")
text = p.read_text(encoding="utf-8")

old = '''    def test_home_enlaza_a_api_publica(self):
        """Home enlaza a la API pública (emergencias, refugios) y al
        portal HTML de hospitales. Los tres coexisten porque la API
        sigue siendo el contrato (§api.md) y el portal HTML es UX."""
        r = self.client.get("/")
        self.assertContains(r, "/api/publico/emergencias/")
        self.assertContains(r, "/refugios/")
        # Hospitales migró a portal HTML en F2.a
        self.assertContains(r, "/hospitales/")'''

new = '''    def test_home_enlaza_a_secciones_publicas(self):
        """Home enlaza a las 3 secciones del portal HTML (F2 completa).
        La API pública sigue existiendo (§api.md) pero ya no se enlaza
        desde el home: el portal es para ciudadanos, la API para
        integraciones."""
        r = self.client.get("/")
        self.assertContains(r, "/alertas/")
        self.assertContains(r, "/refugios/")
        self.assertContains(r, "/hospitales/")
        # Confirmar que ya no hay links crudos a la API desde el home
        self.assertNotContains(r, "/api/publico/emergencias/")
        self.assertNotContains(r, "/api/publico/refugios/")
        self.assertNotContains(r, "/api/publico/hospitales/")'''

if old in text:
    text = text.replace(old, new, 1)
    p.write_text(text, encoding="utf-8")
    print("OK: test_home_* renombrado a test_home_enlaza_a_secciones_publicas")
elif 'test_home_enlaza_a_secciones_publicas' in text:
    print("ya aplicado: test renombrado")
else:
    raise SystemExit("ERROR: bloque anterior no encontrado")
PY

echo ""
echo "▶ 8. Tests nuevos de alertas"
cat >> frontend/tests/test_public_views.py << 'PYEOF'


class AlertasPublicasTests(TestCase):
    """Tests de /alertas/ (F2.c)."""

    def test_alerts_list_200_anonimo(self):
        r = self.client.get("/alertas/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Alertas y emergencias")

    def test_alerts_list_incluye_filtros(self):
        r = self.client.get("/alertas/")
        self.assertContains(r, 'name="categoria"')
        self.assertContains(r, 'name="gravedad"')
        self.assertContains(r, 'name="estado"')

    def test_alert_detail_inexistente_404(self):
        r = self.client.get(
            "/alertas/00000000-0000-0000-0000-000000000000/"
        )
        self.assertEqual(r.status_code, 404)

    def test_alert_detail_no_expone_no_verificadas(self):
        """Una emergencia en RECIBIDA no debe ser accesible por URL directa."""
        from apps.emergencias.models import Emergencia
        from django.utils import timezone

        emergencia = Emergencia.objects.create(
            titulo="Test no verificada",
            descripcion="No debería ser pública",
            categoria=Emergencia.Categoria.OTRA,
            estado=Emergencia.Estado.RECIBIDA,
            ubicacion_texto="Test",
        )

        r = self.client.get(f"/alertas/{emergencia.id}/")
        self.assertEqual(r.status_code, 404)
PYEOF

echo "OK: tests de alertas añadidos (4)"

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
echo "▶ 13. Smoke de alertas"
pkill -f "manage.py runserver" 2>/dev/null || true
sleep 1
python3 manage.py runserver 0.0.0.0:8000 --noreload &> /tmp/rs_f2c.log &
RS_PID=$!
sleep 3

CODE_LIST=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/alertas/)
CODE_404=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/alertas/00000000-0000-0000-0000-000000000000/)
CODE_HOME=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/)
HOME_LINKS=$(curl -s http://localhost:8000/ | grep -oE 'href="/(alertas|refugios|hospitales)/"' | sort -u | wc -l)

kill $RS_PID 2>/dev/null; wait $RS_PID 2>/dev/null || true

echo "GET /alertas/              → $CODE_LIST (esperado 200)"
echo "GET /alertas/<uuid>/        → $CODE_404 (esperado 404)"
echo "GET /                       → $CODE_HOME (esperado 200)"
echo "Links únicos en home:       $HOME_LINKS (esperado 3)"

if [ "$CODE_LIST" != "200" ] || [ "$CODE_404" != "404" ] || [ "$HOME_LINKS" != "3" ]; then
    echo "ERROR: rutas o links incorrectos"
    exit 1
fi

echo ""
echo "✅ F2.c — Alertas implementadas"
echo "🎉 F2 COMPLETO — portal público con 3 secciones HTML"
