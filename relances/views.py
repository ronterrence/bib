from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views import View

from circulation.models import Pret

from .models import CanalRelance, Relance


def prets_en_retard():
    limite = timezone.now() - timedelta(days=28)
    return Pret.objects.filter(
        date_restitution__isnull=True,
        date_emprunt__lt=limite,
    ).select_related("adherent", "document")


class StaffRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not request.user.is_active or not request.user.is_staff:
            raise PermissionDenied("Cette page est réservée au personnel.")
        return super().dispatch(request, *args, **kwargs)


class DashboardRetardsView(StaffRequiredMixin, View):
    template_name = "relances/dashboard.html"

    def get(self, request):
        maintenant = timezone.now()
        retards = list(prets_en_retard().order_by("date_emprunt"))
        for pret in retards:
            pret.jours_retard = (maintenant - pret.date_emprunt).days - 28
        return render(
            request,
            self.template_name,
            {
                "retards": retards,
                "canaux": CanalRelance.choices,
            },
        )


class ImprimerLettresView(StaffRequiredMixin, View):
    template_name = "relances/lettre_impression.html"

    def post(self, request):
        ids_bruts = request.POST.getlist("prets")
        try:
            ids = sorted({int(value) for value in ids_bruts})
        except (TypeError, ValueError):
            ids = []

        canal = request.POST.get("canal", CanalRelance.COURRIER)
        if canal not in CanalRelance.values:
            canal = CanalRelance.COURRIER

        if not ids:
            messages.error(request, "Sélectionnez au moins un prêt en retard.")
            return redirect("relances:dashboard")

        prets = list(prets_en_retard().filter(pk__in=ids).order_by("adherent__nom"))
        if not prets:
            messages.error(request, "Aucun des prêts sélectionnés n'est en retard.")
            return redirect("relances:dashboard")

        maintenant = timezone.now()
        lettres = []
        with transaction.atomic():
            for pret in prets:
                relance = Relance.objects.create(
                    pret=pret,
                    emetteur=request.user,
                    canal=canal,
                )
                lettres.append(
                    {
                        "pret": pret,
                        "relance": relance,
                        "jours_retard": (maintenant - pret.date_emprunt).days - 28,
                        "date_echeance": pret.date_emprunt + timedelta(days=28),
                    }
                )

        return render(
            request,
            self.template_name,
            {
                "lettres": lettres,
                "date_impression": timezone.localdate(),
            },
        )
