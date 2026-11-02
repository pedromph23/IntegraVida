"""URLs del panel (F3.a home + F3.c refugios + F3.d emergencias + F3.e.1 hospitales)."""
from django.urls import path

from frontend.views import dashboard as dash_views
from frontend.views import dashboard_refugios as refugio_views
from frontend.views import dashboard_emergencias as emergencia_views
from frontend.views import dashboard_hospitales as hospital_views
from frontend.views import dashboard_pacientes as paciente_views
from frontend.views import dashboard_triajes as triaje_views
from frontend.views import dashboard_derivaciones as derivacion_views
from frontend.views import dashboard_inventario as inventario_views
from frontend.views import dashboard_transferencias as transferencia_views
from frontend.views import dashboard_entregas as entrega_views
from frontend.views import dashboard_reportes as reporte_views
from frontend.views import dashboard_configuracion as config_views

app_name = "dashboard"

urlpatterns = [
    path("", dash_views.home, name="home"),

    # F3.c — Refugios
    path("refugios/", refugio_views.refugios_list, name="refugios_list"),
    # IMPORTANTE: /nuevo/ va ANTES de /<slug:codigo>/, si no "nuevo"
    # matchea como un código válido.
    path(
        "refugios/nuevo/",
        refugio_views.refugio_create_form,
        name="refugio_create_form",
    ),
    path(
        "refugios/nuevo/guardar/",
        refugio_views.refugio_create_submit,
        name="refugio_create_submit",
    ),
    path(
        "refugios/<slug:codigo>/editar/",
        refugio_views.refugio_update_form,
        name="refugio_update_form",
    ),
    path(
        "refugios/<slug:codigo>/editar/guardar/",
        refugio_views.refugio_update_submit,
        name="refugio_update_submit",
    ),
    path(
        "refugios/<slug:codigo>/inactivar/",
        refugio_views.refugio_inactivar_confirm,
        name="refugio_inactivar_confirm",
    ),
    path(
        "refugios/<slug:codigo>/inactivar/confirmar/",
        refugio_views.refugio_inactivar_submit,
        name="refugio_inactivar_submit",
    ),
    path(
        "refugios/<slug:codigo>/",
        refugio_views.refugio_detail,
        name="refugio_detail",
    ),
    path(
        "refugios/<slug:codigo>/estado/",
        refugio_views.refugio_cambiar_estado,
        name="refugio_cambiar_estado",
    ),

    # F3.d + F5.c — Emergencias
    path(
        "emergencias/",
        emergencia_views.emergencias_list,
        name="emergencias_list",
    ),
    path(
        "emergencias/nueva/",
        emergencia_views.emergencia_create_form,
        name="emergencia_create_form",
    ),
    path(
        "emergencias/nueva/guardar/",
        emergencia_views.emergencia_create_submit,
        name="emergencia_create_submit",
    ),
    path(
        "emergencias/<uuid:emergencia_id>/editar/",
        emergencia_views.emergencia_update_form,
        name="emergencia_update_form",
    ),
    path(
        "emergencias/<uuid:emergencia_id>/editar/guardar/",
        emergencia_views.emergencia_update_submit,
        name="emergencia_update_submit",
    ),
    path(
        "emergencias/<uuid:emergencia_id>/",
        emergencia_views.emergencia_detail,
        name="emergencia_detail",
    ),
    path(
        "emergencias/<uuid:emergencia_id>/estado/",
        emergencia_views.emergencia_cambiar_estado,
        name="emergencia_cambiar_estado",
    ),

    # F3.e.1 + F5.b — Hospitales
    path(
        "hospitales/",
        hospital_views.hospitales_list,
        name="hospitales_list",
    ),
    # IMPORTANTE: /nuevo/ ANTES de /<slug:codigo>/
    path(
        "hospitales/nuevo/",
        hospital_views.hospital_create_form,
        name="hospital_create_form",
    ),
    path(
        "hospitales/nuevo/guardar/",
        hospital_views.hospital_create_submit,
        name="hospital_create_submit",
    ),
    path(
        "hospitales/<slug:codigo>/editar/",
        hospital_views.hospital_update_form,
        name="hospital_update_form",
    ),
    path(
        "hospitales/<slug:codigo>/editar/guardar/",
        hospital_views.hospital_update_submit,
        name="hospital_update_submit",
    ),
    path(
        "hospitales/<slug:codigo>/inactivar/",
        hospital_views.hospital_inactivar_confirm,
        name="hospital_inactivar_confirm",
    ),
    path(
        "hospitales/<slug:codigo>/inactivar/confirmar/",
        hospital_views.hospital_inactivar_submit,
        name="hospital_inactivar_submit",
    ),
    path(
        "hospitales/<slug:codigo>/reactivar/",
        hospital_views.hospital_reactivar,
        name="hospital_reactivar",
    ),
    path(
        "hospitales/<slug:codigo>/",
        hospital_views.hospital_detail,
        name="hospital_detail",
    ),
    path(
        "hospitales/<slug:codigo>/estado/",
        hospital_views.hospital_cambiar_estado,
        name="hospital_cambiar_estado",
    ),
    # F3.e.2 — Pacientes (solo lectura, PII enmascarada)
    path(
        "pacientes/",
        paciente_views.pacientes_list,
        name="pacientes_list",
    ),
    path(
        "pacientes/<uuid:paciente_id>/",
        paciente_views.paciente_detail,
        name="paciente_detail",
    ),
    # F3.f.1 — Triajes (solo lectura, ámbito por membresía)
    path(
        "triajes/",
        triaje_views.triajes_list,
        name="triajes_list",
    ),
    path(
        "triajes/<uuid:triaje_id>/",
        triaje_views.triaje_detail,
        name="triaje_detail",
    ),
    # F3.f.2 — Derivaciones (transiciones delegadas a services)
    path(
        "derivaciones/",
        derivacion_views.derivaciones_list,
        name="derivaciones_list",
    ),
    path(
        "derivaciones/<uuid:derivacion_id>/",
        derivacion_views.derivacion_detail,
        name="derivacion_detail",
    ),
    path(
        "derivaciones/<uuid:derivacion_id>/transicionar/",
        derivacion_views.derivacion_transicionar,
        name="derivacion_transicionar",
    ),
    # F3.g.1 — Inventario (lectura)
    path(
        "inventario/insumos/",
        inventario_views.insumos_list,
        name="insumos_list",
    ),
    path(
        "inventario/insumos/<slug:codigo>/",
        inventario_views.insumo_detail,
        name="insumo_detail",
    ),
    path(
        "inventario/stock/",
        inventario_views.stock_list,
        name="stock_list",
    ),
    path(
        "inventario/stock/<uuid:stock_id>/",
        inventario_views.stock_detail,
        name="stock_detail",
    ),
    # F3.g.2 — Transferencias (transiciones delegadas a services)
    path(
        "inventario/transferencias/",
        transferencia_views.transferencias_list,
        name="transferencias_list",
    ),
    path(
        "inventario/transferencias/<uuid:transferencia_id>/",
        transferencia_views.transferencia_detail,
        name="transferencia_detail",
    ),
    path(
        "inventario/transferencias/<uuid:transferencia_id>/accion/",
        transferencia_views.transferencia_accion,
        name="transferencia_accion",
    ),
    # F3.g.3 — Entregas (transiciones delegadas a services)
    path(
        "inventario/entregas/",
        entrega_views.entregas_list,
        name="entregas_list",
    ),
    path(
        "inventario/entregas/<uuid:entrega_id>/",
        entrega_views.entrega_detail,
        name="entrega_detail",
    ),
    path(
        "inventario/entregas/<uuid:entrega_id>/accion/",
        entrega_views.entrega_accion,
        name="entrega_accion",
    ),
    # F3.h.1 — Reportes (UI wrapper de services)
    # IMPORTANTE: historial/ va ANTES de <slug:slug>/ (else el slug lo captura)
    path(
        "reportes/",
        reporte_views.reportes_index,
        name="reportes_index",
    ),
    path(
        "reportes/historial/",
        reporte_views.reportes_historial,
        name="reportes_historial",
    ),
    path(
        "reportes/<slug:slug>/",
        reporte_views.reporte_ejecutar,
        name="reporte_ejecutar",
    ),
    # F3.h.2 — Configuración (Membresías)
    path(
        "configuracion/",
        config_views.configuracion_index,
        name="configuracion_index",
    ),
    path(
        "configuracion/membresias/",
        config_views.membresias_list,
        name="membresias_list",
    ),
    path(
        "configuracion/membresias/<uuid:membresia_id>/update/",
        config_views.membresia_update,
        name="membresia_update",
    ),
]
