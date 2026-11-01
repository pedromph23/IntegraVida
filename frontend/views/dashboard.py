"""Vistas del panel institucional (F3.a)."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def home(request):
    user = request.user
    groups = list(user.groups.values_list("name", flat=True))
    return render(request, "dashboard/home.html", {
        "page_title": "Panel institucional",
        "user_groups": groups,
        "last_login": user.last_login,
    })
