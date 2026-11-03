"""URLs del panel (F3.a home + F3.c refugios + F3.d emergencias + F3.e.1 hospitales)."""
from django.urls import path

from frontend.views import dashboard as dash_views
from frontend.views import dashboard_mapa as mapa_views
from frontend.views import dashboard_puntos_crud as puntos_views
from frontend.views import api_rutas as api_views
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
from frontend.views import dashboard_usuarios as usuarios_views
from frontend.views import dashboard_pacientes_crud as pac_crud
from frontend.views import dashboard_estructura_crud as est_crud
from frontend.views import dashboard_catalogos_crud as cat_crud
from frontend.views import dashboard_reportes_crud as rep_crud

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
    # F3.e.2 + F5.d — Pacientes
    path(
        "pacientes/nuevo/",
        pac_crud.paciente_create_form,
        name="paciente_create_form",
    ),
    path(
        "pacientes/nuevo/guardar/",
        pac_crud.paciente_create_submit,
        name="paciente_create_submit",
    ),
    path(
        "pacientes/<uuid:paciente_id>/episodios/nuevo/",
        pac_crud.episodio_create_form,
        name="episodio_create_form",
    ),
    path(
        "pacientes/<uuid:paciente_id>/episodios/nuevo/guardar/",
        pac_crud.episodio_create_submit,
        name="episodio_create_submit",
    ),
    path(
        "pacientes/<uuid:paciente_id>/contactos/nuevo/",
        pac_crud.contacto_create_form,
        name="contacto_create_form",
    ),
    path(
        "pacientes/<uuid:paciente_id>/contactos/nuevo/guardar/",
        pac_crud.contacto_create_submit,
        name="contacto_create_submit",
    ),
    path(
        "pacientes/",
        paciente_views.pacientes_list,
        name="pacientes_list",
    ),
    path(
        "pacientes/<uuid:paciente_id>/editar/",
        paciente_views.paciente_update_form,
        name="paciente_update_form",
    ),
    path(
        "pacientes/<uuid:paciente_id>/editar/guardar/",
        paciente_views.paciente_update_submit,
        name="paciente_update_submit",
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
        "inventario/insumos/nuevo/",
        inventario_views.insumo_create_form,
        name="insumo_create_form",
    ),
    path(
        "inventario/insumos/nuevo/guardar/",
        inventario_views.insumo_create_submit,
        name="insumo_create_submit",
    ),
    path(
        "inventario/insumos/<slug:codigo>/editar/",
        inventario_views.insumo_update_form,
        name="insumo_update_form",
    ),
    path(
        "inventario/insumos/<slug:codigo>/editar/guardar/",
        inventario_views.insumo_update_submit,
        name="insumo_update_submit",
    ),
    path(
        "inventario/insumos/<slug:codigo>/toggle/",
        inventario_views.insumo_inactivar_submit,
        name="insumo_inactivar_submit",
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
        "usuarios/",
        usuarios_views.usuarios_list,
        name="usuarios_list",
    ),
    path(
        "usuarios/nuevo/",
        usuarios_views.usuario_create_form,
        name="usuario_create_form",
    ),
    path(
        "usuarios/nuevo/guardar/",
        usuarios_views.usuario_create_submit,
        name="usuario_create_submit",
    ),
    path(
        "usuarios/<uuid:user_id>/editar/",
        usuarios_views.usuario_update_form,
        name="usuario_update_form",
    ),
    path(
        "usuarios/<uuid:user_id>/editar/guardar/",
        usuarios_views.usuario_update_submit,
        name="usuario_update_submit",
    ),
    path(
        "usuarios/<uuid:user_id>/toggle/",
        usuarios_views.usuario_toggle_active,
        name="usuario_toggle_active",
    ),
    path(
        "usuarios/<uuid:user_id>/",
        usuarios_views.usuario_detail,
        name="usuario_detail",
    ),
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
        "configuracion/membresias/nueva/",
        config_views.membresia_create_form,
        name="membresia_create_form",
    ),
    path(
        "configuracion/membresias/nueva/guardar/",
        config_views.membresia_create_submit,
        name="membresia_create_submit",
    ),
    path(
        "configuracion/membresias/<uuid:membresia_id>/update/",
        config_views.membresia_update,
        name="membresia_update",
    ),

    # ── Mapa navegador + puntos de referencia ──
    path("mapa/", mapa_views.mapa_view, name="mapa_view"),
    path("api/ruta/", api_views.calcular_ruta, name="api_ruta"),
    path("puntos/", puntos_views.puntos_list, name="puntos_list"),
    path("puntos/nuevo/", puntos_views.punto_create_form, name="punto_create_form"),
    path("puntos/nuevo/guardar/", puntos_views.punto_create_submit, name="punto_create_submit"),
    path("puntos/<uuid:punto_id>/", puntos_views.punto_detail, name="punto_detail"),
    path("puntos/<uuid:punto_id>/editar/", puntos_views.punto_update_form, name="punto_update_form"),
    path("puntos/<uuid:punto_id>/editar/guardar/", puntos_views.punto_update_submit, name="punto_update_submit"),
    path("puntos/<uuid:punto_id>/toggle/", puntos_views.punto_toggle, name="punto_toggle"),

]





