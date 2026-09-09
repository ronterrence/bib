from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .models import CdRom, Journal, Livre, MotifHorsService, StatutDocument


class CatalogueViewTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.livre = Livre.objects.create(
            titre="Les Misérables",
            auteur="Victor Hugo",
        )
        cls.journal = Journal.objects.create(
            titre="Le Journal municipal",
            date_parution=date(2026, 9, 1),
        )
        cls.cdrom = CdRom.objects.create(
            titre="Histoire de Paris",
            auteur_ou_editeur="Archives municipales",
            thematique="Histoire",
        )

    def test_catalogue_est_monte_a_la_racine_et_sous_catalogue(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get(reverse("catalogue:liste")).status_code, 200)

    def test_recherche_multicritere(self):
        response = self.client.get(
            reverse("catalogue:liste"),
            {"titre": "misér", "auteur": "hugo", "cote": self.livre.cote},
        )

        self.assertContains(response, "Les Misérables")
        self.assertNotContains(response, "Histoire de Paris")

    def test_filtre_par_type(self):
        response = self.client.get(reverse("catalogue:liste"), {"type": "journaux"})

        self.assertContains(response, "Le Journal municipal")
        self.assertNotContains(response, "Les Misérables")

    def test_document_disponible_affiche_le_badge_et_la_localisation(self):
        response = self.client.get(reverse("catalogue:liste"))

        self.assertContains(response, "Disponible en rayon")
        self.assertContains(response, "En rayon")
        self.assertContains(response, "Au guichet")

    def test_mise_hors_service_conserve_le_motif(self):
        self.livre.mettre_hors_service(MotifHorsService.PERDU)
        self.livre.refresh_from_db()

        self.assertEqual(self.livre.statut, StatutDocument.HORS_SERVICE)
        self.assertTrue(self.livre.est_hors_service)
        self.assertEqual(self.livre.motif_hors_service, MotifHorsService.PERDU)
        with self.assertRaises(ValidationError):
            self.journal.mettre_hors_service("INCONNU")

    def test_document_hors_service_affiche_le_badge_indisponible(self):
        self.livre.statut = StatutDocument.HORS_SERVICE
        self.livre.est_hors_service = True
        self.livre.save(update_fields=["statut", "est_hors_service"])

        response = self.client.get(reverse("catalogue:liste"))

        self.assertContains(response, "Indisponible (Hors service)")

    def test_pagination_limite_la_page_a_quinze_documents(self):
        for index in range(16):
            Livre.objects.create(titre=f"Titre {index:02d}", auteur="Auteur")

        response = self.client.get(reverse("catalogue:liste"), {"tri": "cote"})

        self.assertEqual(len(response.context["page_obj"].object_list), 15)
        self.assertTrue(response.context["page_obj"].has_next())
