from django.contrib import admin

from circulation.models import Pret

from .models import Adherent


class PretInline(admin.TabularInline):
    model = Pret
    fields = (
        "document",
        "type_pret",
        "date_emprunt",
        "date_restitution",
        "montant_caution",
        "caution_restituee",
        "poste_ecran",
    )
    readonly_fields = fields
    extra = 0
    can_delete = False
    ordering = ("-date_emprunt",)

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Adherent)
class AdherentAdmin(admin.ModelAdmin):
    inlines = (PretInline,)
    readonly_fields = ("numero_lecteur",)
    list_display = (
        "numero_lecteur",
        "nom",
        "prenom",
        "email",
        "telephone",
        "cotisation_a_jour",
        "est_actif",
        "emprunts_en_cours",
    )
    list_filter = ("cotisation_a_jour", "est_actif")
    search_fields = ("=numero_lecteur", "nom", "prenom", "email", "telephone")

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Emprunts en cours")
    def emprunts_en_cours(self, obj):
        return obj.nb_emprunts_en_cours()
