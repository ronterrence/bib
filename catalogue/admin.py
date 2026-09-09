from django.contrib import admin

from .models import (
    CdRom,
    Journal,
    Livre,
    Microfilm,
    MotifHorsService,
    StatutDocument,
)


class ImmutableModelAdmin(admin.ModelAdmin):
    readonly_fields = ("cote", "date_acquisition")
    actions = ("marquer_hors_service", "marquer_perdu", "marquer_vole")

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description="Marquer les documents sélectionnés hors service")
    def marquer_hors_service(self, request, queryset):
        updated = queryset.update(
            statut=StatutDocument.HORS_SERVICE,
            est_hors_service=True,
            motif_hors_service=MotifHorsService.AUTRE,
        )
        self.message_user(
            request,
            f"{updated} document(s) marqué(s) hors service.",
        )

    @admin.action(description="Marquer les documents sélectionnés comme perdus")
    def marquer_perdu(self, request, queryset):
        updated = queryset.update(
            statut=StatutDocument.HORS_SERVICE,
            est_hors_service=True,
            motif_hors_service=MotifHorsService.PERDU,
        )
        self.message_user(request, f"{updated} document(s) marqué(s) perdu(s).")

    @admin.action(description="Marquer les documents sélectionnés comme volés")
    def marquer_vole(self, request, queryset):
        updated = queryset.update(
            statut=StatutDocument.HORS_SERVICE,
            est_hors_service=True,
            motif_hors_service=MotifHorsService.VOLE,
        )
        self.message_user(request, f"{updated} document(s) marqué(s) volé(s).")


@admin.register(Livre)
class LivreAdmin(ImmutableModelAdmin):
    list_display = (
        "cote",
        "titre",
        "auteur",
        "statut",
        "consultable_uniquement_sur_place",
        "date_acquisition",
    )
    list_filter = (
        "statut",
        "consultable_uniquement_sur_place",
        "est_hors_service",
        "date_acquisition",
    )
    search_fields = ("=cote", "titre", "auteur")


@admin.register(Journal)
class JournalAdmin(ImmutableModelAdmin):
    list_display = (
        "cote",
        "titre",
        "date_parution",
        "statut",
        "date_acquisition",
    )
    list_filter = (
        "statut",
        "est_hors_service",
        "date_parution",
        "date_acquisition",
    )
    search_fields = ("=cote", "titre")


@admin.register(CdRom)
class CdRomAdmin(ImmutableModelAdmin):
    list_display = (
        "cote",
        "titre",
        "auteur_ou_editeur",
        "thematique",
        "caution_montant_requis",
        "statut",
        "date_acquisition",
    )
    list_filter = (
        "statut",
        "thematique",
        "est_hors_service",
        "date_acquisition",
    )
    search_fields = ("=cote", "titre", "auteur_ou_editeur", "thematique")


@admin.register(Microfilm)
class MicrofilmAdmin(ImmutableModelAdmin):
    list_display = (
        "cote",
        "titre",
        "document_associe",
        "statut",
        "date_acquisition",
    )
    list_filter = ("statut", "est_hors_service", "date_acquisition")
    search_fields = ("=cote", "titre", "document_associe__titre")
    list_select_related = ("document_associe",)
