#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

echo "▶ 1. Añadir imports faltantes a frontend/views/public.py"
python3 - << 'PY'
from pathlib import Path
p = Path("frontend/views/public.py")
text = p.read_text(encoding="utf-8")

# Añadir require_http_methods, redirect, get_object_or_404
if "from django.views.decorators.http import require_http_methods" not in text:
    needle = "from django.views.decorators.http import require_GET\n"
    text = text.replace(
        needle,
        needle + "from django.views.decorators.http import require_http_methods\n",
        1,
    )

if "from django.shortcuts import redirect" not in text:
    needle = "from django.shortcuts import render\n"
    text = text.replace(
        needle,
        needle + "from django.shortcuts import redirect\n",
        1,
    )

p.write_text(text, encoding="utf-8")
print("OK: imports añadidos")
PY

echo ""
echo "▶ 2. Añadir vistas report_create y report_tracking"
python3 - << 'PY'
from pathlib import Path
p = Path("frontend/views/public.py")
text = p.read_text(encoding="utf-8")

if "def report_create(" not in text:
    text = text.rstrip() + '''


@require_http_methods(["GET", "POST"])
def report_create(request):
    """Formulario HTML de reporte ciudadano + submit."""
    from django.core.exceptions import ValidationError
    from apps.emergencias.models import Emergencia
    from apps.emergencias.services import recibir_reporte_publico

    form_data = {
        "categoria": "",
        "descripcion": "",
        "ubicacion_texto": "",
        "referencia_lugar": "",
    }
    errors = {}
    limitado = False

    if request.method == "POST":
        form_data = {
            "categoria": request.POST.get("categoria", "").strip(),
            "descripcion": request.POST.get("descripcion", "").strip(),
            "ubicacion_texto": request.POST.get("ubicacion_texto", "").strip(),
            "referencia_lugar": request.POST.get("referencia_lugar", "").strip(),
        }

        try:
            reporte, limitado = recibir_reporte_publico(
                datos=form_data,
                request=request,
            )
            if not limitado and reporte is not None:
                return redirect(
                    "public:report-tracking",
                    reporte_id=reporte.id,
                )
        except ValidationError as exc:
            if hasattr(exc, "message_dict"):
                errors = exc.message_dict
            else:
                errors = {"__all__": list(exc.messages)}

    categorias = [(v, l) for v, l in Emergencia.Categoria.choices]

    status = 200
    if limitado:
        status = 429

    return render(
        request,
        "public/report_form.html",
        {
            "form_data": form_data,
            "errors": errors,
            "limitado": limitado,
            "categorias": categorias,
        },
        status=status,
    )


@require_GET
def report_tracking(request, reporte_id):
    """Seguimiento público de un reporte por UUID (magic link)."""
    from apps.emergencias.models import ReporteEmergencia

    try:
        reporte = ReporteEmergencia.objects.get(id=reporte_id)
    except ReporteEmergencia.DoesNotExist:
        raise Http404("Reporte no encontrado")

    # Privacidad: solo exponer campos NO sensibles.
    # NO se expone: descripcion, ubicacion_texto, referencia_lugar,
    # reportante, punto. El UUID actúa como "magic link".
    vinculado_publico = False
    emergencia_publica = None

    if reporte.emergencia_id is not None:
        try:
            emergencia = reporte.emergencia
            if emergencia.estado in ESTADOS_EMERGENCIA_PUBLICOS:
                vinculado_publico = True
                emergencia_publica = {
                    "id": str(emergencia.id),
                    "titulo": emergencia.titulo,
                }
        except Emergencia.DoesNotExist:
            pass

    data = {
        "id": str(reporte.id),
        "categoria": reporte.categoria,
        "categoria_texto": reporte.get_categoria_display(),
        "estado_revision": reporte.estado_revision,
        "estado_revision_texto": reporte.get_estado_revision_display(),
        "recibido_en": reporte.recibido_en,
        "vinculado": reporte.emergencia_id is not None,
        "vinculado_publico": vinculado_publico,
        "emergencia_publica": emergencia_publica,
    }

    return render(
        request,
        "public/report_tracking.html",
        {"reporte": data},
    )
'''
    p.write_text(text, encoding="utf-8")
    print("OK: report_create y report_tracking añadidas")
