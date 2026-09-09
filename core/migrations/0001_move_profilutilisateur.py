import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def copier_profils(apps, schema_editor):
    AncienProfil = apps.get_model("adherents", "ProfilUtilisateur")
    NouveauProfil = apps.get_model("core", "ProfilUtilisateur")
    NouveauProfil.objects.bulk_create(
        NouveauProfil(
            id=profil.id,
            user_id=profil.user_id,
            est_benevole=profil.est_benevole,
            date_fin_habilitation=profil.date_fin_habilitation,
        )
        for profil in AncienProfil.objects.all().iterator()
    )


def restaurer_profils(apps, schema_editor):
    AncienProfil = apps.get_model("adherents", "ProfilUtilisateur")
    NouveauProfil = apps.get_model("core", "ProfilUtilisateur")
    AncienProfil.objects.bulk_create(
        AncienProfil(
            id=profil.id,
            user_id=profil.user_id,
            est_benevole=profil.est_benevole,
            date_fin_habilitation=profil.date_fin_habilitation,
        )
        for profil in NouveauProfil.objects.all().iterator()
    )


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("adherents", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ProfilUtilisateur",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("est_benevole", models.BooleanField(default=False)),
                (
                    "date_fin_habilitation",
                    models.DateField(blank=True, null=True),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profil",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.RunPython(copier_profils, restaurer_profils),
    ]
