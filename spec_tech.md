# Spécifications Techniques Complémentaires & Architecture UI
## Système de Gestion de Bibliothèque Municipale (Django)

---

## 1. Diagramme de Cas d'Utilisation (Use Cases - Mermaid)

```mermaid
flowchart LR
    %% Acteurs
    Usager((Usager / Public))
    Benevole((Bénévole\nAccès temporaire))
    Employe((Employé /\nBibliothécaire))

    %% Hiérarchie des rôles
    Employe --> Benevole
    Benevole --> Usager

    %% Système
    subgraph Systeme [Système de Gestion de Bibliothèque]
        UC1[Consulter le catalogue\ntitre, auteur, cote, date]
        UC2[Consulter la disponibilité\nen temps réel]

        UC3[Enregistrer un prêt à domicile\nLivre standard, CD-ROM]
        UC4[Enregistrer une consultation sur place\nJournal, Microfilm, Livre spécial, CD-ROM]
        UC5[Encaisser la caution\nObligatoire pour CD-ROM]
        UC6[Vérifier disponibilité écran\nObligatoire pour Microfilm]
        UC7[Enregistrer une restitution]
        UC8[Restituer la caution physique]

        UC9[Inscrire un adhérent\nNuméro séquentiel auto]
        UC10[Modifier une fiche lecteur\nAdresse, téléphone]
        UC11[Enregistrer l'achat d'un document\nCote séquentielle auto]
        UC12[Mettre hors service un document\nPerdu / Volé]
        UC13[Consulter le dossier d'un lecteur\nEmprunts en cours & historique]
        UC14[Déclencher l'édition des relances\nRetard > 4 semaines]
    end

    %% Connexions Usager
    Usager --> UC1
    Usager --> UC2

    %% Connexions Bénévole
    Benevole --> UC3
    Benevole --> UC4
    Benevole --> UC7

    %% Relations include
    UC3 -.->|<<include>>| UC5
    UC4 -.->|<<include si microfilm>>| UC6
    UC7 -.->|<<include si CD-ROM>>| UC8

    %% Connexions Employé
    Employe --> UC9
    Employe --> UC10
    Employe --> UC11
    Employe --> UC12
    Employe --> UC13
    Employe --> UC14