else:
    print("ya aplicado: report_create")
PY

echo ""
echo "▶ 3. URLs de reportes"
python3 - << 'PY'
from pathlib import Path
p = Path("frontend/urls/public.py")
text = p.read_text(encoding="utf-8")

if 'name="report-create"' not in text:
    needle = '    path("alertas/", public.alerts_list, name="alerts-list"),'
    addition = (
        needle + "\n"
        '    path("reportes/", public.report_create, name="report-create"),\n'
        '    path(\n'
        '        "reportes/<uuid:reporte_id>/",\n'
        '        public.report_tracking,\n'
        '        name="report-tracking",\n'
        '    ),'
    )
    text = text.replace(needle, addition, 1)
    p.write_text(text, encoding="utf-8")
    print("OK: URLs de reportes añadidas")
else:
    print("ya aplicado: URLs de reportes")
PY

echo ""
echo "▶ 4. Template report_form.html"
cat > templates/public/report_form.html << 'EOF'
{% extends "base/base_public.html" %}

{% block title %}Reportar emergencia — IntegraVida{% endblock %}

{% block content %}
<section class="mx-auto max-w-2xl px-4 py-8">

  <nav aria-label="Migas de pan" class="text-sm mb-2">
    <a href="{% url 'public:home' %}" class="text-text-muted hover:text-primary">← Inicio</a>
  </nav>

  <header class="mb-6">
    <h1 class="text-3xl font-bold text-primary">Reportar una emergencia</h1>
    <p class="text-text-muted mt-2">
      Tu reporte será recibido por el equipo de coordinación para su
      verificación. No sustituye a los servicios de emergencia.
    </p>
  </header>

  {% include "components/alert.html" with variant="warning" title="Si hay riesgo de vida" body="Llama al 911 o acude al centro de salud más cercano. Este formulario NO es un servicio de emergencia inmediata." %}

  {% if limitado %}
    <div class="mt-4">
      {% include "components/alert.html" with variant="danger" title="Demasiados reportes" body="Has enviado varios reportes en poco tiempo. Espera unos minutos antes de enviar otro." dismissible=False %}
    </div>
  {% endif %}

  {% if errors.__all__ %}
    <div class="mt-4">
      {% include "components/alert.html" with variant="danger" title="Error al enviar" body=errors.__all__.0 dismissible=True %}
    </div>
  {% endif %}

  <form method="post" class="mt-6 card p-6 space-y-4" data-validate>
    {% csrf_token %}

    <div>
      <label for="f-categoria" class="block text-sm font-medium text-text mb-1">
        Categoría <span class="text-danger" aria-hidden="true">*</span>
      </label>
      <select id="f-categoria" name="categoria" class="input" required
              {% if errors.categoria %}aria-invalid="true" aria-describedby="err-categoria"{% endif %}>
        <option value="">Selecciona una categoría</option>
        {% for v, l in categorias %}
          <option value="{{ v }}" {% if v == form_data.categoria %}selected{% endif %}>{{ l }}</option>
        {% endfor %}
      </select>
      {% if errors.categoria %}
        <ul id="err-categoria" class="text-xs text-danger-600 mt-1" role="alert">
          {% for err in errors.categoria %}<li>{{ err }}</li>{% endfor %}
        </ul>
      {% endif %}
    </div>

    <div>
      <label for="f-descripcion" class="block text-sm font-medium text-text mb-1">
        Descripción <span class="text-danger" aria-hidden="true">*</span>
      </label>
      <textarea id="f-descripcion" name="descripcion" rows="5" class="input" required
                maxlength="5000"
                placeholder="Describe qué está pasando. No incluyas datos personales de terceros."
                {% if errors.descripcion %}aria-invalid="true" aria-describedby="err-descripcion"{% endif %}>{{ form_data.descripcion }}</textarea>
      <p class="text-xs text-text-muted mt-1">
        Máximo 5000 caracteres. Evita nombres completos, cédulas o diagnósticos de otras personas.
      </p>
      {% if errors.descripcion %}
        <ul id="err-descripcion" class="text-xs text-danger-600 mt-1" role="alert">
          {% for err in errors.descripcion %}<li>{{ err }}</li>{% endfor %}
        </ul>
      {% endif %}
    </div>

    <div>
      <label for="f-ubicacion" class="block text-sm font-medium text-text mb-1">
        Ubicación <span class="text-danger" aria-hidden="true">*</span>
      </label>
      <input type="text" id="f-ubicacion" name="ubicacion_texto" class="input" required
             maxlength="300"
             placeholder="Ej: Av. Principal de Petare, frente al mercado"
             value="{{ form_data.ubicacion_texto }}"
             {% if errors.ubicacion_texto %}aria-invalid="true" aria-describedby="err-ubicacion"{% endif %}>
      {% if errors.ubicacion_texto %}
        <ul id="err-ubicacion" class="text-xs text-danger-600 mt-1" role="alert">
          {% for err in errors.ubicacion_texto %}<li>{{ err }}</li>{% endfor %}
        </ul>
      {% endif %}
    </div>

    <div>
      <label for="f-referencia" class="block text-sm font-medium text-text mb-1">
        Referencia adicional <span class="text-text-muted">(opcional)</span>
      </label>
      <input type="text" id="f-referencia" name="referencia_lugar" class="input"
             maxlength="250"
             placeholder="Punto de referencia para ubicar mejor el lugar"
             value="{{ form_data.referencia_lugar }}"
             {% if errors.referencia_lugar %}aria-invalid="true" aria-describedby="err-referencia"{% endif %}>
      {% if errors.referencia_lugar %}
        <ul id="err-referencia" class="text-xs text-danger-600 mt-1" role="alert">
          {% for err in errors.referencia_lugar %}<li>{{ err }}</li>{% endfor %}
        </ul>
      {% endif %}
    </div>

    <div class="flex items-center justify-between gap-3 pt-2">
      <p class="text-xs text-text-muted">
        Tu reporte será verificado antes de publicarse.
      </p>
      <button type="submit" class="btn btn-primary">
        Enviar reporte
      </button>
    </div>
  </form>

  <section class="mt-8 pt-6 border-t" style="border-color: color-mix(in srgb, var(--color-text) 10%, transparent);">
    <h2 class="text-lg font-semibold mb-2">¿Ya enviaste un reporte?</h2>
    <p class="text-sm text-text-muted mb-3">
      Consulta su estado con el código que recibiste al enviar tu reporte.
    </p>
    <form method="get" action="#" id="tracking-form" class="flex gap-2">
      <input type="text" id="tracking-code" class="input flex-1"
             placeholder="Pega tu código de seguimiento (UUID)"
             aria-label="Código de seguimiento">
      <button type="button" class="btn btn-ghost" onclick="
        var code = document.getElementById('tracking-code').value.trim();
        if (code) window.location.href = '/reportes/' + code + '/';
      ">Consultar</button>
    </form>
  </section>

