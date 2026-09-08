from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from adherents.models import Adherent, ProfilUtilisateur
from catalogue.models import Livre
from circulation.models import Pret, TypePret

from .models import CanalRelance, Relance


class RelancesViewsTestCase(TestCase):
    def setUp(self):
        self.dashboard_url = reverse("relances:dashboard")
        self.impression_url = reverse("relances:imprimer_lettres")
        self.staff = get_user_model().objects.create_user(
            username="responsable-relances",
            password="mot-de-passe",
            is_staff=True,
        )
        self.adherent = Adherent.objects.create(
            nom="Durand",
            prenom="Camille",
            adresse="12 rue des Lecteurs\n75000 Paris",
            email="camille@example.test",
            telephone="01 23 45 67 89",
        )

    def creer_pret(self, titre, jours):
        document = Livre.objects.create(titre=titre, auteur="Auteur")
        return Pret.objects.create(
            adherent=self.adherent,
            document=document,
            type_pret=TypePret.DOMICILE,
            date_emprunt=timezone.now() - timedelta(days=jours),
        )

    def test_anonyme_est_redirige_vers_la_connexion(self):
        response = self.client.get(self.dashboard_url)

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={self.dashboard_url}",
            fetch_redirect_response=False,
        )

    def test_benevole_ne_peut_pas_acceder_au_dashboard(self):
        benevole = get_user_model().objects.create_user(
            username="benevole-relances",
            password="mot-de-passe",
        )
        ProfilUtilisateur.objects.create(
            user=benevole,
            est_benevole=True,
            date_fin_habilitation=timezone.localdate() + timedelta(days=7),
        )
        self.client.force_login(benevole)

        self.assertEqual(self.client.get(self.dashboard_url).status_code, 403)

    def test_personnel_peut_acceder_au_dashboard(self):
        self.client.force_login(self.staff)

        self.assertEqual(self.client.get(self.dashboard_url).status_code, 200)

    def test_dashboard_affiche_uniquement_les_prets_de_plus_de_28_jours(self):
        pret_retard = self.creer_pret("Document en retard", 29)
        self.creer_pret("Document encore dans les délais", 27)
        pret_restitue = self.creer_pret("Document déjà rendu", 35)
        pret_restitue.restituer()
        self.client.force_login(self.staff)

        response = self.client.get(self.dashboard_url)

        self.assertContains(response, "Document en retard")
        self.assertNotContains(response, "Document encore dans les délais")
        self.assertNotContains(response, "Document déjà rendu")
        self.assertEqual([pret.pk for pret in response.context["retards"]], [pret_retard.pk])

    def test_generation_persiste_relance_et_affiche_emprunteur(self):
        pret = self.creer_pret("Livre non restitué", 31)
        self.client.force_login(self.staff)

        response = self.client.post(
            self.impression_url,
            {"prets": [pret.pk], "canal": CanalRelance.COURRIER},
        )

        self.assertEqual(response.status_code, 200)
        relance = Relance.objects.get()
        self.assertEqual(relance.pret, pret)
        self.assertEqual(relance.emetteur, self.staff)
        self.assertEqual(relance.canal, CanalRelance.COURRIER)
        self.assertContains(response, "DURAND Camille")
        self.assertContains(response, "12 rue des Lecteurs")
        self.assertContains(response, "Livre non restitué")
        self.assertContains(response, "Avis officiel de restitution")

    def test_generation_ignore_un_pret_non_eligible(self):
        pret_recent = self.creer_pret("Livre récent", 10)
        self.client.force_login(self.staff)

        response = self.client.post(
            self.impression_url,
            {"prets": [pret_recent.pk], "canal": CanalRelance.EMAIL},
        )

        self.assertRedirects(response, self.dashboard_url)
        self.assertFalse(Relance.objects.exists())

    def test_generation_sans_selection_ne_cree_rien(self):
        self.client.force_login(self.staff)

        response = self.client.post(self.impression_url, {})

        self.assertRedirects(response, self.dashboard_url)
        self.assertFalse(Relance.objects.exists())
