#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

echo "▶ 1. Crear 10 componentes"

# ── button.html ──
cat > templates/components/button.html << 'EOF'
{% comment %}
Uso:
  {% include "components/button.html" with label="Guardar" variant="primary" %}
  {% include "components/button.html" with label="Cancelar" variant="ghost" %}
  {% include "components/button.html" with label="Eliminar" variant="danger" type="submit" %}
  {% include "components/button.html" with label="Ir" variant="primary" href="/ruta/" %}
Parámetros:
  label       (str)   — texto del botón (obligatorio)
  variant     (str)   — primary | secondary | danger | ghost (default: primary)
  size        (str)   — sm | md | lg (default: md)
  type        (str)   — submit | button | reset (default: button)
  href        (str)   — si se pasa, se renderiza <a> en lugar de <button>
  disabled    (bool)
  icon_left   (str)   — carácter o emoji a la izquierda
  icon_right  (str)
{% endcomment %}
{% with v=variant|default:"primary" s=size|default:"md" t=type|default:"button" %}
{% with base="btn btn-"|add:v %}
{% if s == "sm" %}{% with size_class="px-3 py-1.5 text-sm" %}{% endwith %}{% endif %}
{% if href %}
  <a href="{{ href }}" class="{{ base }} {% if s == 'sm' %}px-3 py-1.5 text-sm{% elif s == 'lg' %}px-6 py-3 text-lg{% endif %} {% if disabled %}pointer-events-none opacity-50{% endif %}">
    {% if icon_left %}<span aria-hidden="true">{{ icon_left }}</span>{% endif %}
    {{ label }}
    {% if icon_right %}<span aria-hidden="true">{{ icon_right }}</span>{% endif %}
  </a>
{% else %}
  <button type="{{ t }}"
          class="{{ base }} {% if s == 'sm' %}px-3 py-1.5 text-sm{% elif s == 'lg' %}px-6 py-3 text-lg{% endif %}"
          {% if disabled %}disabled aria-disabled="true"{% endif %}>
    {% if icon_left %}<span aria-hidden="true">{{ icon_left }}</span>{% endif %}
    {{ label }}
    {% if icon_right %}<span aria-hidden="true">{{ icon_right }}</span>{% endif %}
  </button>
{% endif %}
{% endwith %}
{% endwith %}
EOF

# ── card.html ──
cat > templates/components/card.html << 'EOF'
{% comment %}
Uso:
  {% include "components/card.html" with title="Título" body="Contenido" hover=True %}
Parámetros:
  title       (str)
  body        (str)   — se puede usar {% include %} anidado con `body_html` si es HTML
  body_html   (str)   — HTML seguro (|safe aplicado por el caller)
  footer      (str)
  hover       (bool)  — añade elevación en hover
  variant     (str)   — default | raised (default: raised)
  padding     (str)   — sm | md | lg (default: md)
{% endcomment %}
{% with v=variant|default:"raised" p=padding|default:"md" %}
<article class="card {% if hover %}card-hover{% endif %} {% if p == 'sm' %}p-3{% elif p == 'lg' %}p-8{% else %}p-6{% endif %}"
         {% if v == 'raised' %}style="background-color: var(--color-surface-raised);"{% endif %}>
  {% if title %}
    <h3 class="text-lg font-semibold mb-2">{{ title }}</h3>
  {% endif %}
  <div class="text-text">
    {% if body_html %}{{ body_html|safe }}{% elif body %}{{ body }}{% endif %}
  </div>
  {% if footer %}
    <footer class="mt-4 pt-4 border-t text-sm text-text-muted"
            style="border-color: color-mix(in srgb, var(--color-text) 10%, transparent);">
      {{ footer }}
    </footer>
  {% endif %}
</article>
{% endwith %}
EOF

# ── badge.html ──
cat > templates/components/badge.html << 'EOF'
{% comment %}
Uso:
  {% include "components/badge.html" with label="Activo" variant="success" %}