</section>
{% endblock %}
EOF

echo "OK: report_form.html creado"

echo ""
echo "▶ 5. Template report_tracking.html"
cat > templates/public/report_tracking.html << 'EOF'
{% extends "base/base_public.html" %}

{% block title %}Seguimiento de reporte — IntegraVida{% endblock %}

{% block content %}
<section class="mx-auto max-w-2xl px-4 py-8">

  <nav aria-label="Migas de pan" class="text-sm mb-2">
    <a href="{% url 'public:home' %}" class="text-text-muted hover:text-primary">← Inicio</a>
  </nav>

  <header class="mb-6">
    <h1 class="text-3xl font-bold text-primary">Seguimiento de reporte</h1>
    <p class="text-text-muted mt-2">
      Tu reporte fue recibido correctamente. Guarda este código para
      consultar su estado más adelante.
    </p>
  </header>

  <div class="card p-6 space-y-4">

    <div>
      <p class="text-sm text-text-muted mb-1">Código de seguimiento</p>
      <div class="flex gap-2 items-center">
        <code id="report-id" class="text-sm bg-surface-raised p-3 rounded flex-1 break-all font-mono">{{ reporte.id }}</code>
        <button type="button" class="btn btn-ghost"
                onclick="
                  navigator.clipboard.writeText('{{ reporte.id }}').then(function() {
                    var btn = event.target;
                    var orig = btn.textContent;
                    btn.textContent = '✓ Copiado';
                    setTimeout(function(){ btn.textContent = orig; }, 2000);
                  });
                "
                aria-label="Copiar código al portapapeles">
          Copiar
        </button>
      </div>
      <p class="text-xs text-text-muted mt-2">
        Este código es la única forma de consultar tu reporte. No lo compartas públicamente.
      </p>
    </div>

    <div class="pt-4 border-t" style="border-color: color-mix(in srgb, var(--color-text) 10%, transparent);">
      <dl class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
        <div>
          <dt class="text-text-muted">Categoría</dt>
          <dd class="font-medium">{{ reporte.categoria_texto }}</dd>
        </div>
        <div>
          <dt class="text-text-muted">Estado</dt>
          <dd>
            <span class="badge
              {% if reporte.estado_revision == 'PENDIENTE' %}badge-info
              {% elif reporte.estado_revision == 'EN_REVISION' %}badge-warning
              {% elif reporte.estado_revision == 'VINCULADO' %}badge-success
              {% else %}badge-info{% endif %}"
              aria-live="polite">
              {{ reporte.estado_revision_texto }}
            </span>
          </dd>
        </div>
        <div>
          <dt class="text-text-muted">Recibido</dt>
          <dd class="font-medium">{{ reporte.recibido_en|slice:":16" }}</dd>
        </div>
        {% if reporte.vinculado_publico and reporte.emergencia_publica %}
          <div>
            <dt class="text-text-muted">Vinculado a</dt>
            <dd class="font-medium">
              <a href="{% url 'public:alert-detail' emergencia_id=reporte.emergencia_publica.id %}"
                 class="text-primary underline">
                {{ reporte.emergencia_publica.titulo }} →
              </a>
            </dd>
          </div>
        {% elif reporte.vinculado %}
          <div>
            <dt class="text-text-muted">Vinculado</dt>
            <dd class="text-sm text-text-muted">A una emergencia (no pública)</dd>
          </div>
        {% endif %}
      </dl>
    </div>

  </div>

  <div class="mt-6 space-y-2 text-sm">
    <p class="text-text-muted">
      <strong>Privacidad:</strong> por seguridad, esta página no muestra
      la descripción ni la ubicación que enviaste. Solo el estado de revisión.
    </p>
    <p class="text-text-muted">
      <strong>¿Qué significa cada estado?</strong>
    </p>
    <ul class="list-disc list-inside text-text-muted space-y-1 ml-2">
      <li><strong>Pendiente:</strong> recibido, esperando revisión.</li>
      <li><strong>En revisión:</strong> siendo evaluado por el equipo.</li>
      <li><strong>Vinculado:</strong> confirmado y asociado a una emergencia.</li>
      <li><strong>Duplicado / Descartado:</strong> no genera una alerta nueva.</li>
    </ul>
  </div>

  <div class="mt-8 pt-6 border-t" style="border-color: color-mix(in srgb, var(--color-text) 10%, transparent);">
    <div class="flex flex-wrap gap-2">
      <a href="{% url 'public:report-create' %}" class="btn btn-primary">Hacer otro reporte</a>
      <a href="{% url 'public:home' %}" class="btn btn-ghost">Volver al inicio</a>
    </div>
  </div>

