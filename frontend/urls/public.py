from django.urls import path

from frontend.views import public

app_name = "public"

urlpatterns = [
    path("", public.home, name="home"),
    path("design-system/", public.design_system, name="design-system"),
    path("hospitales/", public.hospitals_list, name="hospitals-list"),
    path("refugios/", public.shelters_list, name="shelters-list"),
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
