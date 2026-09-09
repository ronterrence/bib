from django.contrib import admin

from .models import ProfilUtilisateur


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