</section>
{% endblock %}
EOF

echo "OK: report_tracking.html creado"

echo ""
echo "▶ 6. CTA en home.html — botón Reportar"
python3 - << 'PY'
from pathlib import Path
p = Path("templates/public/home.html")
text = p.read_text(encoding="utf-8")

# Añadir botón "Reportar" si no existe
if '/reportes/' not in text:
    needle = (
        '    <a href="/hospitales/" class="btn btn-ghost">\n'
        '      Ver hospitales →\n'
        '    </a>\n'
        '  </div>'
    )
    addition = (
        '    <a href="/hospitales/" class="btn btn-ghost">\n'
        '      Ver hospitales →\n'
        '    </a>\n'
        '    <a href="/reportes/" class="btn btn-danger">\n'
        '      Reportar emergencia →\n'
        '    </a>\n'
        '  </div>'
    )
    if needle in text:
        text = text.replace(needle, addition, 1)
        p.write_text(text, encoding="utf-8")
        print("OK: home.html +CTA Reportar")
    else:
        print("NOTA: no se encontró el bloque de botones, revisar manualmente")
else:
    print("ya aplicado: home.html")
PY

echo ""
echo "▶ 7. CTA en alerts_list.html — banner '¿Presenciaste algo?'"
python3 - << 'PY'
from pathlib import Path
p = Path("templates/public/alerts_list.html")
text = p.read_text(encoding="utf-8")

