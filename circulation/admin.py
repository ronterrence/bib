from django.contrib import admin

from .models import EcranLecture, Pret


@admin.register(Pret)
class PretAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "adherent",
        "document",
        "type_pret",
        "date_emprunt",
        "en_retard",
        "date_restitution",
        "montant_caution",
        "caution_restituee",
    )
    list_filter = ("type_pret", "date_emprunt", "date_restitution", "caution_restituee")
    search_fields = (
        "=id",
        "=adherent__numero_lecteur",
        "adherent__nom",
        "adherent__prenom",
        "=document__cote",
        "document__titre",
    )
    list_select_related = ("adherent", "document", "poste_ecran")
    date_hierarchy = "date_emprunt"

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(boolean=True, description="En retard")
    def en_retard(self, obj):
        return obj.est_en_retard()


@admin.register(EcranLecture)
class EcranLectureAdmin(admin.ModelAdmin):
    list_display = ("numero", "est_libre")
    list_filter = ("est_libre",)
    search_fields = ("=numero",)
