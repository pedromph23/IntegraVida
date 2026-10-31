from django.db import migrations


SERVICIOS = [
    # codigo, nombre, tipo
    ("emergencia", "Emergencia", "SERVICIO"),
    ("hospitalizacion", "Hospitalización", "SERVICIO"),
    ("uci", "Unidad de Cuidados Intensivos", "SERVICIO"),
    ("quirofano", "Quirófano", "SERVICIO"),
    ("laboratorio", "Laboratorio clínico", "SERVICIO"),
    ("imagenologia", "Imagenología", "SERVICIO"),
    ("farmacia", "Farmacia", "SERVICIO"),
    ("pediatria", "Pediatría", "ESPECIALIDAD"),
    ("ginecologia", "Ginecología y Obstetricia", "ESPECIALIDAD"),
    ("cardiologia", "Cardiología", "ESPECIALIDAD"),
    ("traumatologia", "Traumatología", "ESPECIALIDAD"),
    ("medicina_interna", "Medicina Interna", "ESPECIALIDAD"),
    ("cirugia_general", "Cirugía General", "ESPECIALIDAD"),
    ("oftalmologia", "Oftalmología", "ESPECIALIDAD"),
    ("nefrologia", "Nefrología", "ESPECIALIDAD"),
]


def crear_servicios(apps, schema_editor):
    Servicio = apps.get_model("hospitales", "Servicio")
    for codigo, nombre, tipo in SERVICIOS:
        Servicio.objects.get_or_create(
            codigo=codigo,
            defaults={"nombre": nombre, "tipo": tipo, "activo": True},
        )


class Migration(migrations.Migration):

    dependencies = [
        ("hospitales", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(crear_servicios, migrations.RunPython.noop),
    ]
