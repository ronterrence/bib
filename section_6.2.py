# =============================================================================
# Section 6.2: Core Domain Models
# =============================================================================

# catalogue/models.py
from django.db import models
from django.core.exceptions import ProtectedError

class StatutDocument(models.TextChoices):
    DISPONIBLE = "DISPONIBLE", "Disponible"
    EN_PRET = "EN_PRET", "En prêt"
    EN_CONSULTATION = "EN_CONSULTATION", "En consultation sur place"
    PERDU = "PERDU", "Perdu"
    VOLE = "VOLE", "Volé"
    HORS_SERVICE = "HORS_SERVICE", "Hors service"

class Document(models.Model):
    cote = models.AutoField(primary_key=True)
    titre = models.CharField(max_length=255)
    statut = models.CharField(max_length=20, choices=StatutDocument.choices, default=StatutDocument.DISPONIBLE)
    date_acquisition = models.DateField(auto_now_add=True)
    est_hors_service = models.BooleanField(default=False)

    def delete(self, *args, **kwargs):
        raise ProtectedError("Les fiches documents ne peuvent jamais être supprimées.", self)

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
    caution_montant_requis = models.DecimalField(max_digits=6, decimal_places=2, default=15.00)

class Microfilm(Document):
    document_associe = models.ForeignKey(Document, on_delete=models.PROTECT, related_name="microfilms")


# adherents/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ProtectedError
from django.utils import timezone

class Adherent(models.Model):
    numero_lecteur = models.AutoField(primary_key=True)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    adresse = models.TextField()
    email = models.EmailField(blank=True)
    telephone = models.CharField(max_length=20, blank=True)
    cotisation_a_jour = models.BooleanField(default=True)
    est_actif = models.BooleanField(default=True)

    def delete(self, *args, **kwargs):
        raise ProtectedError("Les fiches lecteurs ne peuvent jamais être supprimées.", self)

    def nb_emprunts_en_cours(self):
        return self.prets.filter(date_restitution__isnull=True).count()

    def __str__(self):
        return f"[{self.numero_lecteur}] {self.nom} {self.prenom}"

class ProfilUtilisateur(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profil")
    est_benevole = models.BooleanField(default=False)
    date_fin_habilitation = models.DateField(null=True, blank=True)

    @property
    def a_acces_circulation(self):
        if self.user.is_superuser or self.user.is_staff:
            return True
        if self.est_benevole and self.date_fin_habilitation:
            return self.date_fin_habilitation >= timezone.now().date()
        return False


# circulation/models.py
from datetime import timedelta
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from catalogue.models import Document, Livre, Journal, CdRom, Microfilm, StatutDocument
from adherents.models import Adherent

class TypePret(models.TextChoices):
    DOMICILE = "DOMICILE", "Prêt à domicile"
    SUR_PLACE = "SUR_PLACE", "Consultation sur place"

class EcranLecture(models.Model):
    numero = models.IntegerField(primary_key=True)
    est_libre = models.BooleanField(default=True)

    def __str__(self):
        return f"Écran N°{self.numero}"

class Pret(models.Model):
    adherent = models.ForeignKey(Adherent, on_delete=models.PROTECT, related_name="prets")
    document = models.ForeignKey(Document, on_delete=models.PROTECT, related_name="prets")
    type_pret = models.CharField(max_length=20, choices=TypePret.choices)
    date_emprunt = models.DateTimeField(default=timezone.now)
    date_restitution = models.DateTimeField(null=True, blank=True)
    montant_caution = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    caution_restituee = models.BooleanField(default=False)
    poste_ecran = models.ForeignKey(EcranLecture, on_delete=models.SET_NULL, null=True, blank=True)

    def est_en_retard(self):
        if self.date_restitution:
            return False
        return timezone.now() > self.date_emprunt + timedelta(days=28)

    def clean(self):
        super().clean()

        if not self.adherent.cotisation_a_jour:
            raise ValidationError("La cotisation de l'adhérent n'est pas à jour.")

        if not self.pk and self.document.statut != StatutDocument.DISPONIBLE:
            raise ValidationError("Le document sélectionné n'est pas disponible.")

        # Quota verification
        active_loans = Pret.objects.filter(adherent=self.adherent, date_restitution__isnull=True)
        if self.pk:
            active_loans = active_loans.exclude(pk=self.pk)
        if active_loans.count() >= 5:
            raise ValidationError("Le lecteur a déjà atteint le quota maximum de 5 emprunts en cours.")

        # Home loan eligibility
        if self.type_pret == TypePret.DOMICILE:
            if hasattr(self.document, "journal") or hasattr(self.document, "microfilm"):
                raise ValidationError("Ce type de document est consultable uniquement sur place.")
            if hasattr(self.document, "livre") and self.document.livre.consultable_uniquement_sur_place:
                raise ValidationError("Ce livre est consultable uniquement sur place.")

        # Deposit verification for CD-ROM
        if hasattr(self.document, "cdrom"):
            cd = self.document.cdrom
            if self.montant_caution < cd.caution_montant_requis:
                raise ValidationError(f"Une caution minimale de {cd.caution_montant_requis} € est obligatoire pour l'emprunt d'un CD-ROM.")

        # Microfilm screen allocation
        if hasattr(self.document, "microfilm"):
            if not self.poste_ecran or not self.poste_ecran.est_libre:
                raise ValidationError("Un écran de lecture libre doit être obligatoirement affecté pour visualiser un microfilm.")

    def save(self, *args, **kwargs):
        self.full_clean()
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new and not self.date_restitution:
            self.document.statut = (
                StatutDocument.EN_PRET if self.type_pret == TypePret.DOMICILE else StatutDocument.EN_CONSULTATION
            )
            self.document.save(update_fields=["statut"])
            if self.poste_ecran:
                self.poste_ecran.est_libre = False
                self.poste_ecran.save(update_fields=["est_libre"])

    def restituer(self):
        self.date_restitution = timezone.now()
        if hasattr(self.document, "cdrom"):
            self.caution_restituee = True
        self.save()

        self.document.statut = StatutDocument.DISPONIBLE
        self.document.save(update_fields=["statut"])

        if self.poste_ecran:
            self.poste_ecran.est_libre = True
            self.poste_ecran.save(update_fields=["est_libre"])