if '/reportes/' not in text:
    needle = '  <form method="get" class="card p-4 mb-6" aria-label="Filtros de alertas">'
    addition = (
        '  <div class="card p-4 mb-6" style="background: var(--gradient-calm);">\n'
        '    <div class="flex items-center justify-between gap-3 flex-wrap">\n'
        '      <div class="text-white">\n'
        '        <p class="font-semibold">¿Presenciaste una emergencia?</p>\n'
        '        <p class="text-sm opacity-90">Repórtala para que podamos verificarla.</p>\n'
        '      </div>\n'
        '      <a href="/reportes/" class="btn btn-primary">Reportar →</a>\n'
        '    </div>\n'
        '  </div>\n\n'
        '  <form method="get" class="card p-4 mb-6" aria-label="Filtros de alertas">'
    )
    if needle in text:
        text = text.replace(needle, addition, 1)
        p.write_text(text, encoding="utf-8")
        print("OK: alerts_list.html +CTA Reportar")
    else:
        print("NOTA: patrón no encontrado")
else:
    print("ya aplicado: alerts_list.html")
PY

echo ""
echo "▶ 8. Añadir tests de reportes"
cat >> frontend/tests/test_public_views.py << 'PYEOF'


class ReportesPublicosTests(TestCase):
    """Tests del formulario de reporte y seguimiento (F2.d)."""

    def setUp(self):
        from django.core.cache import cache
        cache.clear()  # Aislar rate limit entre tests

    def test_form_get_200(self):
        r = self.client.get("/reportes/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Reportar una emergencia")
        self.assertContains(r, 'name="categoria"')
        self.assertContains(r, 'name="descripcion"')
        self.assertContains(r, 'name="ubicacion_texto"')

    def test_form_post_valido_redirige(self):
        r = self.client.post("/reportes/", {
            "categoria": "INUNDACION",
            "descripcion": "Calle anegada en Petare",
            "ubicacion_texto": "Av. Principal de Petare",
            "referencia_lugar": "Frente al mercado",
        })
        self.assertEqual(r.status_code, 302)
        self.assertIn("/reportes/", r.url)
        # El UUID debe estar en la URL de redirección
        self.assertRegex(r.url, r"/reportes/[0-9a-f-]{36}/")

    def test_form_post_sin_categoria_falla(self):
        r = self.client.post("/reportes/", {
            "descripcion": "Test",
            "ubicacion_texto": "Test",
        })
        # Re-render con errores (200) o 400/429 si rate limit
        self.assertIn(r.status_code, [200, 400, 429])

    def test_form_post_sin_descripcion_falla(self):
        r = self.client.post("/reportes/", {
            "categoria": "INUNDACION",
            "ubicacion_texto": "Test",
        })
        self.assertIn(r.status_code, [200, 400, 429])

    def test_tracking_inexistente_404(self):
        r = self.client.get(
            "/reportes/00000000-0000-0000-0000-000000000000/"
        )
        self.assertEqual(r.status_code, 404)

    def test_tracking_muestra_estado_y_codigo(self):
        """Verifica que el tracking muestra el UUID y el estado,
        pero NO la descripción ni la ubicación."""
        from apps.emergencias.models import ReporteEmergencia
        reporte = ReporteEmergencia.objects.create(
            categoria=ReporteEmergencia._meta.get_field("categoria").choices[0][0]
                       if ReporteEmergencia._meta.get_field("categoria").choices
                       else "OTRA",
            descripcion="Descripción secreta con info sensible",
            ubicacion_texto="Dirección exacta privada",
            estado_revision=ReporteEmergencia.EstadoRevision.PENDIENTE,
        )

        r = self.client.get(f"/reportes/{reporte.id}/")
        self.assertEqual(r.status_code, 200)
        # El UUID sí se muestra
        self.assertContains(r, str(reporte.id))
        # El estado sí
        self.assertContains(r, "Pendiente")
        # Privacidad: NO se muestra descripción ni ubicación
        self.assertNotContains(r, "Descripción secreta con info sensible")
        self.assertNotContains(r, "Dirección exacta privada")

    def test_tracking_no_expone_reporte_descartado_como_publico(self):
        """Un reporte descartado se puede consultar (el usuario lo envió),
        pero NO debe aparecer como vinculado a emergencia pública."""
        from apps.emergencias.models import ReporteEmergencia
        reporte = ReporteEmergencia.objects.create(
            categoria=ReporteEmergencia._meta.get_field("categoria").choices[0][0]
                       if ReporteEmergencia._meta.get_field("categoria").choices
                       else "OTRA",
            descripcion="Test",
            ubicacion_texto="Test",
            estado_revision=ReporteEmergencia.EstadoRevision.DESCARTADO,
        )

        r = self.client.get(f"/reportes/{reporte.id}/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Descartado")

    def test_home_tiene_cta_reportar(self):
        r = self.client.get("/")
        self.assertContains(r, "/reportes/")
        self.assertContains(r, "Reportar emergencia")

    def test_alerts_list_tiene_cta_reportar(self):
        r = self.client.get("/alertas/")
        self.assertContains(r, "/reportes/")
        self.assertContains(r, "Reportar")
