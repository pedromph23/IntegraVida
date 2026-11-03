"""§11 — Comprobaciones estáticas de accesibilidad (sin axe-core).

Detecta regresiones típicas en plantillas antes de entrar a Playwright:
- <img> sin alt
- <a> sin href
- <button> sin type
- <input> visible sin id / aria-* (excluye hidden, submit, button, reset, image)

Las pruebas axe-core completas se ejecutan en tests/e2e/ con Playwright.
"""
import re
from pathlib import Path

from django.test import SimpleTestCase

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "templates"

# Comentarios a eliminar antes de comprobar.
COMMENT_BLOCK = re.compile(r"{%\s*comment\s*%}.*?{%\s*endcomment\s*%}", re.DOTALL)
COMMENT_LINE = re.compile(r"{#.*?#}", re.DOTALL)

IMG_NO_ALT = re.compile(
    r"""<img\b
        (?![^>]*\balt=)
        [^>]*>""",
    re.IGNORECASE | re.VERBOSE,
)

A_NO_HREF = re.compile(
    r"""<a\b
        (?![^>]*\bhref=)
        [^>]*>""",
    re.IGNORECASE | re.VERBOSE,
)

BTN_NO_TYPE = re.compile(
    r"""<button\b
        (?![^>]*\btype=)
        [^>]*>""",
    re.IGNORECASE | re.VERBOSE,
)

INPUT_NO_LABEL = re.compile(
    r"""<input\b
        (?![^>]*\b(?:id|aria-label|aria-labelledby)=)
        (?![^>]*\btype=["']?(?:hidden|submit|button|reset|image)\b)
        [^>]*>""",
    re.IGNORECASE | re.VERBOSE,
)

def _strip(text: str) -> str:
    return COMMENT_LINE.sub("", COMMENT_BLOCK.sub("", text))

def _iter_templates():
    for f in TEMPLATES.rglob("*.html"):
        yield f, _strip(f.read_text(encoding="utf-8", errors="ignore"))

def _offenders(pattern):
    return [
        f"{f.relative_to(ROOT)}: {m.group(0)[:80]!r}"
        for f, t in _iter_templates()
        for m in pattern.finditer(t)
    ]

class A11yStaticTests(SimpleTestCase):
    def test_imgs_con_alt(self):
        bad = _offenders(IMG_NO_ALT)
        self.assertEqual(bad, [], f"<img> sin alt ({len(bad)}): {bad[:5]}")

    def test_enlaces_con_href(self):
        bad = _offenders(A_NO_HREF)
        self.assertEqual(bad, [], f"<a> sin href ({len(bad)}): {bad[:5]}")

    def test_botones_con_type(self):
        bad = _offenders(BTN_NO_TYPE)
        self.assertEqual(bad, [], f"<button> sin type ({len(bad)}): {bad[:5]}")

    def test_inputs_con_id_o_aria(self):
        bad = _offenders(INPUT_NO_LABEL)
        self.assertEqual(bad, [], f"<input> sin id/aria ({len(bad)}): {bad[:5]}")
