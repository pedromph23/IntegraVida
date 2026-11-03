from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST
from apps.hospitales.models import Servicio, RecursoHospitalario
from apps.inventario.models import Almacen, Lote, Insumo
from apps.organizaciones.models import Membresia, Organizacion
from frontend.forms.estructura_crud import ServicioForm, RecursoHospitalarioForm, AlmacenForm, LoteForm

def _org_ids(user):
    return list(Membresia.objects.filter(usuario=user, estado=Membresia.Estado.ACTIVA).values_list("organizacion_id", flat=True))

@login_required
@require_GET
def servicio_create_form(request):
    return render(request, "dashboard/generic_crud_form.html", {"form": ServicioForm(), "page_title": "Nuevo Servicio"})

@login_required
@require_POST
def servicio_create_submit(request):
    form = ServicioForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "Servicio creado.")
        return redirect("dashboard:servicios_list")
    return render(request, "dashboard/generic_crud_form.html", {"form": form, "page_title": "Nuevo Servicio"})

@login_required
@require_GET
def recurso_create_form(request, codigo):
    from apps.hospitales.models import Hospital
    hospital = get_object_or_404(Hospital, codigo=codigo)
    form = RecursoHospitalarioForm()
    return render(request, "dashboard/generic_crud_form.html", {
        "form": form, "page_title": f"Nuevo Recurso · {hospital.nombre}",
    })

@login_required
@require_POST
def recurso_create_submit(request, codigo):
    from apps.hospitales.models import Hospital
    hospital = get_object_or_404(Hospital, codigo=codigo)
    form = RecursoHospitalarioForm(request.POST)
    if form.is_valid():
        r = form.save(commit=False)
        r.hospital = hospital
        r.save()
        messages.success(request, "Recurso añadido.")
        return redirect("dashboard:hospital_detail", hospital.codigo)
    return render(request, "dashboard/generic_crud_form.html", {
        "form": form, "page_title": f"Nuevo Recurso · {hospital.nombre}",
    })

@login_required
@require_GET
def almacen_create_form(request):
    form = AlmacenForm()
    form.fields["hospital"].queryset = form.fields["hospital"].queryset.filter(organizacion_id__in=_org_ids(request.user))
    form.fields["refugio"].queryset = form.fields["refugio"].queryset.filter(organizacion_id__in=_org_ids(request.user))
    return render(request, "dashboard/generic_crud_form.html", {"form": form, "page_title": "Nuevo Almacén"})

@login_required
@require_POST
def almacen_create_submit(request):
    form = AlmacenForm(request.POST)
    if form.is_valid():
        a = form.save(commit=False)
        a.organizacion_id = request.user.membresias.first().organizacion_id
        a.save()
        messages.success(request, "Almacén creado.")
        return redirect("dashboard:stock_list")
    return render(request, "dashboard/generic_crud_form.html", {"form": form, "page_title": "Nuevo Almacén"})

@login_required
@require_GET
def lote_create_form(request, insumo_codigo):
    insumo = get_object_or_404(Insumo, codigo=insumo_codigo)
    form = LoteForm(initial={"insumo": insumo})
    form.fields["insumo"].disabled = True
    return render(request, "dashboard/generic_crud_form.html", {"form": form, "page_title": f"Nuevo Lote de {insumo.nombre}"})

@login_required
@require_POST
def lote_create_submit(request, insumo_codigo):
    insumo = get_object_or_404(Insumo, codigo=insumo_codigo)
    form = LoteForm(request.POST)
    if form.is_valid():
        lote = form.save(commit=False)
        lote.insumo = insumo
        lote.save()
        messages.success(request, "Lote creado.")
        return redirect("dashboard:stock_list")
    return render(request, "dashboard/generic_crud_form.html", {"form": form, "page_title": f"Nuevo Lote de {insumo.nombre}"})
