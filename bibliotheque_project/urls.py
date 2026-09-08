"""Root URL configuration for bibliotheque_project."""
from django.contrib import admin
from django.urls import include, path

from catalogue.views import liste

urlpatterns = [
    path("", liste, name="accueil"),
    path("catalogue/", include("catalogue.urls")),
    path("circulation/", include("circulation.urls")),
    path("relances/", include("relances.urls")),
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
]
