from django.urls import path

from .views import DashboardRetardsView, ImprimerLettresView

app_name = "relances"

urlpatterns = [
    path("retards/", DashboardRetardsView.as_view(), name="dashboard"),
    path("imprimer-lettres/", ImprimerLettresView.as_view(), name="imprimer_lettres"),
]
