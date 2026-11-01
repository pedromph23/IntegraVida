"""Tests de F3.b — métricas reales del dashboard home.

No creamos instancias de Refugio/Emergencia/Hospital (sus campos
requeridos se definen en F3.c). Probamos:
- _visible_cards (puro)
- _build_cards con DB vacía (todos los conteos en 0)
- render del view home sin datos
- filtrado por grupo
- que no haya N+1 (query count acotado)
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from frontend.views.dashboard import ALL_CARDS, _visible_cards

User = get_user_model()


def _mk_user(username, groups=()):
    u = User.objects.create_user(username=username, password="x")
    for n in groups:
        g, _ = Group.objects.get_or_create(name=n)
        u.groups.add(g)
    return u


class VisibleCardsTests(TestCase):
    def test_no_groups_sees_all(self):
        self.assertEqual(_visible_cards(_mk_user("u1")), ALL_CARDS)

    def test_operador_refugio_sees_only_refugios(self):
        u = _mk_user("u2", ["OPERADOR_REFUGIO"])
        self.assertEqual(_visible_cards(u), {"refugios"})

    def test_unknown_group_falls_back_to_all(self):
        u = _mk_user("u3", ["GRUPO_INEXISTENTE"])
        self.assertEqual(_visible_cards(u), ALL_CARDS)

    def test_multiple_groups_union(self):
        u = _mk_user("u4", ["OPERADOR_REFUGIO", "ANALISTA"])
        self.assertEqual(_visible_cards(u), {"refugios", "reportes"})


class DashboardHomeTests(TestCase):
    def setUp(self):
        self.user = _mk_user("dash_user")
        self.client.force_login(self.user)

    def test_home_requires_auth(self):
        self.client.logout()
        r = self.client.get(reverse("dashboard:home"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/panel/login/", r.url)

    def test_home_renders_all_cards_with_empty_db(self):
        r = self.client.get(reverse("dashboard:home"))
        self.assertEqual(r.status_code, 200)
        for label in (
            "Refugios activos",
            "Emergencias abiertas",
            "Hospitales disponibles",
            "Reportes pendientes",
        ):
            self.assertContains(r, label)

    def test_home_shows_zero_counts(self):
        r = self.client.get(reverse("dashboard:home"))
        self.assertContains(r, "0")

    def test_home_filters_cards_by_group(self):
        self.user.groups.add(
            Group.objects.create(name="OPERADOR_REFUGIO")
        )
        r = self.client.get(reverse("dashboard:home"))
        self.assertContains(r, "Refugios activos")
        self.assertNotContains(r, "Emergencias abiertas")
        self.assertNotContains(r, "Hospitales disponibles")
        self.assertNotContains(r, "Reportes pendientes")

    def test_home_query_count_bounded(self):
        # 1 sesión + 1 user + 1 grupos + 4 aggregates = ~7. Margen 12.
        with CaptureQueriesContext(connection) as ctx:
            self.client.get(reverse("dashboard:home"))
        self.assertLessEqual(
            len(ctx.captured_queries), 12,
            f"Demasiadas queries: {len(ctx.captured_queries)}",
        )
