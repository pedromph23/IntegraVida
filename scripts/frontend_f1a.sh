#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

echo "▶ 1. Crear app Django frontend/"
mkdir -p frontend/views frontend/urls frontend/templatetags frontend/tests

# ── frontend/__init__.py ──
touch frontend/__init__.py
touch frontend/views/__init__.py
touch frontend/urls/__init__.py
touch frontend/templatetags/__init__.py
touch frontend/tests/__init__.py

# ── frontend/apps.py ──
cat > frontend/apps.py << 'EOF'
from django.apps import AppConfig


class FrontendConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "frontend"
    verbose_name = "Frontend"
EOF

# ── frontend/views/public.py (home con datos reales) ──
cat > frontend/views/public.py << 'EOF'
"""Vistas del portal público — sin registro (§6.1)."""

from django.conf import settings
from django.shortcuts import render
from django.views.decorators.http import require_GET

from apps.emergencias.models import Emergencia
from apps.hospitales.models import Hospital
from apps.refugios.models import Refugio


ESTADOS_EMERGENCIA_PUBLICOS = [
    Emergencia.Estado.CONFIRMADA,
    Emergencia.Estado.EN_ATENCION,
    Emergencia.Estado.RESUELTA,
]

ESTADOS_REFUGIO_PUBLICOS = [
    Refugio.EstadoOperativo.ACTIVO,
    Refugio.EstadoOperativo.LLENO,
]

ESTADOS_HOSPITAL_PUBLICOS = [
    Hospital.EstadoOperativo.DISPONIBLE,
    Hospital.EstadoOperativo.SATURADO,
]


@require_GET
def home(request):
    """Home del portal público con conteos agregados."""
    contexto = {
        "stats": {
            "emergencias_publicas": Emergencia.objects.filter(
                estado__in=ESTADOS_EMERGENCIA_PUBLICOS,
            ).count(),
            "refugios_activos": Refugio.objects.filter(
                estado_operativo__in=ESTADOS_REFUGIO_PUBLICOS,
            ).count(),
            "hospitales_activos": Hospital.objects.filter(
                estado_operativo__in=ESTADOS_HOSPITAL_PUBLICOS,
            ).count(),
        },
    }
    return render(request, "public/home.html", contexto)


@require_GET
def design_system(request):
    """Demo del sistema de diseño. Solo en DEBUG."""
    if not settings.DEBUG:
        from django.http import Http404
        raise Http404()
    return render(request, "public/design_system.html", {})
EOF

# ── frontend/urls/public.py ──
cat > frontend/urls/public.py << 'EOF'
from django.urls import path

from frontend.views import public

app_name = "public"

urlpatterns = [
    path("", public.home, name="home"),
    path("design-system/", public.design_system, name="design-system"),
]
EOF

# ── frontend/templatetags/ui_extras.py ──
cat > frontend/templatetags/ui_extras.py << 'EOF'
"""Filtros y tags de presentación (sin lógica de negocio)."""

from django import template

register = template.Library()


@register.filter
def badge_class(estado: str) -> str:
    """Mapea un estado a clase CSS de badge."""
    mapping = {
        "CONFIRMADA": "badge-danger",
        "EN_ATENCION": "badge-warning",
        "RESUELTA": "badge-success",
        "ACTIVO": "badge-success",
        "LLENO": "badge-warning",
        "DISPONIBLE": "badge-success",
        "SATURADO": "badge-warning",
    }
    return mapping.get(estado, "badge-info")
EOF

echo "OK: app frontend/ creada"

echo ""
echo "▶ 2. Crear templates base y layouts"
mkdir -p templates/base templates/layouts templates/public templates/components

