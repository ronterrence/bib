from django.contrib import admin

from .models import Adherent, ProfilUtilisateur


@admin.register(Adherent)
class AdherentAdmin(admin.ModelAdmin):
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


@admin.register(ProfilUtilisateur)
class ProfilUtilisateurAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "est_benevole",
        "date_fin_habilitation",
        "acces_circulation",
    )
    list_filter = ("est_benevole", "date_fin_habilitation")
    search_fields = ("user__username", "user__first_name", "user__last_name")
    autocomplete_fields = ("user",)

    @admin.display(boolean=True, description="Accès circulation")
    def acces_circulation(self, obj):
        return obj.a_acces_circulation
