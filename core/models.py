from django.conf import settings
from django.db import models
from django.utils import timezone


class ProfilUtilisateur(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profil",
    )
    est_benevole = models.BooleanField(default=False)
    date_fin_habilitation = models.DateField(null=True, blank=True)

    @property
    def a_acces_circulation(self):
        if self.user.is_superuser or self.user.is_staff:
            return True
        return bool(
            self.est_benevole
            and self.date_fin_habilitation
            and self.date_fin_habilitation >= timezone.localdate()
        )

    def __str__(self):
        return f"Profil de {self.user.get_username()}"
