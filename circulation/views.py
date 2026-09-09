from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View

from adherents.models import Adherent
from catalogue.models import Document, StatutDocument

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
        feedback = request.session.pop("retour_feedback", None)
        return self.render_forms(
            request,
            PretForm(),
            RetourForm(),
            "retour" if feedback else "pret",
            feedback,
        )

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
                jours_retard = max((timezone.now() - pret.date_echeance).days, 0)
                pret.restituer()
                messages.success(request, "La restitution a bien été enregistrée.")
                request.session["retour_feedback"] = {
                    "jours_retard": jours_retard,
                    "remboursement": (
                        f"{remboursement:.2f}" if remboursement else None
                    ),
                    "adherent": str(adherent),
                }
                return redirect(reverse("circulation:guichet") + "?tab=retour")
            return self.render_forms(request, pret_form, retour_form, "retour")

        pret_form = PretForm(request.POST)
        if pret_form.is_valid():
            try:
                pret = pret_form.save()
            except ValidationError as exc:
                correspondances = {
                    "adherent": "numero_lecteur",
                    "document": "cote",
                }
                if hasattr(exc, "error_dict"):
                    for champ_modele, erreurs in exc.error_dict.items():
                        champ_formulaire = correspondances.get(champ_modele, champ_modele)
                        if champ_formulaire not in pret_form.fields:
                            champ_formulaire = None
                        for erreur in erreurs:
                            pret_form.add_error(champ_formulaire, erreur)
                else:
                    pret_form.add_error(None, exc)
            else:
                messages.success(
                    request,
                    f"Prêt enregistré avec succès : {pret.document}.",
                )
                return redirect("circulation:guichet")
        return self.render_forms(request, pret_form, retour_form, "pret")

    def render_forms(
        self, request, pret_form, retour_form, active_tab, retour_feedback=None
    ):
        if request.GET.get("tab") == "retour":
            active_tab = "retour"
        return render(
            request,
            self.template_name,
            {
                "pret_form": pret_form,
                "retour_form": retour_form,
                "active_tab": active_tab,
                "retour_feedback": retour_feedback,
            },
        )


class ResumeAdherentView(AccesCirculationRequiredMixin, View):
    def get(self, request, numero_lecteur):
        adherent = get_object_or_404(Adherent, pk=numero_lecteur)
        emprunts = adherent.nb_emprunts_en_cours()
        return JsonResponse(
            {
                "nom": f"{adherent.nom} {adherent.prenom}",
                "emprunts_en_cours": emprunts,
                "quota": 5,
                "cotisation_a_jour": adherent.cotisation_a_jour,
                "est_actif": adherent.est_actif,
                "peut_emprunter": adherent.peut_emprunter(),
            }
        )


class ResumeDocumentView(AccesCirculationRequiredMixin, View):
    def get(self, request, cote):
        document = get_object_or_404(
            Document.objects.select_related("livre", "journal", "cdrom", "microfilm"),
            pk=cote,
        )
        if hasattr(document, "cdrom"):
            document_type = "cdrom"
            caution = str(document.cdrom.caution_montant_requis)
        elif hasattr(document, "microfilm"):
            document_type = "microfilm"
            caution = None
        elif hasattr(document, "journal"):
            document_type = "journal"
            caution = None
        else:
            document_type = "livre"
            caution = None
        return JsonResponse(
            {
                "titre": document.titre,
                "type": document_type,
                "disponible": (
                    document.statut == StatutDocument.DISPONIBLE
                    and not document.est_hors_service
                ),
                "caution_requise": caution,
                "ecran_requis": document_type == "microfilm",
            }
        )
