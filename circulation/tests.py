from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from adherents.models import Adherent
from catalogue.models import (
    CdRom,
    Document,
    Journal,
    Livre,
    Microfilm,
    StatutDocument,
)
from circulation.models import EcranLecture, Pret, TypePret
from core.models import ProfilUtilisateur


class PretRulesTestCase(TestCase):
    def setUp(self):
        self.adherent = Adherent.objects.create(
            nom="Dupont",
            prenom="Alice",
            adresse="1 rue de la Bibliothèque",
        )

    def create_livre(self, suffix, **kwargs):
        return Livre.objects.create(
            titre=f"Livre {suffix}",
            auteur="Auteur",
            **kwargs,
        )

    def create_pret(self, document, **kwargs):
        values = {
            "adherent": self.adherent,
            "document": document,
            "type_pret": TypePret.DOMICILE,
        }
        values.update(kwargs)
        return Pret.objects.create(**values)

    def test_quota_de_cinq_prets_et_recuperation_du_creneau(self):
        prets = [
            self.create_pret(self.create_livre(index)) for index in range(1, 6)
        ]
        sixieme_document = self.create_livre(6)

        self.assertEqual(self.adherent.nb_emprunts_en_cours(), 5)
        self.assertFalse(self.adherent.peut_emprunter())
        with self.assertRaises(ValidationError):
            self.create_pret(sixieme_document)

        prets[0].restituer()
        self.adherent.refresh_from_db()
        self.assertEqual(self.adherent.nb_emprunts_en_cours(), 4)
        self.assertTrue(self.adherent.peut_emprunter())

        self.create_pret(sixieme_document)
        self.assertEqual(self.adherent.nb_emprunts_en_cours(), 5)

    def test_journal_interdit_en_pret_a_domicile(self):
        journal = Journal.objects.create(
            titre="Journal municipal",
            date_parution=date.today(),
        )

        with self.assertRaises(ValidationError):
            self.create_pret(journal)

    def test_microfilm_interdit_en_pret_a_domicile(self):
        reference = self.create_livre("référence")
        microfilm = Microfilm.objects.create(
            titre="Microfilm des archives",
            document_associe=reference,
        )
        ecran = EcranLecture.objects.create(numero=1)

        with self.assertRaises(ValidationError):
            self.create_pret(microfilm, poste_ecran=ecran)

    def test_livre_special_interdit_en_pret_a_domicile(self):
        livre = self.create_livre(
            "consultation",
            consultable_uniquement_sur_place=True,
        )

        with self.assertRaises(ValidationError):
            self.create_pret(livre)

    def test_cdrom_exige_la_caution_minimale(self):
        cdrom = CdRom.objects.create(
            titre="Encyclopédie multimédia",
            auteur_ou_editeur="Mairie",
            thematique="Histoire",
            caution_montant_requis=Decimal("20.00"),
        )

        with self.assertRaises(ValidationError):
            self.create_pret(cdrom, montant_caution=Decimal("19.99"))

        pret = self.create_pret(cdrom, montant_caution=Decimal("20.00"))
        self.assertFalse(pret.caution_restituee)

    def test_restitution_cdrom_rembourse_la_caution(self):
        cdrom = CdRom.objects.create(
            titre="Atlas sur CD-ROM",
            auteur_ou_editeur="Cartographe",
            thematique="Géographie",
            caution_montant_requis=Decimal("15.00"),
        )
        pret = self.create_pret(cdrom, montant_caution=Decimal("15.00"))

        pret.restituer()
        pret.refresh_from_db()
        cdrom.refresh_from_db()

        self.assertIsNotNone(pret.date_restitution)
        self.assertTrue(pret.caution_restituee)
        self.assertEqual(cdrom.statut, StatutDocument.DISPONIBLE)

    def test_microfilm_exige_un_ecran(self):
        reference = self.create_livre("source")
        microfilm = Microfilm.objects.create(
            titre="Archives sans écran",
            document_associe=reference,
        )

        with self.assertRaises(ValidationError):
            self.create_pret(microfilm, type_pret=TypePret.SUR_PLACE)

    def test_microfilm_refuse_un_ecran_occupe(self):
        reference = self.create_livre("source occupée")
        microfilm = Microfilm.objects.create(
            titre="Archives avec écran occupé",
            document_associe=reference,
        )
        ecran = EcranLecture.objects.create(numero=2, est_libre=False)

        with self.assertRaises(ValidationError):
            self.create_pret(
                microfilm,
                type_pret=TypePret.SUR_PLACE,
                poste_ecran=ecran,
            )

    def test_microfilm_reserve_puis_libere_ecran(self):
        reference = self.create_livre("source disponible")
        microfilm = Microfilm.objects.create(
            titre="Archives consultables",
            document_associe=reference,
        )
        ecran = EcranLecture.objects.create(numero=3)

        pret = self.create_pret(
            microfilm,
            type_pret=TypePret.SUR_PLACE,
            poste_ecran=ecran,
        )
        ecran.refresh_from_db()
        microfilm.refresh_from_db()
        self.assertFalse(ecran.est_libre)
        self.assertEqual(microfilm.statut, StatutDocument.EN_CONSULTATION)

        pret.restituer()
        ecran.refresh_from_db()
        microfilm.refresh_from_db()
        self.assertTrue(ecran.est_libre)
        self.assertEqual(microfilm.statut, StatutDocument.DISPONIBLE)

    def test_cotisation_non_a_jour_bloque_le_pret(self):
        self.adherent.cotisation_a_jour = False
        self.adherent.save(update_fields=["cotisation_a_jour"])

        with self.assertRaises(ValidationError):
            self.create_pret(self.create_livre("cotisation"))

    def test_document_non_disponible_bloque_le_pret(self):
        livre = self.create_livre("indisponible")
        livre.statut = StatutDocument.EN_PRET
        livre.save(update_fields=["statut"])

        with self.assertRaises(ValidationError):
            self.create_pret(livre)

    def test_detection_retard_strictement_superieur_a_28_jours(self):
        maintenant = timezone.now()
        pret_non_en_retard = Pret(
            date_emprunt=maintenant - timedelta(days=27),
            date_restitution=None,
        )
        pret_en_retard = Pret(
            date_emprunt=maintenant - timedelta(days=29),
            date_restitution=None,
        )
        pret_restitue = Pret(
            date_emprunt=maintenant - timedelta(days=29),
            date_restitution=maintenant,
        )

        self.assertFalse(pret_non_en_retard.est_en_retard())
        self.assertTrue(pret_en_retard.est_en_retard())
        self.assertFalse(pret_restitue.est_en_retard())


