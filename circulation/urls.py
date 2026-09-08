from django.urls import path

from .views import GuichetView

app_name = "circulation"

urlpatterns = [
    path("", GuichetView.as_view(), name="guichet"),
]
