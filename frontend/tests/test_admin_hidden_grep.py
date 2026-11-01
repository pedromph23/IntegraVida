"""Tests de F4.e — grep del slug del admin en templates.

El slug del admin NO debe aparecer hardcoded en ningún template público
ni del panel. Solo debe resolverse vía {% url 'admin:index' %} cuando
el usuario ya está autenticado como staff.
"""
from pathlib import Path

from django.conf import settings
from django.test import TestCase


class SlugNoEnTemplatesPublicosTests(TestCase):
    """Grep recursivo en templates/ — excluye los admin_custom (que solo
    renderizan para staff autenticado con MFA)."""

    def setUp(self):
        self.slug = settings.INTEGRAVIDA_ADMIN_SLUG
        self.base = Path(__file__).resolve().parent.parent.parent / "templates"

    def _templates_a_verificar(self):
        # Directorios públicos, panel, componentes, layouts, base,
        # auth, errors. Excluimos admin_custom/ porque solo se renderiza
        # a staff autenticado con MFA (el slug puede aparecer en <a href>
        # resuelto por {% url 'admin:index' %}, pero nunca hardcoded).
        dirs = [
            "public",
            "layouts",
            "components",
            "auth",
            "dashboard",
            "errors",
        ]
        for d in dirs:
            dir_ = self.base / d
            if not dir_.exists():
                continue
            yield from dir_.rglob("*.html")
        # base/ — excluye base_admin*.html
        base_dir = self.base / "base"
        if base_dir.exists():
            for f in base_dir.rglob("*.html"):
                if "admin" in f.name:
                    continue
                yield f
        # index.html (landing F0, si existe)
        idx = self.base / "index.html"
        if idx.exists():
            yield idx

    def test_no_slug_hardcoded_en_templates(self):
        slug = self.slug
        # Aceptamos que el slug esté vacío en dev solo si está mal configurado
        if not slug:
            self.skipTest("Slug vacío")
        ofensores = []
        for f in self._templates_a_verificar():
            content = f.read_text(encoding="utf-8")
            if slug in content:
                ofensores.append(str(f.relative_to(self.base)))
        self.assertEqual(
            ofensores, [],
            f"Slug '{slug}' hardcoded en: {ofensores}",
        )

    def test_no_href_hardcoded_al_admin(self):
        """Ningún template público debe tener href="/<slug>/..." literal."""
        slug = self.slug
        if not slug:
            self.skipTest("Slug vacío")
        ofensores = []
        for f in self._templates_a_verificar():
            content = f.read_text(encoding="utf-8")
            if f'href="/{slug}/' in content:
                ofensores.append(str(f.relative_to(self.base)))
        self.assertEqual(ofensores, [], f"href hardcoded en: {ofensores}")

    def test_home_no_contiene_slug(self):
        # Doble check: request a home y verificar en HTML renderizado
        from django.test import Client
        client = Client()
        r = client.get("/")
        self.assertNotIn(self.slug, r.content.decode())

    def test_panel_login_no_contiene_slug(self):
        from django.test import Client
        client = Client()
        r = client.get("/panel/login/")
        self.assertNotIn(self.slug, r.content.decode())

    def test_paginas_publicas_no_contienen_slug(self):
        from django.test import Client
        client = Client()
        for path in ("/", "/hospitales/", "/refugios/", "/alertas/"):
            r = client.get(path)
            self.assertEqual(r.status_code, 200, f"Fallo en {path}")
            self.assertNotIn(
                self.slug, r.content.decode(),
                f"Slug expuesto en {path}",
            )
