from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalogue", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="motif_hors_service",
            field=models.CharField(
                blank=True,
                choices=[
                    ("PERDU", "Perdu"),
                    ("VOLE", "Volé"),
                    ("AUTRE", "Autre"),
                ],
                max_length=20,
                null=True,
            ),
        ),
    ]
