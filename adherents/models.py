from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.deletion import ProtectedError


class AdherentQuerySet(models.QuerySet):
    def delete(self):
        raise ProtectedError(
            "Les fiches lecteurs ne peuvent jamais être supprimées.",
            set(self),
        )


class Adherent(models.Model):
    numero_lecteur = models.AutoField(primary_key=True)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    adresse = models.TextField()
    email = models.EmailField(blank=True)
    telephone = models.CharField(max_length=20, blank=True)
    cotisation_a_jour = models.BooleanField(default=True)
    est_actif = models.BooleanField(default=True)

    objects = AdherentQuerySet.as_manager()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._numero_lecteur_original = self.pk

    def save(self, *args, **kwargs):
        if (
            self._numero_lecteur_original is not None
            and self.pk != self._numero_lecteur_original
        ):
            raise ValidationError(
                {"numero_lecteur": "Le numéro de lecteur est immuable."}
            )
        result = super().save(*args, **kwargs)
        self._numero_lecteur_original = self.pk
        return result

    def delete(self, *args, **kwargs):
        raise ProtectedError(
            "Les fiches lecteurs ne peuvent jamais être supprimées.",
            {self},
        )

    def nb_emprunts_en_cours(self):
        return self.prets.filter(date_restitution__isnull=True).count()

    def peut_emprunter(self):
        return (
            self.est_actif
            and self.cotisation_a_jour
            and self.nb_emprunts_en_cours() < 5
        )

    def __str__(self):
        return f"[{self.numero_lecteur}] {self.nom} {self.prenom}"


# Temporary import compatibility for callers that used the former app location.
from core.models import ProfilUtilisateur  # noqa: E402,F401
