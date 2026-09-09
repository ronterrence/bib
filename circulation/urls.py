from django.urls import path
from django.views.generic import RedirectView

from .views import GuichetView, ResumeAdherentView, ResumeDocumentView

app_name = "circulation"

urlpatterns = [
    path(
        "",
        RedirectView.as_view(pattern_name="circulation:guichet", permanent=False),
        name="accueil",
    ),
    path("guichet/", GuichetView.as_view(), name="guichet"),
    path(
        "api/adherents/<int:numero_lecteur>/",
        ResumeAdherentView.as_view(),
        name="resume_adherent",
    ),
    path(
        "api/documents/<int:cote>/",
        ResumeDocumentView.as_view(),
        name="resume_document",
    ),
]