Parámetros:
  label     (str)
  variant   (str) — success | warning | danger | info (default: info)
  icon      (str) — emoji o carácter
{% endcomment %}
{% with v=variant|default:"info" %}
<span class="badge badge-{{ v }}">
  {% if icon %}<span aria-hidden="true" class="mr-1">{{ icon }}</span>{% endif %}
  {{ label }}
</span>
{% endwith %}
EOF

# ── input.html ──
cat > templates/components/input.html << 'EOF'
{% comment %}
Uso:
  {% include "components/input.html" with name="email" label="Email" type="email" required=True %}
Parámetros:
  name        (str)   — obligatorio
  label       (str)
  type        (str)   — text | email | password | tel | number | date | search (default: text)
  value       (str)
  placeholder (str)
  required    (bool)
  disabled    (bool)
  help_text   (str)
  errors      (list[str]) — errores de validación (backend o frontend)
  id          (str)   — si no se pasa, se usa "id_" + name
{% endcomment %}
{% with input_id=id|default:"id_"|add:name t=type|default:"text" %}
<div class="space-y-1">
  {% if label %}
    <label for="{{ input_id }}" class="block text-sm font-medium text-text">
      {{ label }}
      {% if required %}<span aria-hidden="true" class="text-danger">*</span>{% endif %}
    </label>
  {% endif %}
  <input
    type="{{ t }}"
    name="{{ name }}"
    id="{{ input_id }}"
    {% if value %}value="{{ value }}"{% endif %}
    {% if placeholder %}placeholder="{{ placeholder }}"{% endif %}
    {% if required %}required aria-required="true"{% endif %}
    {% if disabled %}disabled{% endif %}
    class="input {% if errors %}border-danger-500{% endif %}"
    {% if help_text %}aria-describedby="{{ input_id }}_help"{% endif %}
    {% if errors %}aria-invalid="true" aria-describedby="{{ input_id }}_errors"{% endif %}
  >
  {% if help_text %}
    <p id="{{ input_id }}_help" class="text-xs text-text-muted">{{ help_text }}</p>
  {% endif %}
  {% if errors %}
    <ul id="{{ input_id }}_errors" class="text-xs text-danger-600 space-y-0.5" role="alert">
      {% for err in errors %}<li>{{ err }}</li>{% endfor %}
    </ul>
  {% endif %}
</div>
{% endwith %}
EOF

# ── select.html ──
cat > templates/components/select.html << 'EOF'
{% comment %}
Uso:
  {% include "components/select.html" with name="estado" label="Estado" choices=estados %}
Parámetros:
  name        (str)     — obligatorio
  label       (str)
  choices     (list)    — lista de tuplas (value, label) o dict {value: label}
  value       (str)     — valor actual
  required    (bool)
  help_text   (str)
  errors      (list[str])
  id          (str)
{% endcomment %}
{% with input_id=id|default:"id_"|add:name %}
<div class="space-y-1">
  {% if label %}
    <label for="{{ input_id }}" class="block text-sm font-medium text-text">{{ label }}</label>
  {% endif %}
  <select
    name="{{ name }}"
    id="{{ input_id }}"
    class="input"
    {% if required %}required aria-required="true"{% endif %}
    {% if errors %}aria-invalid="true"{% endif %}
  >
    <option value="">—</option>
    {% for c in choices %}
      {% if c.0 is not None %}
        <option value="{{ c.0 }}" {% if c.0 == value %}selected{% endif %}>{{ c.1 }}</option>
      {% else %}
        <option value="{{ c.0 }}" {% if c.0 == value %}selected{% endif %}>{{ c }}</option>
      {% endif %}
    {% endfor %}
  </select>
  {% if help_text %}<p class="text-xs text-text-muted">{{ help_text }}</p>{% endif %}
  {% if errors %}
    <ul class="text-xs text-danger-600 space-y-0.5" role="alert">
      {% for err in errors %}<li>{{ err }}</li>{% endfor %}
    </ul>
  {% endif %}
