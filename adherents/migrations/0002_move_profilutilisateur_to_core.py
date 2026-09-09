from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("adherents", "0001_initial"),
        ("core", "0001_move_profilutilisateur"),
    ]

    operations = [
        migrations.DeleteModel(name="ProfilUtilisateur"),
    ]
