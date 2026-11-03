from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST
from apps.emergencias.models import ReporteEmergencia
from frontend.forms.reportes_crud import ReporteEmergenciaForm

@login_required
@require_GET
def reporte_emergencia_create_form(request):
    return render(request, "dashboard/generic_crud_form.html", {"form": ReporteEmergenciaForm(), "page_title": "Nuevo Reporte de Emergencia"})

@login_required
@require_POST
def reporte_emergencia_create_submit(request):
    form = ReporteEmergenciaForm(request.POST)
    if form.is_valid():
        r = form.save(commit=False)
        r.reportante = request.user
        r.save()
        messages.success(request, "Reporte de emergencia registrado.")
        return redirect("dashboard:emergencias_list")
    return render(request, "dashboard/generic_crud_form.html", {"form": form, "page_title": "Nuevo Reporte de Emergencia"})
