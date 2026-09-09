from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from circulation.models import DUREE_PRET, Pret


class CanalRelance(models.TextChoices):
    COURRIER = "COURRIER", "Courrier postal"
    EMAIL = "EMAIL", "E-mail"


class Relance(models.Model):
    pret = models.ForeignKey(
        Pret,
        on_delete=models.PROTECT,
        related_name="relances",
    )
    date_emission = models.DateTimeField(auto_now_add=True)
    emetteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="relances_emises",
    )
    canal = models.CharField(
        max_length=20,
        choices=CanalRelance.choices,
        default=CanalRelance.COURRIER,
    )

    class Meta:
        ordering = ("-date_emission",)

    def __str__(self):
        return f"Relance {self.pk} - prêt {self.pret_id}"

    @classmethod
    def generer_lettre(cls, *, pret, emetteur=None, canal=CanalRelance.COURRIER):
        if canal not in CanalRelance.values:
            raise ValidationError({"canal": "Le canal de relance est invalide."})
        if pret.date_restitution or pret.date_emprunt >= timezone.now() - DUREE_PRET:
            raise ValidationError("Ce prêt n'est pas éligible à une relance.")
        return cls.objects.create(pret=pret, emetteur=emetteur, canal=canal)
