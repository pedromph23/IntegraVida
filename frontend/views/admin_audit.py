"""Vistas de auditoría del admin custom (F4.d).

Solo lectura. Los eventos son inmutables (hash chain + PROTECT sobre
actor). Filtros por resultado, actor, acción, tipo de objeto y rango
de fechas. Detalle con hash chain visual + metadatos JSON.
"""
import json
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_GET

from apps.auditoria.models import EventoAuditoria


User = get_user_model()

PAGE_SIZE = 50


_admin_login_required = login_required(login_url=reverse_lazy("admin:login"))


def _require_admin_access(request):
    u = request.user
    return u.is_authenticated and (u.is_superuser or u.is_staff)


def _parse_fecha(s: str) -> datetime | None:
    """Acepta YYYY-MM-DD. Devuelve datetime aware en la zona local.

    Con USE_TZ=True, un datetime naive se compara mal contra
    `ocurrido_en` (que es aware en UTC). Convertimos a aware en
    `timezone.get_current_timezone()` para que "desde 2026-11-01"
    signifique medianoche local del 1 de noviembre.
    """
    if not s:
        return None
    try:
        naive = datetime.strptime(s.strip(), "%Y-%m-%d")
    except ValueError:
        return None
    return timezone.make_aware(naive, timezone.get_current_timezone())


@_admin_login_required
@require_GET
def audit_list(request):
    if not _require_admin_access(request):
        return HttpResponseForbidden("Solo staff/superuser.")

    qs = (
        EventoAuditoria.objects
        .select_related("actor")
        .order_by("-ocurrido_en")
    )

    # Filtros
    resultado = request.GET.get("resultado", "").strip()
    resultados_validos = {v for v, _ in EventoAuditoria._meta.get_field("resultado").choices}
    if resultado not in resultados_validos:
        resultado = ""
    if resultado:
        qs = qs.filter(resultado=resultado)

    actor_q = request.GET.get("actor", "").strip()[:100]
    if actor_q:
        qs = qs.filter(actor__username__icontains=actor_q)

    accion_q = request.GET.get("accion", "").strip()[:100]
    if accion_q:
        qs = qs.filter(accion__icontains=accion_q)

    tipo_objeto_q = request.GET.get("tipo_objeto", "").strip()[:100]
    if tipo_objeto_q:
        qs = qs.filter(tipo_objeto__icontains=tipo_objeto_q)

    desde = _parse_fecha(request.GET.get("desde", ""))
    hasta = _parse_fecha(request.GET.get("hasta", ""))
    if desde:
        qs = qs.filter(ocurrido_en__gte=desde)
    if hasta:
        # Incluye todo el día
        qs = qs.filter(ocurrido_en__lt=hasta + timedelta(days=1))

    paginator = Paginator(qs, PAGE_SIZE)
    page = paginator.get_page(request.GET.get("page", 1))

    return render(request, "admin_custom/audit_list.html", {
        "page_title": "Admin · Auditoría",
        "page_obj": page,
        "total": paginator.count,
        "filters": {
            "resultado": resultado,
            "actor": actor_q,
            "accion": accion_q,
            "tipo_objeto": tipo_objeto_q,
            "desde": request.GET.get("desde", ""),
            "hasta": request.GET.get("hasta", ""),
        },
        "resultados": EventoAuditoria._meta.get_field("resultado").choices,
    })


@_admin_login_required
@require_GET
def audit_detail(request, evento_id):
    if not _require_admin_access(request):
        return HttpResponseForbidden("Solo staff/superuser.")

    evento = get_object_or_404(
        EventoAuditoria.objects.select_related("actor"),
        id=evento_id,
    )

    # Metadatos pretty-printed
    try:
        metadatos_str = json.dumps(
            evento.metadatos or {}, indent=2, ensure_ascii=False, default=str,
        )
    except (TypeError, ValueError):
        metadatos_str = repr(evento.metadatos)

    return render(request, "admin_custom/audit_detail.html", {
        "page_title": f"Evento · {evento.accion}",
        "evento": evento,
        "metadatos_str": metadatos_str,
    })
