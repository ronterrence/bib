# Product Requirements Document (PRD)
## Application Web de Gestion de Bibliothèque Municipale

---

## 1. Contexte, Objectifs & Choix Technologiques

### 1.1 Contexte
Ce document spécifie les exigences fonctionnelles, techniques et opérationnelles d'une application web développée sous **Django** pour gérer le cycle de vie des documents, les emprunts (sur place et à domicile), le suivi des usagers et les relances au sein d'une bibliothèque municipale.

### 1.2 Objectifs Principaux
* Automatiser l'inventaire des acquisitions et la circulation de documents hétérogènes (livres, périodiques, microfilms, CD-ROM).
* Proposer un catalogue de recherche (OPAC) ouvert aux usagers avec disponibilité des exemplaires en temps réel.
* Garantir l'intégrité métier : plafond strict de 5 prêts actifs, verrouillage des consultations sur place, dépôt de caution pour les CD-ROM, contrôle de la cotisation annuelle.
* Préserver l'historique complet sans suppression physique des fiches lecteurs et documents.
* Fournir au personnel un tableau de bord des retards (> 4 semaines) avec génération à la demande des lettres de relance.

### 1.3 Justification de la Stack : Django Templates + Bootstrap + Django Admin

| Critère | Django Fullstack (Templates + Bootstrap + Admin) | Django REST Framework + SPA (React / Vue) | Décision & Justification |
| :--- | :--- | :--- | :--- |
| **Validation Métier** | Centralisée dans l'ORM Django (`clean()`, contraintes BDD). | Dupliquée côté client (JS) et serveur (Python). | **Garantie d'intégrité absolue** : aucune incohérence possible entre l'UI et la base. |
| **Back-office Personnel** | Natif via `django.contrib.admin` personnalisable. | Développement d'une interface d'administration complète sur mesure. | **Gain de productivité massif** : inscription usagers, achats et états couverts immédiatement. |
| **Interdiction de Suppression** | Verrouillage direct (`has_delete_permission = False`, `PROTECT`). | Logique d'interdiction à coder et sécuriser sur chaque endpoint d'API. | **Conformité stricte** à la consigne : *« On ne pourra jamais retirer une fiche »*. |
| **Complexité Technique** | Dépôt unique, cycle de rendu HTML direct, zéro dépendance JS lourde. | Deux dépôts, gestion CORS, builds Node.js, synchronisation d'état client. | **Architecture sobre**, robuste et maintenable. |

---

## 2. Rôles, Permissions & Modèle de Sécurité (RBAC)

L'application segmente les accès en trois profils d'utilisateurs :

1. **Usager (Accès Public / Bornes libres)** :
   * Consultation du catalogue sans authentification requise.
   * Filtres multi-critères : type de document, auteur, cote, titre, date.
   * Consultation de l'état d'un exemplaire en temps réel (`Disponible`, `En prêt`, `En consultation`, `Hors service`).
2. **Bénévole (Compte temporaire à expiration programmée)** :
   * Authentification requise.
   * Accès au guichet de circulation : enregistrement des prêts à domicile et consultations sur place, saisie des cautions CD-ROM, clôture des restitutions.
   * Accès révoqué automatiquement dès que la date limite d'habilitation est dépassée.
3. **Personnel / Bibliothécaire** :
   * Accès complet à l'administration Django et aux fonctions de circulation.
   * Inscription des adhérents et encaissement des cotisations annuelles.
   * Enregistrement des achats et génération automatique de la cote unique.
   * Déclaration des documents perdus ou volés (mise hors service logique).
   * Consultation du dossier complet d'un adhérent (emprunts passés et en cours).
   * Déclenchement et édition des lettres de relance pour les retards supérieurs à 28 jours.

---

## 3. Schéma Relationnel / MCD (Modèle de Données)

```mermaid
classDiagram
    direction TB

    class StatutDocument {
        <<enumeration>>
        DISPONIBLE
        EN_PRET
        EN_CONSULTATION
        PERDU
        VOLE
        HORS_SERVICE
    }

    class TypePret {
        <<enumeration>>
        DOMICILE
        SUR_PLACE
    }

    class Document {
        +int cote PK
        +string titre
        +StatutDocument statut
        +date date_acquisition
        +bool est_hors_service
        +mettre_hors_service(motif)
    }

    class Livre {
        +string auteur
        +bool consultable_uniquement_sur_place
    }

    class Journal {
        +date date_parution
    }

    class CdRom {
        +string auteur_ou_editeur
        +string thematique
        +decimal caution_montant_requis
    }

    class Microfilm {
        +int document_associe_id FK
    }

    class Adherent {
        +int numero_lecteur PK
        +string nom
        +string prenom
        +string adresse
        +string email
        +string telephone
        +bool cotisation_a_jour
        +bool est_actif
        +nb_emprunts_en_cours() int
        +peut_emprunter() bool
    }

    class Pret {
        +int id PK
        +TypePret type_pret
        +datetime date_emprunt
        +datetime date_echeance
        +datetime date_restitution
        +decimal montant_caution
        +bool caution_restituee
        +int poste_ecran_numero
        +est_en_retard() bool
        +restituer()
    }

    class Relance {
        +int id PK
        +datetime date_emission
        +string canal
        +generer_lettre()
    }

    class EcranLecture {
        +int numero PK
        +bool est_libre
    }

    %% Héritage des documents
    Document <|-- Livre
    Document <|-- Journal
    Document <|-- CdRom
    Document <|-- Microfilm

    %% Relations
    Document "1" <-- "0..*" Microfilm : reference (livre ou journal)
    Adherent "1" --> "0..5" Pret : effectue
    Document "1" <-- "0..*" Pret : concerne
    Pret "1" <-- "0..*" Relance : declenche
    EcranLecture "0..1" <-- "0..1" Pret : alloue si microfilm