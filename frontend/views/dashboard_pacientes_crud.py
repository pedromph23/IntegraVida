from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST
from apps.pacientes.models import Paciente, Episodio, ContactoEmergencia
from apps.organizaciones.models import Membresia
from frontend.forms.pacientes_crud import PacienteCreateForm, EpisodioForm, ContactoEmergenciaForm

def _org_ids(user):
    return list(Membresia.objects.filter(usuario=user, estado=Membresia.Estado.ACTIVA).values_list("organizacion_id", flat=True))

@login_required
@require_GET
def paciente_create_form(request):
    return render(request, "dashboard/pacientes/crud_form.html", {"form": PacienteCreateForm(), "page_title": "Nuevo Paciente"})

@login_required
@require_POST
def paciente_create_submit(request):
    form = PacienteCreateForm(request.POST)
    if form.is_valid():
        p = form.save()
        messages.success(request, "Paciente registrado.")
        return redirect("dashboard:paciente_detail", p.id)
    return render(request, "dashboard/pacientes/crud_form.html", {"form": form, "page_title": "Nuevo Paciente"})

@login_required
@require_GET
def episodio_create_form(request, paciente_id):
    paciente = get_object_or_404(Paciente, id=paciente_id)
    form = EpisodioForm(org_ids=_org_ids(request.user))
    return render(request, "dashboard/pacientes/crud_form.html", {"form": form, "page_title": f"Nuevo Episodio para {paciente.nombres}"})

@login_required
@require_POST
def episodio_create_submit(request, paciente_id):
    paciente = get_object_or_404(Paciente, id=paciente_id)
    form = EpisodioForm(request.POST, org_ids=_org_ids(request.user))
    if form.is_valid():
        e = form.save(commit=False)
        e.paciente = paciente
        e.registrado_por = request.user
        e.save()
        messages.success(request, "Episodio abierto.")
        return redirect("dashboard:paciente_detail", paciente.id)
    return render(request, "dashboard/pacientes/crud_form.html", {"form": form, "page_title": f"Nuevo Episodio para {paciente.nombres}"})

@login_required
@require_GET
def contacto_create_form(request, paciente_id):
    paciente = get_object_or_404(Paciente, id=paciente_id)
    return render(request, "dashboard/pacientes/crud_form.html", {"form": ContactoEmergenciaForm(), "page_title": f"Nuevo Contacto para {paciente.nombres}"})

@login_required
@require_POST
def contacto_create_submit(request, paciente_id):
    paciente = get_object_or_404(Paciente, id=paciente_id)
    form = ContactoEmergenciaForm(request.POST)
    if form.is_valid():
        c = form.save(commit=False)
        c.paciente = paciente
        c.save()
        messages.success(request, "Contacto añadido.")
        return redirect("dashboard:paciente_detail", paciente.id)
    return render(request, "dashboard/pacientes/crud_form.html", {"form": form, "page_title": f"Nuevo Contacto para {paciente.nombres}"})