</div>
{% endwith %}
EOF

# ── textarea.html ──
cat > templates/components/textarea.html << 'EOF'
{% comment %}
Uso:
  {% include "components/textarea.html" with name="mensaje" label="Mensaje" rows=4 %}
Parámetros:
  name, label, value, placeholder, rows (default 3),
  required, help_text, errors, id
{% endcomment %}
{% with input_id=id|default:"id_"|add:name r=rows|default:3 %}
<div class="space-y-1">
  {% if label %}
    <label for="{{ input_id }}" class="block text-sm font-medium text-text">{{ label }}</label>
  {% endif %}
  <textarea
    name="{{ name }}"
    id="{{ input_id }}"
    rows="{{ r }}"
    class="input"
    {% if placeholder %}placeholder="{{ placeholder }}"{% endif %}
    {% if required %}required aria-required="true"{% endif %}
  >{% if value %}{{ value }}{% endif %}</textarea>
  {% if help_text %}<p class="text-xs text-text-muted">{{ help_text }}</p>{% endif %}
  {% if errors %}
    <ul class="text-xs text-danger-600 space-y-0.5" role="alert">
      {% for err in errors %}<li>{{ err }}</li>{% endfor %}
    </ul>
  {% endif %}
</div>
{% endwith %}
EOF

# ── alert.html ──
cat > templates/components/alert.html << 'EOF'
{% comment %}
Uso:
  {% include "components/alert.html" with variant="success" title="Guardado" body="Los cambios se guardaron." dismissible=True %}
Parámetros:
  variant      (str)  — info | success | warning | danger (default: info)
  title        (str)
  body         (str)
  dismissible  (bool)
  role         (str)  — alert | status (default: alert)
{% endcomment %}
{% with v=variant|default:"info" r=role|default:"alert" %}
<div role="{{ r }}"
     class="rounded-lg p-4 border-l-4 animate-slide-in-right"
     data-alert-auto-dismiss
     {% if not dismissible %}data-alert-persistent="true"{% endif %}
     style="
       border-left-color: var(--color-{{ v|default:'primary' }});
       background-color: color-mix(in srgb, var(--color-{{ v|default:'primary' }}) 8%, var(--color-surface));
     ">
  <div class="flex items-start justify-between gap-3">
    <div>
      {% if title %}<h3 class="font-semibold mb-1">{{ title }}</h3>{% endif %}
      {% if body %}<p class="text-sm text-text">{{ body }}</p>{% endif %}
    </div>
    {% if dismissible %}
      <button type="button"
              class="btn btn-ghost p-1 text-sm"
              aria-label="Cerrar alerta"
              onclick="this.closest('[role]').remove()">
        ×
      </button>
    {% endif %}
  </div>
</div>
{% endwith %}
EOF

# ── modal.html ──
cat > templates/components/modal.html << 'EOF'
{% comment %}
Uso:
  {% include "components/modal.html" with id="modal-confirm" title="¿Eliminar?" body="Esta acción no se puede deshacer." confirm_label="Eliminar" confirm_variant="danger" %}
  Y el botón que lo abre:
  <button data-modal-open="modal-confirm" class="btn btn-danger">Eliminar</button>
