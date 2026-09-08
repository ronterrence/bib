from datetime import date, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone

from adherents.models import Adherent
from catalogue.models import Livre, Journal, CdRom, Microfilm, StatutDocument
from circulation.models import Pret, TypePret, EcranLecture


class Command(BaseCommand):
    help = "Initialise la base avec 10 adhérents, 20 documents hétérogènes et des scénarios de prêt."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Démarrage du peuplement de la base de données..."))

        # ---------------------------------------------------------------------
        # 1. Écrans de lecture pour microfilms
        # ---------------------------------------------------------------------
        for num in range(1, 4):
            EcranLecture.objects.get_or_create(numero=num, defaults={"est_libre": True})
        self.stdout.write("-> Écrans de consultation créés.")

        # ---------------------------------------------------------------------
        # 2. Création de 10 Adhérents
        # ---------------------------------------------------------------------
        donnees_adherents = [
            ("Lefebvre", "Thomas", "12 Rue de la Paix", "thomas.l@mail.fr", "0611223344", True),
            ("Moreau", "Sophie", "45 Avenue Victor Hugo", "sophie.m@mail.fr", "0622334455", True),
            ("Bernard", "Lucas", "8 Boulevard Gambetta", "lucas.b@mail.fr", "0633445566", True),
            ("Dubois", "Camille", "17 Rue des Lilas", "camille.d@mail.fr", "0644556677", True),
            ("Laurent", "Antoine", "3 Place Bellecour", "antoine.l@mail.fr", "0655667788", True),
            ("Simon", "Élodie", "29 Rue Nationale", "elodie.s@mail.fr", "0666778899", True),
            ("Michel", "Hugo", "14 Rue du Moulin", "hugo.m@mail.fr", "0677889900", True),
            ("Garcia", "Emma", "56 Allée des Roses", "emma.g@mail.fr", "0688990011", True),
            ("Roux", "Nicolas", "9 Rue de la Gare", "nicolas.r@mail.fr", "0699001122", False),  # Cotisation non réglée
            ("Vincent", "Chloé", "21 Boulevard Jean Jaurès", "chloe.v@mail.fr", "0600112233", True),
        ]

        adherents = []
        for nom, prenom, adr, email, tel, cotis in donnees_adherents:
            adherent, created = Adherent.objects.get_or_create(
                nom=nom,
                prenom=prenom,
                defaults={
                    "adresse": adr,
                    "email": email,
                    "telephone": tel,
                    "cotisation_a_jour": cotis,
                    "est_actif": True,
                },
            )
            adherents.append(adherent)
        self.stdout.write(f"-> {len(adherents)} adhérents enregistrés.")

        # ---------------------------------------------------------------------
        # 3. Création de 20 Documents variés
        # ---------------------------------------------------------------------
        # A. Livres ordinaires (empruntables à domicile)
        livres_standards = [
            ("Les Misérables", "Victor Hugo"),
            ("Le Petit Prince", "Antoine de Saint-Exupéry"),
            ("1984", "George Orwell"),
            ("L'Étranger", "Albert Camus"),
            ("Madame Bovary", "Gustave Flaubert"),
            ("Germinal", "Émile Zola"),
        ]
        docs_livres = []
        for titre, auteur in livres_standards:
            livre, _ = Livre.objects.get_or_create(
                titre=titre,
                defaults={
                    "auteur": auteur,
                    "consultable_uniquement_sur_place": False,
                    "statut": StatutDocument.DISPONIBLE,
                },
            )
            docs_livres.append(livre)

        # B. Livres spéciaux (consultables sur place uniquement)
        livres_speciaux = [
            ("Manuscrit des Chroniques Médiévales", "Anonyme"),
            ("Atlas Géographique Ancien de 1680", "Mercator"),
        ]
        for titre, auteur in livres_speciaux:
            Livre.objects.get_or_create(
                titre=titre,
                defaults={
                    "auteur": auteur,
                    "consultable_uniquement_sur_place": True,
                    "statut": StatutDocument.DISPONIBLE,
                },
            )

        # C. Journaux / Périodiques (consultables sur place uniquement)
        journaux = [
            ("Le Figaro", date(2026, 8, 1)),
            ("Le Monde", date(2026, 8, 15)),
            ("Libération", date(2026, 8, 20)),
            ("Courrier International", date(2026, 8, 25)),
            ("L'Équipe", date(2026, 9, 1)),
        ]
        docs_journaux = []
        for titre, date_pub in journaux:
            journal, _ = Journal.objects.get_or_create(
                titre=titre,
                defaults={
                    "date_parution": date_pub,
                    "statut": StatutDocument.DISPONIBLE,
                },
            )
            docs_journaux.append(journal)

        # D. CD-ROM Documentaires (prêt avec caution)
        cdroms = [
            ("Encyclopédie Universalis Édition 2026", "Universalis", "Encyclopédie générale", Decimal("20.00")),
            ("Visite Interactive du Musée d'Orsay", "RMN", "Beaux-Arts & Histoire", Decimal("15.00")),
            ("Atlas Interactif du Système Solaire", "NASA / ESA", "Astronomie", Decimal("15.00")),
            ("Dictionnaire Multimédia de la Musique", "Larousse", "Musique", Decimal("10.00")),
        ]
        docs_cd = []
        for titre, editeur, theme, caution in cdroms:
            cd, _ = CdRom.objects.get_or_create(
                titre=titre,
                defaults={
                    "auteur_ou_editeur": editeur,
                    "thematique": theme,
                    "caution_montant_requis": caution,
                    "statut": StatutDocument.DISPONIBLE,
                },
            )
            docs_cd.append(cd)

        # E. Microfilms (liés à des ouvrages existants)
        microfilms = [
            ("Microfilm - Archives Le Figaro Août 2026", docs_journaux[0]),
            ("Microfilm - Édition Originale Les Misérables", docs_livres[0]),
            ("Microfilm - Archives Presse Régionale 1914-1918", docs_journaux[1]),
        ]
        for titre, ref_doc in microfilms:
            Microfilm.objects.get_or_create(
                titre=titre,
                defaults={
                    "document_associe": ref_doc,
                    "statut": StatutDocument.DISPONIBLE,
                },
            )

        self.stdout.write("-> 20 documents de divers types créés ou vérifiés.")

        # ---------------------------------------------------------------------
        # 4. Création des 3 Prêts en retard (> 28 jours)
        # ---------------------------------------------------------------------
        # Retards affectés aux trois premiers adhérents sur les trois premiers livres
        retards_config = [
            (adherents[0], docs_livres[0], 35),  # 35 jours de retard
            (adherents[1], docs_livres[1], 42),  # 42 jours de retard
            (adherents[2], docs_livres[2], 29),  # 29 jours de retard (> 28 jours)
        ]

        maintenant = timezone.now()

        for adherent, livre, jours in retards_config:
            pret, cree = Pret.objects.get_or_create(
                adherent=adherent,
                document=livre,
                date_restitution__isnull=True,
                defaults={
                    "type_pret": TypePret.DOMICILE,
                    "date_emprunt": maintenant - timedelta(days=jours),
                    "montant_caution": Decimal("0.00"),
                },
            )
            if not cree:
                # Force la date antérieure si le prêt existait déjà
                Pret.objects.filter(pk=pret.pk).update(date_emprunt=maintenant - timedelta(days=jours))

            livre.statut = StatutDocument.EN_PRET
            livre.save(update_fields=["statut"])

        self.stdout.write("-> 3 prêts en retard (> 28 jours) configurés avec succès.")

        # ---------------------------------------------------------------------
        # 5. Prêt de CD-ROM en cours (avec caution consécutive)
        # ---------------------------------------------------------------------
        cd_pret = docs_cd[0]
        Pret.objects.get_or_create(
            adherent=adherents[3],
            document=cd_pret,
            date_restitution__isnull=True,
            defaults={
                "type_pret": TypePret.DOMICILE,
                "date_emprunt": maintenant - timedelta(days=5),
                "montant_caution": cd_pret.caution_montant_requis,
                "caution_restituee": False,
            },
        )
        cd_pret.statut = StatutDocument.EN_PRET
        cd_pret.save(update_fields=["statut"])
        self.stdout.write("-> 1 prêt actif de CD-ROM avec caution consigné.")

        self.stdout.write(self.style.SUCCESS("Base de données initialisée avec succès !"))