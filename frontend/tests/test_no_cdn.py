"""§11.5 — Prueba anti-CDN + bundles presentes.

Se ejecuta en CI (pytest / manage.py test) y falla si:
- algún template, src/css o src/js referencia un CDN conocido
- los bundles compilados faltan o están vacíos

Los comentarios Django ({#...#}, {% comment %}...{% endcomment %}) se
eliminan antes de buscar para no generar falsos positivos con ejemplos
documentados dentro de plantillas.
"""
import re
from pathlib import Path

from django.test import SimpleTestCase

ROOT = Path(__file__).resolve().parents[2]
CHECK_DIRS = [
    ROOT / "templates",
    ROOT / "static" / "css" / "src",
    ROOT / "static" / "js" / "src",
]

# Solo CDNs conocidos. Los tiles de mapa (p. ej. tile.openstreetmap.org)
# no figuran aquí por ser configurables por entorno (docs/frontend/local-dependencies.md).
FORBIDDEN = re.compile(
    r"""(?:https?:)?//(?:
        cdn\. |
        unpkg\.com |
        jsdelivr\.net |
        cdnjs\.cloudflare\.com |
        fonts\.googleapis\.com |
        fonts\.gstatic\.com |
        cdn\.tailwindcss\.com |
        ajax\.googleapis\.com |
        code\.jquery\.com
    )""",
    re.VERBOSE | re.IGNORECASE,
)

# Comentarios a eliminar antes de comprobar.
COMMENT_BLOCK = re.compile(r"{%\s*comment\s*%}.*?{%\s*endcomment\s*%}", re.DOTALL)
COMMENT_LINE = re.compile(r"{#.*?#}", re.DOTALL)

def _strip_django_comments(text: str) -> str:
    return COMMENT_LINE.sub("", COMMENT_BLOCK.sub("", text))

class NoCDNTests(SimpleTestCase):
    def test_templates_y_src_sin_cdn(self):
        offenders = []
        for d in CHECK_DIRS:
            if not d.exists():
                continue
            for f in d.rglob("*"):
                if f.suffix not in {".html", ".js", ".css", ".ts"}:
                    continue
                text = _strip_django_comments(
                    f.read_text(encoding="utf-8", errors="ignore")
                )
                for m in FORBIDDEN.finditer(text):
                    offenders.append(f"{f.relative_to(ROOT)}: {m.group(0)}")
        self.assertEqual(offenders, [], f"CDN detectado: {offenders[:10]}")

    def test_bundles_existen_y_no_vacios(self):
        for p in [
            ROOT / "static" / "css" / "dist" / "main.css",
            ROOT / "static" / "js" / "dist" / "main.js",
        ]:
            self.assertTrue(p.exists(), f"Falta bundle: {p}")
            self.assertGreater(p.stat().st_size, 1000, f"Bundle vacío: {p}")
