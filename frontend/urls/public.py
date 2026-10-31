from django.urls import path

from frontend.views import public

app_name = "public"

urlpatterns = [
    path("", public.home, name="home"),
    path("design-system/", public.design_system, name="design-system"),
]
