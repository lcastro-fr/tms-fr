import django.db.models.manager
from django.db import migrations, models

from catalog.paises import PAISES


def sembrar_paises(apps, schema_editor):
    Pais = apps.get_model("catalog", "Pais")
    Pais.objects.bulk_create(
        [Pais(codigo=codigo, nombre=nombre) for codigo, nombre in PAISES],
        ignore_conflicts=True,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0003_ubicacion_validada"),
    ]

    operations = [
        migrations.CreateModel(
            name="Pais",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("active", models.BooleanField(default=True)),
                ("codigo", models.CharField(max_length=2, primary_key=True, serialize=False)),
                ("nombre", models.CharField(max_length=80)),
            ],
            options={
                "verbose_name": "país",
                "verbose_name_plural": "países",
                "db_table": "pais",
                "abstract": False,
                "base_manager_name": "all_objects",
                "constraints": [
                    models.UniqueConstraint(
                        condition=models.Q(("active", True)),
                        fields=("nombre",),
                        name="uq_pais_nombre",
                    )
                ],
            },
            managers=[
                ("objects", django.db.models.manager.Manager()),
                ("all_objects", django.db.models.manager.Manager()),
            ],
        ),
        migrations.RunPython(sembrar_paises, migrations.RunPython.noop),
    ]
