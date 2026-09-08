from decimal import Decimal

from django import forms

from adherents.models import Adherent
from catalogue.models import Document

from .models import EcranLecture, Pret, TypePret


class PretForm(forms.Form):
    numero_lecteur = forms.IntegerField(label="Numéro de lecteur", min_value=1)
    cote = forms.IntegerField(label="Cote du document", min_value=1)
    type_pret = forms.ChoiceField(label="Type de prêt", choices=TypePret.choices)
    montant_caution = forms.DecimalField(
        label="Montant de la caution",
        required=False,
        min_value=Decimal("0.00"),
        max_digits=6,
        decimal_places=2,
        initial=Decimal("0.00"),
    )
    poste_ecran = forms.ModelChoiceField(
        label="Poste écran",
        queryset=EcranLecture.objects.order_by("numero"),
        required=False,
        empty_label="Aucun",
    )

    def clean_numero_lecteur(self):
        numero = self.cleaned_data["numero_lecteur"]
        try:
            self.adherent = Adherent.objects.get(pk=numero)
        except Adherent.DoesNotExist as exc:
            raise forms.ValidationError("Aucun adhérent ne correspond à ce numéro.") from exc
        return numero

    def clean_cote(self):
        cote = self.cleaned_data["cote"]
        try:
            self.document = Document.objects.get(pk=cote)
        except Document.DoesNotExist as exc:
            raise forms.ValidationError("Aucun document ne correspond à cette cote.") from exc
        return cote

    def save(self):
        pret = Pret(
            adherent=self.adherent,
            document=self.document,
            type_pret=self.cleaned_data["type_pret"],
            montant_caution=self.cleaned_data.get("montant_caution") or Decimal("0.00"),
            poste_ecran=self.cleaned_data.get("poste_ecran"),
        )
        pret.save()
        return pret


class RetourForm(forms.Form):
    cote = forms.IntegerField(label="Cote du document", min_value=1)

    def clean_cote(self):
        cote = self.cleaned_data["cote"]
        try:
            self.pret = Pret.objects.select_related("adherent", "document").get(
                document_id=cote,
                date_restitution__isnull=True,
            )
        except Pret.DoesNotExist as exc:
            raise forms.ValidationError(
                "Aucun prêt en cours ne correspond à cette cote."
            ) from exc
        return cote
