from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST
from django.http import HttpResponseForbidden
from apps.organizaciones.services import puede_administrar_plataforma
from frontend.forms.catalogos_crud import OrganizacionForm, EntidadFederalForm, MunicipioForm, ParroquiaForm

def _require_admin(user):
    if not puede_administrar_plataforma(user):
        raise PermissionError("Solo admin de plataforma.")

@login_required
@require_GET
def organizacion_create_form(request):
    if not puede_administrar_plataforma(request.user): return HttpResponseForbidden()
    return render(request, "dashboard/generic_crud_form.html", {
        "form": OrganizacionForm(),
        "page_title": "Nueva Organización",
        "submit_url": reverse("dashboard:organizacion_create_submit"),
    })

@login_required
@require_POST
def organizacion_create_submit(request):
    if not puede_administrar_plataforma(request.user): return HttpResponseForbidden()
    form = OrganizacionForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "Organización creada.")
        return redirect("dashboard:configuracion_index")
    # Si falla la validación, volvemos a renderizar el form CON el submit_url correcto
    return render(request, "dashboard/generic_crud_form.html", {
        "form": form,
        "page_title": "Nueva Organización",
        "submit_url": reverse("dashboard:organizacion_create_submit"),
    })

@login_required
@require_GET
def entidad_create_form(request):
    if not puede_administrar_plataforma(request.user): return HttpResponseForbidden()
    return render(request, "dashboard/generic_crud_form.html", {"form": EntidadFederalForm(), "page_title": "Nueva Entidad Federal"})

@login_required
@require_POST
def entidad_create_submit(request):
    if not puede_administrar_plataforma(request.user): return HttpResponseForbidden()
    form = EntidadFederalForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "Entidad Federal creada.")
        return redirect("dashboard:configuracion_index")
    return render(request, "dashboard/generic_crud_form.html", {"form": form, "page_title": "Nueva Entidad Federal"})


@login_required
@require_GET
def municipio_create_form(request):
    if not puede_administrar_plataforma(request.user): return HttpResponseForbidden()
    return render(request, "dashboard/generic_crud_form.html", {"form": MunicipioForm(), "page_title": "Nuevo Municipio"})

@login_required
@require_POST
def municipio_create_submit(request):
    if not puede_administrar_plataforma(request.user): return HttpResponseForbidden()
    form = MunicipioForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "Municipio creado.")
        return redirect("dashboard:configuracion_index")
    return render(request, "dashboard/generic_crud_form.html", {"form": form, "page_title": "Nuevo Municipio"})

@login_required
@require_GET
def parroquia_create_form(request):
    if not puede_administrar_plataforma(request.user): return HttpResponseForbidden()
    return render(request, "dashboard/generic_crud_form.html", {"form": ParroquiaForm(), "page_title": "Nueva Parroquia"})

@login_required
@require_POST
def parroquia_create_submit(request):
    if not puede_administrar_plataforma(request.user): return HttpResponseForbidden()
    form = ParroquiaForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "Parroquia creada.")
        return redirect("dashboard:configuracion_index")
    return render(request, "dashboard/generic_crud_form.html", {"form": form, "page_title": "Nueva Parroquia"})
