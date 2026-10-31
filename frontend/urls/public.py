from django.urls import path

from frontend.views import public

app_name = "public"

urlpatterns = [
    path("", public.home, name="home"),
    path("design-system/", public.design_system, name="design-system"),
    path("hospitales/", public.hospitals_list, name="hospitals-list"),
    path("refugios/", public.shelters_list, name="shelters-list"),
    path("alertas/", public.alerts_list, name="alerts-list"),
    path("reportes/", public.report_create, name="report-create"),
    path(
        "reportes/<uuid:reporte_id>/",
        public.report_tracking,
        name="report-tracking",
    ),
    path(
        "alertas/<uuid:emergencia_id>/",
        public.alert_detail,
        name="alert-detail",
    ),
    path(
        "refugios/<slug:codigo>/",
        public.shelter_detail,
        name="shelter-detail",
    ),
    path(
        "hospitales/<slug:codigo>/",
        public.hospital_detail,
        name="hospital-detail",
    ),
]
