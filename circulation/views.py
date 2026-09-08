from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from .forms import PretForm, RetourForm


class AccesCirculationRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        profil = getattr(request.user, "profil", None)
        if not request.user.is_active or not (
            request.user.is_staff
            or request.user.is_superuser
            or (profil and profil.a_acces_circulation)
        ):
            raise PermissionDenied("Accès au guichet non autorisé.")
        return super().dispatch(request, *args, **kwargs)


class GuichetView(AccesCirculationRequiredMixin, View):
    template_name = "circulation/guichet.html"

    def get(self, request):
        return self.render_forms(request, PretForm(), RetourForm(), "pret")

    def post(self, request):
        action = request.POST.get("action")
        pret_form = PretForm()
        retour_form = RetourForm()

        if action == "retour":
            retour_form = RetourForm(request.POST)
            if retour_form.is_valid():
                pret = retour_form.pret
                remboursement = (
                    pret.montant_caution
                    if hasattr(pret.document, "cdrom") and pret.montant_caution
                    else None
                )
                adherent = pret.adherent
                pret.restituer()
                messages.success(request, "La restitution a bien été enregistrée.")
                if remboursement:
                    messages.warning(
                        request,
                        f"Rembourser la caution de {remboursement:.2f} € à l'adhérent {adherent}.",
                    )
                return redirect(reverse("circulation:guichet") + "?tab=retour")
            return self.render_forms(request, pret_form, retour_form, "retour")

        pret_form = PretForm(request.POST)
        if pret_form.is_valid():
            try:
                pret = pret_form.save()
            except ValidationError as exc:
                pret_form.add_error(None, exc)
            else:
                messages.success(
                    request,
                    f"Prêt enregistré avec succès : {pret.document}.",
                )
                return redirect("circulation:guichet")
        return self.render_forms(request, pret_form, retour_form, "pret")

    def render_forms(self, request, pret_form, retour_form, active_tab):
        if request.GET.get("tab") == "retour":
            active_tab = "retour"
        return render(
            request,
            self.template_name,
            {
                "pret_form": pret_form,
                "retour_form": retour_form,
                "active_tab": active_tab,
            },
        )