Parámetros:
  id               (str)  — obligatorio, ID único
  title            (str)
  body             (str)
  confirm_label    (str)  — default "Aceptar"
  cancel_label     (str)  — default "Cancelar"
  confirm_variant  (str)  — primary | danger | secondary (default: primary)
  size             (str)  — sm | md | lg (default: md)
{% endcomment %}
{% with s=size|default:"md" %}
<div id="{{ id }}"
     role="dialog"
     aria-modal="true"
     aria-labelledby="{{ id }}_title"
     hidden
     class="fixed inset-0 z-50 flex items-center justify-center p-4"
     style="background-color: color-mix(in srgb, black 50%, transparent);">
  <div class="card {% if s == 'sm' %}max-w-sm{% elif s == 'lg' %}max-w-2xl{% else %}max-w-md{% endif %} w-full p-6"
       style="background-color: var(--color-surface-overlay);">
    {% if title %}
      <h2 id="{{ id }}_title" class="text-lg font-semibold mb-3">{{ title }}</h2>
    {% endif %}
    {% if body %}<p class="text-text mb-6">{{ body }}</p>{% endif %}
    <div class="flex justify-end gap-2">
      <button type="button" class="btn btn-ghost" data-modal-close>
        {{ cancel_label|default:"Cancelar" }}
      </button>
      {% if confirm_label %}
        <button type="button"
                class="btn btn-{{ confirm_variant|default:'primary' }}"
                data-modal-close>
          {{ confirm_label }}
        </button>
      {% endif %}
    </div>
  </div>
</div>
{% endwith %}
EOF

# ── skeleton.html ──
cat > templates/components/skeleton.html << 'EOF'
{% comment %}
Uso:
  {% include "components/skeleton.html" with variant="card" %}
Parámetros:
  variant  (str) — text | card | avatar (default: text)
  count    (int) — número de líneas/items (default: 1)
{% endcomment %}
{% with v=variant|default:"text" c=count|default:1 %}
{% if v == "avatar" %}
  <div class="skeleton rounded-full" style="width: 40px; height: 40px;"></div>
{% elif v == "card" %}
  <div class="card p-6 space-y-3">
    <div class="skeleton h-4 w-3/4"></div>
    <div class="skeleton h-3 w-full"></div>
    <div class="skeleton h-3 w-5/6"></div>
  </div>
{% else %}
  {% for i in "x"|rjust:c %}
    <div class="skeleton h-4 w-full mb-2"></div>
  {% endfor %}
{% endif %}
{% endwith %}
EOF

# ── empty-state.html ──
cat > templates/components/empty-state.html << 'EOF'
{% comment %}
Uso:
  {% include "components/empty-state.html" with title="Sin resultados" description="No hay datos para mostrar." action_label="Crear" action_url="/crear/" %}
Parámetros:
  icon          (str) — emoji opcional
  title         (str)
  description   (str)
  action_label  (str)
  action_url    (str)
{% endcomment %}
<div class="text-center py-12">
  {% if icon %}
    <div class="text-5xl mb-4" aria-hidden="true">{{ icon }}</div>
  {% endif %}
  {% if title %}
    <h3 class="text-lg font-medium text-text mb-2">{{ title }}</h3>
  {% endif %}
  {% if description %}
    <p class="text-sm text-text-muted max-w-md mx-auto">{{ description }}</p>
  {% endif %}
  {% if action_label and action_url %}
    <div class="mt-6">
      <a href="{{ action_url }}" class="btn btn-primary">{{ action_label }}</a>
    </div>
  {% endif %}
</div>
EOF

echo "OK: 10 componentes creados"

echo ""
echo "▶ 2. Tests de componentes"
cat > frontend/tests/test_components.py << 'EOF'
"""Tests de renderizado de componentes (F1.b)."""
from django.template.loader import render_to_string
from django.test import TestCase


def render(template, ctx=None):
    return render_to_string(template, ctx or {})


class ButtonComponentTests(TestCase):
    def test_boton_primary(self):
        html = render("components/button.html", {
            "label": "Guardar", "variant": "primary",
        })
        self.assertIn("btn-primary", html)
        self.assertIn("Guardar", html)
        self.assertIn("<button", html)

    def test_boton_como_link(self):
        html = render("components/button.html", {
            "label": "Ir", "variant": "primary", "href": "/ruta/",
        })
        self.assertIn("<a href=\"/ruta/\"", html)

    def test_boton_danger(self):
        html = render("components/button.html", {
            "label": "Eliminar", "variant": "danger",
        })
        self.assertIn("btn-danger", html)