# ── base_public.html ──
cat > templates/base/base_public.html << 'EOF'
{% load static %}<!DOCTYPE html>
<html lang="es" data-theme="light">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="csrf-token" content="{{ csrf_token }}">
  <title>{% block title %}IntegraVida{% endblock %}</title>

  <link rel="stylesheet" href="{% static 'css/dist/main.css' %}">

  <script>
    (function () {
      try {
        var t = localStorage.getItem('iv-theme') || 'system';
        var effective = t === 'system'
          ? (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
          : t;
        document.documentElement.setAttribute('data-theme', effective);
      } catch (e) { /* noop */ }
    })();
  </script>
</head>
<body class="min-h-screen flex flex-col">

  {% include "layouts/public_header.html" %}

  <main id="main" class="flex-1">
    {% block content %}{% endblock %}
  </main>

  {% include "layouts/public_footer.html" %}

  <div id="toast-container" aria-live="polite" aria-atomic="true"
       class="fixed bottom-4 right-4 z-50 space-y-2"></div>

  <script src="{% static 'js/dist/main.js' %}" defer></script>
  {% block scripts %}{% endblock %}
</body>
</html>
EOF

# ── base_dashboard.html ──
cat > templates/base/base_dashboard.html << 'EOF'
{% load static %}<!DOCTYPE html>
<html lang="es" data-theme="light">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="csrf-token" content="{{ csrf_token }}">
  <title>{% block title %}Panel — IntegraVida{% endblock %}</title>
  <link rel="stylesheet" href="{% static 'css/dist/main.css' %}">
  <script>
    (function () {
      try {
        var t = localStorage.getItem('iv-theme') || 'system';
        var effective = t === 'system'
          ? (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
          : t;
        document.documentElement.setAttribute('data-theme', effective);
      } catch (e) { /* noop */ }
    })();
  </script>
</head>
<body class="min-h-screen bg-surface text-text">
  <div class="flex min-h-screen">
    <aside class="w-64 border-r" style="border-color: var(--color-surface-raised);">
      <div class="p-4 border-b" style="border-color: var(--color-surface-raised);">
        <a href="{% url 'public:home' %}" class="text-lg font-semibold text-primary">
          IntegraVida
        </a>
        <div class="text-xs text-text-muted">Panel institucional</div>
      </div>
      <nav class="p-2" aria-label="Navegación principal">
        {% block sidebar %}{% endblock %}
      </nav>
    </aside>
    <div class="flex-1 flex flex-col">
      <header class="border-b px-6 py-3 flex items-center justify-between"
              style="border-color: var(--color-surface-raised);">
        <h1 class="text-lg font-medium">{% block heading %}{% endblock %}</h1>
        <div class="flex items-center gap-3">
          {% include "components/theme-toggle.html" %}
        </div>
      </header>
      <main class="flex-1 p-6">
        {% block content %}{% endblock %}
      </main>
    </div>
  </div>
  <script src="{% static 'js/dist/main.js' %}" defer></script>
  {% block scripts %}{% endblock %}
</body>
</html>
EOF

# ── base_admin.html ──
cat > templates/base/base_admin.html << 'EOF'
{% load static %}<!DOCTYPE html>
<html lang="es" data-theme="light">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="robots" content="noindex, nofollow, noarchive">
  <meta name="csrf-token" content="{{ csrf_token }}">
  <title>{% block title %}Admin — IntegraVida{% endblock %}</title>
  <link rel="stylesheet" href="{% static 'css/dist/main.css' %}">
  <script>
    (function () {
      try {
        var t = localStorage.getItem('iv-theme') || 'system';
        var effective = t === 'system'
          ? (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
          : t;
        document.documentElement.setAttribute('data-theme', effective);
      } catch (e) { /* noop */ }
    })();
  </script>
</head>
<body class="min-h-screen bg-surface text-text">
  <div class="mx-auto max-w-5xl p-6">
    {% block content %}{% endblock %}
  </div>
  <script src="{% static 'js/dist/main.js' %}" defer></script>
  {% block scripts %}{% endblock %}
</body>
</html>
EOF

# ── public_header.html ──
cat > templates/layouts/public_header.html << 'EOF'
<header class="border-b" style="border-color: var(--color-surface-raised);">
  <div class="mx-auto max-w-7xl px-4 py-3 flex items-center justify-between">
    <a href="{% url 'public:home' %}" class="text-lg font-semibold text-primary">
      IntegraVida
    </a>
    <nav class="flex items-center gap-2" aria-label="Navegación">
      <a href="{% url 'public:home' %}" class="btn btn-ghost text-sm">Inicio</a>
      {% include "components/theme-toggle.html" %}
    </nav>
  </div>
</header>
EOF

# ── public_footer.html ──
cat > templates/layouts/public_footer.html << 'EOF'
<footer class="border-t py-6 mt-12" style="border-color: var(--color-surface-raised);">
  <div class="mx-auto max-w-7xl px-4 text-sm text-text-muted text-center">
    IntegraVida — Conectando recursos y multiplicando esperanzas.
    <span class="mx-2">·</span>
    <a href="/health/" class="underline">Health</a>
  </div>
</footer>
EOF

# ── components/theme-toggle.html ──
cat > templates/components/theme-toggle.html << 'EOF'
<button type="button"
        x-data="{ theme: (window.Alpine ? $store.theme.current : 'system') }"
        @click="$store.theme.cycle(); theme = $store.theme.current"
        :aria-label="'Tema actual: ' + theme"
        class="btn btn-ghost p-2"
        title="Cambiar tema (claro / oscuro / sistema)">
  <span aria-hidden="true" x-show="theme === 'light'">☀</span>
  <span aria-hidden="true" x-show="theme === 'dark'">☾</span>
  <span aria-hidden="true" x-show="theme === 'system'">⌬</span>
</button>
EOF

# ── public/home.html ──
cat > templates/public/home.html << 'EOF'
{% extends "base/base_public.html" %}
{% load static %}

{% block title %}IntegraVida — Portal público{% endblock %}

{% block content %}
<section data-hero class="mx-auto max-w-7xl px-4 py-12 md:py-20">
  <div data-hero-item>
    <h1 class="text-4xl md:text-5xl font-bold text-primary mb-4">
      Encuentra ayuda ahora
    </h1>
    <p class="text-lg text-text-muted max-w-2xl">
      Consulta hospitales, refugios y alertas verificadas durante emergencias.
      Sin registro, sin barreras.
    </p>
  </div>

  <div class="mt-10 grid grid-cols-1 sm:grid-cols-3 gap-4">
    <div class="card p-6" data-hero-item>
      <div class="text-3xl font-bold text-primary">{{ stats.emergencias_publicas }}</div>
      <div class="text-sm text-text-muted mt-1">Emergencias públicas</div>
    </div>
    <div class="card p-6" data-hero-item>
      <div class="text-3xl font-bold text-secondary">{{ stats.refugios_activos }}</div>
      <div class="text-sm text-text-muted mt-1">Refugios activos</div>
    </div>
    <div class="card p-6" data-hero-item>
      <div class="text-3xl font-bold text-accent">{{ stats.hospitales_activos }}</div>
      <div class="text-sm text-text-muted mt-1">Hospitales activos</div>
    </div>
  </div>

  <div class="mt-8 flex flex-wrap gap-3" data-hero-item>
    <a href="/api/publico/emergencias/" class="btn btn-primary">
      Ver emergencias →
    </a>
    <a href="/api/publico/refugios/" class="btn btn-secondary">
      Ver refugios →
    </a>
    <a href="/api/publico/hospitales/" class="btn btn-ghost">
      Ver hospitales →
    </a>
  </div>
</section>
{% endblock %}
EOF

# ── public/design_system.html (placeholder) ──
cat > templates/public/design_system.html << 'EOF'
{% extends "base/base_public.html" %}

{% block title %}Sistema de diseño — IntegraVida{% endblock %}

{% block content %}
<section class="mx-auto max-w-5xl px-4 py-12">
  <h1 class="text-3xl font-bold text-primary mb-2">Sistema de diseño</h1>
  <p class="text-text-muted mb-8">
    Demo de los componentes base. Solo visible en DEBUG.
  </p>

  <div class="space-y-8">
    <div>
      <h2 class="text-xl font-semibold mb-3">Botones</h2>
      <div class="flex flex-wrap gap-3">
        <button class="btn btn-primary">Primario</button>
        <button class="btn btn-secondary">Secundario</button>
        <button class="btn btn-danger">Peligro</button>
        <button class="btn btn-ghost">Ghost</button>
      </div>
    </div>

    <div>
      <h2 class="text-xl font-semibold mb-3">Badges</h2>
      <div class="flex flex-wrap gap-2">
        <span class="badge badge-success">Activo</span>
        <span class="badge badge-warning">Saturado</span>
        <span class="badge badge-danger">Crítico</span>
        <span class="badge badge-info">Info</span>
      </div>
    </div>

    <div>
      <h2 class="text-xl font-semibold mb-3">Card</h2>
      <div class="card p-6">
        <h3 class="text-lg font-medium mb-2">Título de tarjeta</h3>
        <p class="text-text-muted">
          Contenido de la tarjeta. Los gradientes respetan contraste AA.
        </p>
      </div>
    </div>
  </div>
</section>
{% endblock %}
EOF

echo "OK: templates base + layouts + componentes iniciales"

# ── Logo SVG ──
mkdir -p static/img
cat > static/img/logo.svg << 'EOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" aria-label="IntegraVida">
  <defs>
    <linearGradient id="iv-grad" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#7A1F2B"/>
      <stop offset="50%" stop-color="#A8323F"/>
      <stop offset="100%" stop-color="#D98C1F"/>
    </linearGradient>
  </defs>
  <rect width="32" height="32" rx="6" fill="url(#iv-grad)"/>
  <path d="M16 24s-7-4.5-7-10a4 4 0 0 1 7-2.65A4 4 0 0 1 23 14c0 5.5-7 10-7 10z"
        fill="white" opacity="0.95"/>
</svg>
EOF

echo "OK: static/img/logo.svg"

echo ""
echo "▶ 3. Registrar app + montar URLs"
python3 - << 'PY'
from pathlib import Path

# 1) INSTALLED_APPS: añadir 'frontend'
p = Path("config/settings.py")
text = p.read_text(encoding="utf-8")
if "'frontend'," not in text:
    needle = "    'apps.configuracion.apps.ConfiguracionConfig',\n"
    addition = needle + "    'frontend',\n"
    if needle in text:
        text = text.replace(needle, addition, 1)
        p.write_text(text, encoding="utf-8")
        print("OK: 'frontend' en INSTALLED_APPS")
    else:
        raise SystemExit("ERROR: marker ConfiguracionConfig no encontrado")
else:
    print("ya aplicado: 'frontend' en INSTALLED_APPS")

# 2) config/urls.py: reemplazar path("", config_views.index) por include frontend
p = Path("config/urls.py")
text = p.read_text(encoding="utf-8")
old = '    path("", config_views.index, name="index"),\n'
new = '    path("", include("frontend.urls.public")),\n'
if old in text:
    text = text.replace(old, new, 1)
    p.write_text(text, encoding="utf-8")
    print("OK: config/urls.py — frontend montado en raíz")
elif 'include("frontend.urls.public")' in text:
    print("ya aplicado: frontend en urls")
else:
    raise SystemExit("ERROR: marker config_views.index no encontrado")
PY

# 3) Mantener compatibilidad: apps/configuracion/views.py aún tiene index(), lo dejamos.
# No lo borramos por si algún test lo referencia; el health() sigue en uso.

echo ""
echo "▶ 4. Verificación"
python3 manage.py check

echo ""
echo "▶ 5. Verificar imports"
python3 manage.py shell -c "
from frontend.views import public
from frontend.urls import public as urls_public
print('OK: frontend importa')
"
