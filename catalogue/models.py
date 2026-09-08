from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.deletion import ProtectedError


class StatutDocument(models.TextChoices):
    DISPONIBLE = "DISPONIBLE", "Disponible"
    EN_PRET = "EN_PRET", "En prêt"
    EN_CONSULTATION = "EN_CONSULTATION", "En consultation sur place"
    PERDU = "PERDU", "Perdu"
    VOLE = "VOLE", "Volé"
    HORS_SERVICE = "HORS_SERVICE", "Hors service"


class DocumentQuerySet(models.QuerySet):
    def delete(self):
        raise ProtectedError(
            "Les fiches documents ne peuvent jamais être supprimées.",
            set(self),
        )


class Document(models.Model):
    cote = models.AutoField(primary_key=True)
    titre = models.CharField(max_length=255)
    statut = models.CharField(
        max_length=20,
        choices=StatutDocument.choices,
        default=StatutDocument.DISPONIBLE,
    )
    date_acquisition = models.DateField(auto_now_add=True)
    est_hors_service = models.BooleanField(default=False)

    objects = DocumentQuerySet.as_manager()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cote_originale = self.pk

    def save(self, *args, **kwargs):
        if self._cote_originale is not None and self.pk != self._cote_originale:
            raise ValidationError({"cote": "La cote d'un document est immuable."})
        result = super().save(*args, **kwargs)
        self._cote_originale = self.pk
        return result

    def delete(self, *args, **kwargs):
        raise ProtectedError(
            "Les fiches documents ne peuvent jamais être supprimées.",
            {self},
        )

    def __str__(self):
        return f"[{self.cote}] {self.titre}"


class Livre(Document):
    auteur = models.CharField(max_length=255)
    consultable_uniquement_sur_place = models.BooleanField(default=False)


class Journal(Document):
    date_parution = models.DateField()


class CdRom(Document):
    auteur_ou_editeur = models.CharField(max_length=255)
    thematique = models.CharField(max_length=255)
    caution_montant_requis = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("15.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )


class Microfilm(Document):
    document_associe = models.ForeignKey(
        Document,
        on_delete=models.PROTECT,
        related_name="microfilms",
    )

    def clean(self):
        super().clean()
        if not self.document_associe_id:
            return
        document = self.document_associe
        if not (hasattr(document, "livre") or hasattr(document, "journal")):
            raise ValidationError(
                {
                    "document_associe": (
                        "Un microfilm doit référencer un livre ou un journal."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