class CardComponentTests(TestCase):
    def test_card_con_titulo_y_body(self):
        html = render("components/card.html", {
            "title": "Título", "body": "Contenido",
        })
        self.assertIn("Título", html)
        self.assertIn("Contenido", html)

    def test_card_con_hover(self):
        html = render("components/card.html", {
            "title": "T", "body": "B", "hover": True,
        })
        self.assertIn("card-hover", html)


class BadgeComponentTests(TestCase):
    def test_badge_success(self):
        html = render("components/badge.html", {
            "label": "Activo", "variant": "success",
        })
        self.assertIn("badge-success", html)
        self.assertIn("Activo", html)

    def test_badge_default_info(self):
        html = render("components/badge.html", {"label": "Info"})
        self.assertIn("badge-info", html)


class InputComponentTests(TestCase):
    def test_input_basico(self):
        html = render("components/input.html", {
            "name": "email", "label": "Email", "type": "email",
        })
        self.assertIn('name="email"', html)
        self.assertIn('type="email"', html)
        self.assertIn("Email", html)
        self.assertIn('id="id_email"', html)

    def test_input_con_errores(self):
        html = render("components/input.html", {
            "name": "tel", "label": "Teléfono",
            "errors": ["Formato inválido", "Requerido"],
        })
        self.assertIn("aria-invalid=\"true\"", html)
        self.assertIn("Formato inválido", html)
        self.assertIn("Requerido", html)

    def test_input_required(self):
        html = render("components/input.html", {
            "name": "x", "label": "X", "required": True,
        })
        self.assertIn("required", html)
        self.assertIn("aria-required=\"true\"", html)


class SelectComponentTests(TestCase):
    def test_select_con_choices(self):
        html = render("components/select.html", {
            "name": "estado", "label": "Estado",
            "choices": [("A", "Activo"), ("B", "Bloqueado")],
        })
        self.assertIn("Activo", html)
        self.assertIn("Bloqueado", html)
        self.assertIn("<select", html)


class TextareaComponentTests(TestCase):
    def test_textarea_rows(self):
        html = render("components/textarea.html", {
            "name": "msg", "label": "Mensaje", "rows": 5,
        })
        self.assertIn('rows="5"', html)
        self.assertIn("<textarea", html)


class AlertComponentTests(TestCase):
    def test_alert_danger_dismissible(self):
        html = render("components/alert.html", {
            "variant": "danger", "title": "Error", "body": "Algo salió mal",
            "dismissible": True,
        })
        self.assertIn("Error", html)
        self.assertIn("Algo salió mal", html)
        self.assertIn("Cerrar alerta", html)

    def test_alert_persistente(self):
        html = render("components/alert.html", {
            "variant": "info", "title": "Info",
        })
        self.assertIn('data-alert-persistent="true"', html)


class ModalComponentTests(TestCase):
    def test_modal_estructura(self):
        html = render("components/modal.html", {
            "id": "modal-confirm",
            "title": "¿Eliminar?",
            "body": "Esta acción no se puede deshacer.",
            "confirm_label": "Eliminar",
            "confirm_variant": "danger",
        })
        self.assertIn('id="modal-confirm"', html)
        self.assertIn('role="dialog"', html)
        self.assertIn("¿Eliminar?", html)
        self.assertIn("data-modal-close", html)
        self.assertIn("btn-danger", html)


class SkeletonComponentTests(TestCase):
    def test_skeleton_card(self):
        html = render("components/skeleton.html", {"variant": "card"})
        self.assertIn("skeleton", html)

    def test_skeleton_text_count(self):
        html = render("components/skeleton.html", {"variant": "text", "count": 3})
        self.assertEqual(html.count("skeleton h-4"), 3)


