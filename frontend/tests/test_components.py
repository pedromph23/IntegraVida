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
