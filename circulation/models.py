from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models.deletion import ProtectedError
from django.utils import timezone

from adherents.models import Adherent
from catalogue.models import Document, StatutDocument


class TypePret(models.TextChoices):
    DOMICILE = "DOMICILE", "Prêt à domicile"
    SUR_PLACE = "SUR_PLACE", "Consultation sur place"


class EcranLecture(models.Model):
    numero = models.IntegerField(primary_key=True)
    est_libre = models.BooleanField(default=True)

    def __str__(self):
        return f"Écran N°{self.numero}"


class PretQuerySet(models.QuerySet):
    def delete(self):
        raise ProtectedError(
            "Les prêts ne peuvent pas être supprimés.",
            set(self),
        )


class Pret(models.Model):
    adherent = models.ForeignKey(
        Adherent,
        on_delete=models.PROTECT,
        related_name="prets",
    )
    document = models.ForeignKey(
        Document,
        on_delete=models.PROTECT,
        related_name="prets",
    )
    type_pret = models.CharField(max_length=20, choices=TypePret.choices)
    date_emprunt = models.DateTimeField(default=timezone.now)
    date_restitution = models.DateTimeField(null=True, blank=True)
    montant_caution = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    caution_restituee = models.BooleanField(default=False)
    poste_ecran = models.ForeignKey(
        EcranLecture,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    objects = PretQuerySet.as_manager()

    def _document_type(self):
        if not self.document_id:
            return None
        document = self.document
        for type_name in ("livre", "journal", "cdrom", "microfilm"):
            if hasattr(document, type_name):
                return type_name
        return None

    def _previous_values(self):
        if not self.pk:
            return None
        return (
            type(self)
            .objects.filter(pk=self.pk)
            .values(
                "adherent_id",
                "document_id",
                "type_pret",
                "date_emprunt",
                "date_restitution",
                "montant_caution",
                "poste_ecran_id",
            )
            .first()
        )

    def est_en_retard(self):
        if self.date_restitution:
            return False
        return timezone.now() > self.date_emprunt + timedelta(days=28)

    def clean(self):
        super().clean()
        errors = {}
        previous = self._previous_values()

        if previous:
            immutable_fields = {
                "adherent": (previous["adherent_id"], self.adherent_id),
                "document": (previous["document_id"], self.document_id),
                "type_pret": (previous["type_pret"], self.type_pret),
                "date_emprunt": (previous["date_emprunt"], self.date_emprunt),
                "montant_caution": (
                    previous["montant_caution"],
                    self.montant_caution,
                ),
                "poste_ecran": (
                    previous["poste_ecran_id"],
                    self.poste_ecran_id,
                ),
            }
            for field, (old_value, new_value) in immutable_fields.items():
                if old_value != new_value:
                    errors[field] = "Ce champ est immuable après la création du prêt."
            if previous["date_restitution"] and not self.date_restitution:
                errors["date_restitution"] = "Un prêt restitué ne peut pas être rouvert."

        # Origination rules must not prevent a later return (for example, after
        # the member's subscription expires or a microfilm screen is reserved).
        if not previous:
            if self.date_restitution:
                errors["date_restitution"] = (
                    "Un nouveau prêt ne peut pas être déjà restitué."
                )
            if self.caution_restituee:
                errors["caution_restituee"] = (
                    "La caution ne peut pas être restituée à la création."
                )

            if self.adherent_id:
                adherent = self.adherent
                if not adherent.est_actif:
                    errors["adherent"] = "L'adhérent est inactif."
                elif not adherent.cotisation_a_jour:
                    errors["adherent"] = "La cotisation de l'adhérent n'est pas à jour."
                elif (
                    Pret.objects.filter(
                        adherent_id=self.adherent_id,
                        date_restitution__isnull=True,
                    ).count()
                    >= 5
                ):
                    errors["adherent"] = (
                        "Le lecteur a déjà atteint le quota maximum de 5 "
                        "emprunts en cours."
                    )

            document_type = None
            if self.document_id:
                document = self.document
                document_type = self._document_type()
                if (
                    document.est_hors_service
                    or document.statut != StatutDocument.DISPONIBLE
                ):
                    errors["document"] = (
                        "Le document sélectionné n'est pas disponible."
                    )

                if self.type_pret == TypePret.DOMICILE:
                    if document_type in {"journal", "microfilm"}:
                        errors["type_pret"] = (
                            "Ce type de document est consultable uniquement sur place."
                        )
                    elif (
                        document_type == "livre"
                        and document.livre.consultable_uniquement_sur_place
                    ):
                        errors["type_pret"] = (
                            "Ce livre est consultable uniquement sur place."
                        )

                if document_type == "cdrom":
                    if self.montant_caution < document.cdrom.caution_montant_requis:
                        errors["montant_caution"] = (
                            "Une caution minimale de "
                            f"{document.cdrom.caution_montant_requis} € est obligatoire "
                            "pour l'emprunt d'un CD-ROM."
                        )

            if document_type == "microfilm":
                if not self.poste_ecran_id:
                    errors["poste_ecran"] = (
                        "Un écran de lecture libre doit être affecté au microfilm."
                    )
                elif not self.poste_ecran.est_libre:
                    errors["poste_ecran"] = (
                        "L'écran de lecture sélectionné n'est pas libre."
                    )
            elif self.poste_ecran_id:
                errors["poste_ecran"] = (
                    "Un écran de lecture ne peut être affecté qu'à un microfilm."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        with transaction.atomic():
            is_new = self.pk is None
            previous = None
            if not is_new:
                previous = (
                    type(self)
                    .objects.select_for_update()
                    .filter(pk=self.pk)
                    .values("date_restitution")
                    .first()
                )

            if self.adherent_id:
                self.adherent = Adherent.objects.select_for_update().get(
                    pk=self.adherent_id
                )
            if self.document_id:
                self.document = Document.objects.select_for_update().get(
                    pk=self.document_id
                )
            if self.poste_ecran_id:
                self.poste_ecran = EcranLecture.objects.select_for_update().get(
                    pk=self.poste_ecran_id
                )

            is_return = bool(
                previous
                and previous["date_restitution"] is None
                and self.date_restitution is not None
            )
            if is_return and self._document_type() == "cdrom":
                self.caution_restituee = True

            self.full_clean()
            result = super().save(*args, **kwargs)

            if is_new:
                self.document.statut = (
                    StatutDocument.EN_PRET
                    if self.type_pret == TypePret.DOMICILE
                    else StatutDocument.EN_CONSULTATION
                )
                self.document.save(update_fields=["statut"])
                if self.poste_ecran_id:
                    self.poste_ecran.est_libre = False
                    self.poste_ecran.save(update_fields=["est_libre"])
            elif is_return:
                if not self.document.est_hors_service and self.document.statut not in {
                    StatutDocument.PERDU,
                    StatutDocument.VOLE,
                    StatutDocument.HORS_SERVICE,
                }:
                    self.document.statut = StatutDocument.DISPONIBLE
                    self.document.save(update_fields=["statut"])
                if self.poste_ecran_id:
                    self.poste_ecran.est_libre = True
                    self.poste_ecran.save(update_fields=["est_libre"])

            return result

    def restituer(self):
        if not self.pk:
            raise ValidationError("Un prêt non enregistré ne peut pas être restitué.")
        with transaction.atomic():
            current = type(self).objects.select_for_update().get(pk=self.pk)
            if current.date_restitution:
                self.date_restitution = current.date_restitution
                self.caution_restituee = current.caution_restituee
                return
            self.date_restitution = timezone.now()
            self.save()

    def delete(self, *args, **kwargs):
        raise ProtectedError(
            "Les prêts ne peuvent pas être supprimés.",
            {self},
        )

    def __str__(self):
        return f"Prêt {self.pk} - {self.adherent} - {self.document}"