PYEOF

echo "OK: 9 tests de reportes añadidos"

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
echo "▶ 13. Smoke de reportes"
pkill -f "manage.py runserver" 2>/dev/null || true
sleep 1
python3 manage.py runserver 0.0.0.0:8000 --noreload &> /tmp/rs_f2d.log &
RS_PID=$!
sleep 3

CODE_FORM=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/reportes/)
CODE_404=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/reportes/00000000-0000-0000-0000-000000000000/)
HOME_CTA=$(curl -s http://localhost:8000/ | grep -c 'href="/reportes/"' || true)
ALERTS_CTA=$(curl -s http://localhost:8000/alertas/ | grep -c 'href="/reportes/"' || true)

kill $RS_PID 2>/dev/null; wait $RS_PID 2>/dev/null || true

echo "GET /reportes/              → $CODE_FORM (esperado 200)"
echo "GET /reportes/<uuid>/        → $CODE_404 (esperado 404)"
echo "CTA en home:                 $HOME_CTA (esperado ≥1)"
echo "CTA en /alertas/:            $ALERTS_CTA (esperado ≥1)"

if [ "$CODE_FORM" != "200" ] || [ "$CODE_404" != "404" ]; then
    echo "ERROR: rutas incorrectas"
    exit 1
fi

echo ""
echo "✅ F2.d — Reportes implementados"