class EmptyStateComponentTests(TestCase):
    def test_empty_state_con_accion(self):
        html = render("components/empty-state.html", {
            "title": "Sin resultados",
            "description": "No hay datos.",
            "action_label": "Crear",
            "action_url": "/crear/",
        })
        self.assertIn("Sin resultados", html)
        self.assertIn("/crear/", html)
        self.assertIn("Crear", html)
EOF

echo "OK: frontend/tests/test_components.py (16 tests)"

echo ""
echo "▶ 3. Actualizar design_system.html con TODOS los componentes"
cat > templates/public/design_system.html << 'EOF'
{% extends "base/base_public.html" %}
{% load ui_extras %}

{% block title %}Sistema de diseño — IntegraVida{% endblock %}

{% block content %}
<section class="mx-auto max-w-5xl px-4 py-12 space-y-12">

  <header>
    <h1 class="text-3xl font-bold text-primary mb-2">Sistema de diseño</h1>
    <p class="text-text-muted">
      Catálogo de componentes base. Solo visible en <code>DEBUG=True</code>.
      Verificar contraste en ambos temas con <code>axe-core</code>.
    </p>
  </header>

  <section>
    <h2 class="text-xl font-semibold mb-4 pb-2 border-b">1. Botones</h2>
    <div class="space-y-4">
      <div class="flex flex-wrap gap-3">
        {% include "components/button.html" with label="Primario" variant="primary" %}
        {% include "components/button.html" with label="Secundario" variant="secondary" %}
        {% include "components/button.html" with label="Peligro" variant="danger" %}
        {% include "components/button.html" with label="Ghost" variant="ghost" %}
      </div>
      <div class="flex flex-wrap gap-3 items-center">
        {% include "components/button.html" with label="Small" variant="primary" size="sm" %}
        {% include "components/button.html" with label="Medium" variant="primary" %}
        {% include "components/button.html" with label="Large" variant="primary" size="lg" %}
      </div>
      <div class="flex flex-wrap gap-3">
        {% include "components/button.html" with label="Deshabilitado" variant="primary" disabled=True %}
        {% include "components/button.html" with label="Con icono" variant="secondary" icon_right="→" %}
        {% include "components/button.html" with label="Como link" variant="ghost" href="/" %}
      </div>
    </div>
  </section>

  <section>
    <h2 class="text-xl font-semibold mb-4 pb-2 border-b">2. Badges</h2>
    <div class="flex flex-wrap gap-2">
      {% include "components/badge.html" with label="Activo" variant="success" %}
      {% include "components/badge.html" with label="Saturado" variant="warning" %}
      {% include "components/badge.html" with label="Crítico" variant="danger" %}
      {% include "components/badge.html" with label="Info" variant="info" %}
      {% include "components/badge.html" with label="Con icono" variant="success" icon="✓" %}
    </div>
  </section>

  <section>
    <h2 class="text-xl font-semibold mb-4 pb-2 border-b">3. Cards</h2>
    <div class="grid md:grid-cols-2 gap-4">
      {% include "components/card.html" with title="Card básico" body="Contenido simple de una tarjeta." %}
      {% include "components/card.html" with title="Card con hover" body="Elevación al pasar el mouse." hover=True %}
    </div>
  </section>

  <section>
    <h2 class="text-xl font-semibold mb-4 pb-2 border-b">4. Formularios</h2>
    <div class="grid md:grid-cols-2 gap-4 max-w-2xl">
      {% include "components/input.html" with name="nombre" label="Nombre" help_text="Como aparece en tu documento." %}
      {% include "components/input.html" with name="email" label="Email" type="email" required=True %}
      {% include "components/input.html" with name="tel" label="Teléfono" type="tel" errors="Formato inválido" %}
      {% include "components/select.html" with name="estado" label="Estado" choices=estados_demo %}
      {% include "components/textarea.html" with name="mensaje" label="Mensaje" rows=3 %}
    </div>
  </section>

  <section>
    <h2 class="text-xl font-semibold mb-4 pb-2 border-b">5. Alerts</h2>
    <div class="space-y-3">
      {% include "components/alert.html" with variant="info" title="Información" body="Mensaje informativo." dismissible=True %}
      {% include "components/alert.html" with variant="success" title="Éxito" body="Operación completada." dismissible=True %}
      {% include "components/alert.html" with variant="warning" title="Aviso" body="Revisa los datos antes de continuar." dismissible=True %}
      {% include "components/alert.html" with variant="danger" title="Error" body="Ocurrió un problema." dismissible=True %}
    </div>
  </section>

  <section>
    <h2 class="text-xl font-semibold mb-4 pb-2 border-b">6. Modal</h2>
    <button class="btn btn-danger" data-modal-open="modal-demo">
      Abrir modal de ejemplo
    </button>
    {% include "components/modal.html" with id="modal-demo" title="¿Eliminar registro?" body="Esta acción no se puede deshacer." confirm_label="Eliminar" confirm_variant="danger" %}
  </section>

  <section>
    <h2 class="text-xl font-semibold mb-4 pb-2 border-b">7. Skeleton</h2>
    <div class="grid md:grid-cols-2 gap-4">
      <div>
        <p class="text-sm text-text-muted mb-2">Texto (3 líneas):</p>
        {% include "components/skeleton.html" with variant="text" count=3 %}
      </div>
      <div>
        <p class="text-sm text-text-muted mb-2">Card:</p>
        {% include "components/skeleton.html" with variant="card" %}
      </div>
    </div>
  </section>

  <section>
    <h2 class="text-xl font-semibold mb-4 pb-2 border-b">8. Empty state</h2>
    {% include "components/empty-state.html" with icon="○" title="Sin resultados" description="No encontramos datos para mostrar." action_label="Volver al inicio" action_url="/" %}
  </section>