class SuppressionInterditeTestCase(TestCase):
    def test_suppression_document_leve_protected_error(self):
        document = Livre.objects.create(titre="Inaliénable", auteur="Auteur")
        cote = document.cote

        with self.assertRaises(ProtectedError):
            document.delete()

        self.assertTrue(Document.objects.filter(pk=cote).exists())

    def test_suppression_adherent_leve_protected_error(self):
        adherent = Adherent.objects.create(
            nom="Martin",
            prenom="Bob",
            adresse="2 rue des Archives",
        )
        numero_lecteur = adherent.numero_lecteur

        with self.assertRaises(ProtectedError):
            adherent.delete()

        self.assertTrue(Adherent.objects.filter(pk=numero_lecteur).exists())

    def test_suppression_en_masse_est_egalement_interdite(self):
        document = Livre.objects.create(titre="Lot protégé", auteur="Auteur")
        adherent = Adherent.objects.create(
            nom="Durand",
            prenom="Chloé",
            adresse="3 rue de l'Histoire",
        )

        with self.assertRaises(ProtectedError):
            Document.objects.filter(pk=document.pk).delete()
        with self.assertRaises(ProtectedError):
            Adherent.objects.filter(pk=adherent.pk).delete()


class GuichetViewTestCase(TestCase):
    def setUp(self):
        self.url = reverse("circulation:guichet")
        self.user = get_user_model().objects.create_user(
            username="bibliothecaire",
            password="mot-de-passe",
            is_staff=True,
        )
        self.adherent = Adherent.objects.create(
            nom="Lecteur",
            prenom="Test",
            adresse="3 rue du Guichet",
        )
        self.livre = Livre.objects.create(titre="Livre du guichet", auteur="Auteur")

    def test_utilisateur_anonyme_est_redirige_vers_la_connexion(self):
        response = self.client.get(self.url)

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={self.url}",
            fetch_redirect_response=False,
        )

    def test_ancienne_url_redirige_vers_le_guichet_canonique(self):
        response = self.client.get("/circulation/")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.url)

    def test_utilisateur_sans_habilitation_recoit_403(self):
        utilisateur = get_user_model().objects.create_user(
            username="sans-acces",
            password="mot-de-passe",
        )
        self.client.force_login(utilisateur)

        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_benevole_habilite_accede_au_guichet(self):
        benevole = get_user_model().objects.create_user(
            username="benevole",
            password="mot-de-passe",
        )
        ProfilUtilisateur.objects.create(
            user=benevole,
            est_benevole=True,
            date_fin_habilitation=timezone.localdate(),
        )
        self.client.force_login(benevole)

        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_benevole_expire_recoit_403(self):
        benevole = get_user_model().objects.create_user(
            username="benevole-expire",
            password="mot-de-passe",
        )
        ProfilUtilisateur.objects.create(
            user=benevole,
            est_benevole=True,
            date_fin_habilitation=timezone.localdate() - timedelta(days=1),
        )
        self.client.force_login(benevole)

        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_enregistrement_pret_depuis_le_formulaire(self):
        self.client.force_login(self.user)

        response = self.client.post(
            self.url,
            {
                "action": "pret",
                "numero_lecteur": self.adherent.numero_lecteur,
                "cote": self.livre.cote,
                "type_pret": TypePret.DOMICILE,
                "montant_caution": "0.00",
                "poste_ecran": "",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Pret.objects.filter(date_restitution__isnull=True).count(), 1)
        self.assertContains(response, "Prêt enregistré")

    def test_sixieme_pret_est_refuse_par_le_guichet(self):
        self.client.force_login(self.user)
        for index in range(5):
            Pret.objects.create(
                adherent=self.adherent,
                document=Livre.objects.create(titre=f"Quota {index}", auteur="Auteur"),
                type_pret=TypePret.DOMICILE,
            )

        response = self.client.post(
            self.url,
            {
                "action": "pret",
                "numero_lecteur": self.adherent.numero_lecteur,
                "cote": self.livre.cote,
                "type_pret": TypePret.DOMICILE,
                "montant_caution": "0.00",
                "poste_ecran": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "quota maximum de 5")
        self.assertEqual(Pret.objects.filter(date_restitution__isnull=True).count(), 5)

    def test_api_resume_adherent_et_document(self):
        self.client.force_login(self.user)

        adherent_response = self.client.get(
            reverse("circulation:resume_adherent", args=[self.adherent.pk])
        )
        document_response = self.client.get(
            reverse("circulation:resume_document", args=[self.livre.pk])
        )

        self.assertEqual(adherent_response.json()["quota"], 5)
        self.assertTrue(adherent_response.json()["cotisation_a_jour"])
        self.assertEqual(document_response.json()["type"], "livre")
        self.assertTrue(document_response.json()["disponible"])

    def test_retour_cdrom_affiche_le_message_de_remboursement(self):
        cdrom = CdRom.objects.create(
            titre="CD-ROM à rendre",
            auteur_ou_editeur="Éditeur",
            thematique="Culture",
            caution_montant_requis=Decimal("15.00"),
        )
        Pret.objects.create(
            adherent=self.adherent,
            document=cdrom,
            type_pret=TypePret.DOMICILE,
            montant_caution=Decimal("15.00"),
        )
        self.client.force_login(self.user)

        response = self.client.post(
            self.url,
            {"action": "retour", "cote": cdrom.cote},
            follow=True,
        )

        self.assertContains(
            response,
            "Rembourser la caution de 15.00 €",
        )
        self.assertIsNotNone(Pret.objects.get(document=cdrom).date_restitution)
