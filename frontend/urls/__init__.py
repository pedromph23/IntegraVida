from django.urls import include, path

urlpatterns = [
    path("", include("frontend.urls.public")),
    path("panel/", include("frontend.urls.auth")),
    path("panel/", include("frontend.urls.dashboard")),
]
