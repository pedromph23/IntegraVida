"""Tests de F3.a — login/logout del panel (obligatorios §16).

Usa get_user_model() porque el proyecto tiene usuarios.Usuario custom.
Los POST del login usan "username" como key porque AuthenticationForm
de Django siempre lo declara así, sin importar USERNAME_FIELD del modelo.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

User = get_user_model()
USERNAME_FIELD = User.USERNAME_FIELD


def _identifier():
    return "test@example.com" if USERNAME_FIELD == "email" else "testuser"


def _create_user(**overrides):
    kwargs = {USERNAME_FIELD: _identifier(), "password": "CorrectPassword123!"}
    kwargs.update(overrides)
    return User.objects.create_user(**kwargs)


def _login_payload(password="CorrectPassword123!"):
    return {"username": _identifier(), "password": password}


class LoginViewTests(TestCase):
    def setUp(self):
        self.user = _create_user()
        self.client = Client()

    def test_login_get_returns_200_with_form(self):
        r = self.client.get(reverse("auth:login"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "<form")
        self.assertContains(r, 'data-testid="login-form"')

    def test_login_get_has_anti_fouc_script(self):
        r = self.client.get(reverse("auth:login"))
        self.assertContains(r, "data-theme")
        self.assertContains(r, "localStorage.getItem('iv-theme')")

    def test_login_post_valid_redirects_to_dashboard(self):
        r = self.client.post(reverse("auth:login"), _login_payload())
        self.assertRedirects(r, reverse("dashboard:home"))

    def test_login_post_invalid_generic_error(self):
        r = self.client.post(reverse("auth:login"), _login_payload(password="wrong"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Credenciales inválidas")

    def test_login_post_unknown_user_same_message(self):
        r = self.client.post(reverse("auth:login"), {
            "username": "no_such_user_xyz_9999", "password": "whatever",
        })
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Credenciales inválidas")

    def test_login_redirects_authenticated_user(self):
        self.client.force_login(self.user)
        r = self.client.get(reverse("auth:login"))
        self.assertEqual(r.status_code, 302)


class DashboardAuthTests(TestCase):
    def setUp(self):
        self.user = _create_user()
        self.client = Client()

    def test_dashboard_requires_login(self):
        r = self.client.get(reverse("dashboard:home"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/panel/login/", r.url)

    def test_dashboard_with_login_returns_200(self):
        self.client.force_login(self.user)
        r = self.client.get(reverse("dashboard:home"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Panel institucional")

    def test_logout_post_redirects_to_login(self):
        self.client.force_login(self.user)
        r = self.client.post(reverse("auth:logout"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/panel/login/", r.url)
