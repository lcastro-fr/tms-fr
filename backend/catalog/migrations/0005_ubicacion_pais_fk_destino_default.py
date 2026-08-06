import django.db.models.deletion
from django.db import migrations, models


def texto_a_fk(apps, schema_editor):
    """El `pais` de texto libre pasa a FK. Lo que no matchea queda NULL, no se inventa."""
    Pais = apps.get_model("catalog", "Pais")
    Ubicacion = apps.get_model("catalog", "Ubicacion")

    por_clave = {}
    for codigo, nombre in Pais.objects.values_list("codigo", "nombre"):
        por_clave[codigo.upper()] = codigo
        por_clave[nombre.upper()] = codigo

    for pk, texto in Ubicacion.objects.values_list("pk", "pais"):
        codigo = por_clave.get((texto or "").strip().upper())
        if codigo is not None:
            Ubicacion.objects.filter(pk=pk).update(pais_ref_id=codigo)


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0004_pais"),
    ]

    operations = [
        migrations.AddField(
            model_name="ubicacion",
            name="pais_ref",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="ubicaciones",
                to="catalog.pais",
            ),
        ),
        migrations.RunPython(texto_a_fk, migrations.RunPython.noop),
        migrations.RemoveField(model_name="ubicacion", name="pais"),
        migrations.RenameField(model_name="ubicacion", old_name="pais_ref", new_name="pais"),
        migrations.AddField(
            model_name="ubicacion",
            name="destino_default",
            field=models.CharField(
                blank=True,
                choices=[("puerto_maritimo", "Puerto Maritimo"), ("aeropuerto", "Aeropuerto")],
                max_length=30,
                null=True,
            ),
        ),
        migrations.AddConstraint(
            model_name="ubicacion",
            constraint=models.UniqueConstraint(
                condition=models.Q(("active", True), ("destino_default__isnull", False)),
                fields=("destino_default",),
                name="uq_ubicacion_destino_default",
            ),
        ),
    ]
