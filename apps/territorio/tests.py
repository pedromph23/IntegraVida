from django.test import TestCase

from apps.territorio.models import EntidadFederal, Municipio, Parroquia


class TerritorioModelTests(TestCase):
    def test_jerarquia_territorial(self):
        entidad = EntidadFederal.objects.create(
            nombre="Entidad de prueba",
            codigo="TEST-ENT",
            tipo=EntidadFederal.Tipo.ESTADO,
        )
        municipio = Municipio.objects.create(
            entidad_federal=entidad,
            nombre="Municipio de prueba",
            codigo="TEST-MUN",
        )
        parroquia = Parroquia.objects.create(
            municipio=municipio,
            nombre="Parroquia de prueba",
            codigo="TEST-PAR",
        )

        self.assertEqual(parroquia.municipio, municipio)
        self.assertEqual(municipio.entidad_federal, entidad)
        self.assertEqual(entidad.municipios.count(), 1)
        self.assertEqual(municipio.parroquias.count(), 1)