# ═════════════════════════════════════════════════════════════════
# Rutas de servicios + almacenes + lotes (restauradas)
# ═════════════════════════════════════════════════════════════════
urlpatterns += [
    path("servicios/nuevo/", est_crud.servicio_create_form, name="servicio_create_form"),
    path("servicios/nuevo/guardar/", est_crud.servicio_create_submit, name="servicio_create_submit"),
    path("almacenes/nuevo/", est_crud.almacen_create_form, name="almacen_create_form"),
    path("almacenes/nuevo/guardar/", est_crud.almacen_create_submit, name="almacen_create_submit"),
    path("insumos/<slug:insumo_codigo>/lotes/nuevo/", est_crud.lote_create_form, name="lote_create_form"),
    path("insumos/<slug:insumo_codigo>/lotes/nuevo/guardar/", est_crud.lote_create_submit, name="lote_create_submit"),
]

# ═════════════════════════════════════════════════════════════════
# Rutas de catálogos (restauradas)
# ═════════════════════════════════════════════════════════════════
urlpatterns += [
    path("organizaciones/nueva/", cat_crud.organizacion_create_form, name="organizacion_create_form"),
    path("organizaciones/nueva/guardar/", cat_crud.organizacion_create_submit, name="organizacion_create_submit"),
    path("entidades/nueva/", cat_crud.entidad_create_form, name="entidad_create_form"),
    path("entidades/nueva/guardar/", cat_crud.entidad_create_submit, name="entidad_create_submit"),
]

# ═════════════════════════════════════════════════════════════════
# Rutas de recursos + municipios + parroquias + reportes (restauradas)
# ═════════════════════════════════════════════════════════════════
urlpatterns += [
    path(
        "hospitales/<slug:codigo>/recursos/nuevo/",
        est_crud.recurso_create_form,
        name="recurso_create_form",
    ),
    path(
        "hospitales/<slug:codigo>/recursos/nuevo/guardar/",
        est_crud.recurso_create_submit,
        name="recurso_create_submit",
    ),
    path("municipios/nuevo/", cat_crud.municipio_create_form, name="municipio_create_form"),
    path("municipios/nuevo/guardar/", cat_crud.municipio_create_submit, name="municipio_create_submit"),
    path("parroquias/nuevo/", cat_crud.parroquia_create_form, name="parroquia_create_form"),
    path("parroquias/nuevo/guardar/", cat_crud.parroquia_create_submit, name="parroquia_create_submit"),
    path("reportes-emergencia/nuevo/", rep_crud.reporte_emergencia_create_form, name="reporte_emergencia_create_form"),
    path("reportes-emergencia/nuevo/guardar/", rep_crud.reporte_emergencia_create_submit, name="reporte_emergencia_create_submit"),
]
