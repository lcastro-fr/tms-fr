import django.contrib.gis.db.models.fields
from django.db import migrations

# El AlterField que genera Django emite el ALTER sin USING, y Postgres rechaza el cast implícito
# de geometry(Polygon) a geometry(MultiPolygon) en cuanto hay una fila. La vuelta es con pérdida:
# se queda con el primer polígono.
A_MULTIPOLYGON = (
    'ALTER TABLE "zona" ALTER COLUMN "geom" TYPE geometry(MultiPolygon,4326) USING ST_Multi("geom")'
)
A_POLYGON = (
    'ALTER TABLE "zona" ALTER COLUMN "geom" TYPE geometry(Polygon,4326) '
    'USING ST_GeometryN("geom", 1)'
)


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0007_division_politica"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunSQL(A_MULTIPOLYGON, A_POLYGON)],
            state_operations=[
                migrations.AlterField(
                    model_name="zona",
                    name="geom",
                    field=django.contrib.gis.db.models.fields.MultiPolygonField(srid=4326),
                ),
            ],
        ),
    ]