</section>
{% endblock %}
EOF

# El template usa `estados_demo`; añadir al contexto de la vista
python3 - << 'PY'
from pathlib import Path
p = Path("frontend/views/public.py")
text = p.read_text(encoding="utf-8")

old = '''    if not settings.DEBUG:
        from django.http import Http404
        raise Http404()
    return render(request, "public/design_system.html", {})'''

new = '''    if not settings.DEBUG:
        from django.http import Http404
        raise Http404()
    return render(request, "public/design_system.html", {
        "estados_demo": [
            ("ACTIVO", "Activo"),
            ("LLENO", "Lleno"),
            ("CERRADO", "Cerrado"),
        ],
    })'''

if old in text:
    text = text.replace(old, new, 1)
    p.write_text(text, encoding="utf-8")
    print("OK: design_system context actualizado")
elif 'estados_demo' in text:
    print("ya aplicado: design_system context")
else:
    raise SystemExit("ERROR: bloque design_system no encontrado")
PY

echo "OK: design_system.html actualizado"

echo ""
echo "▶ 4. Rebuild CSS (nuevos componentes usan clases Tailwind)"
NODE_ENV=production npx tailwindcss \
  -i ./static/css/src/main.css \
  -o ./static/css/dist/main.css \
  --minify

echo "CSS gzip: $(gzip -c static/css/dist/main.css | wc -c) bytes"

echo ""
echo "▶ 5. Anti-CDN"
bash scripts/check-no-cdn.sh

echo ""
echo "▶ 6. Tests componentes"
python3 manage.py test frontend.tests.test_components -v 2 2>&1 | tail -10

echo ""
echo "▶ 7. Tests frontend completos"
python3 manage.py test frontend -v 1 2>&1 | tail -4

echo ""
echo "▶ 8. Suite configuración + frontend"
python3 manage.py test apps.configuracion frontend -v 1 2>&1 | tail -4

echo ""
echo "✅ F1.b — componentes completados"
