"""Tests de validación global: TODOS los ModelForm reciben validadores."""
from django import forms
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from apps.organizaciones.models import Organizacion


class ModelFormDinamicoRecibeValidadores(SimpleTestCase):
    """Cualquier ModelForm (aunque sea nuevo) debe recibir validadores."""

    def test_form_dinamico_recibe_validadores(self):
        # Form creado dinámicamente (no existe en el código)
        class FormNuevo(forms.ModelForm):
            class Meta:
                model = Organizacion
                fields = ["nombre", "codigo", "telefono_publico"]

        form = FormNuevo()

        # El campo 'nombre' debe tener el validador
        nombre_validators = form.fields["nombre"].validators
        from frontend.validators import validar_nombre_persona
        self.assertIn(validar_nombre_persona, nombre_validators)

        # 'codigo' debe tener su validador
        from frontend.validators import validar_codigo
        self.assertIn(validar_codigo, form.fields["codigo"].validators)


class ValidacionRechazaBasura(SimpleTestCase):
    """La validación debe rechazar strings sin sentido."""

    def test_nombre_basura_larga(self):
        """El string del usuario no debe pasar."""
        from frontend.validators import validar_nombre_persona
        with self.assertRaises(ValidationError):
            validar_nombre_persona(
                "jdsufuguhugHUHUIDHGH7hdufvuigWGG77GVGYGDYSGYGYFGY"
            )

    def test_nombre_sin_vocales(self):
        from frontend.validators import validar_nombre_persona
        with self.assertRaises(ValidationError):
            validar_nombre_persona("jdsfghjk")

    def test_nombre_letras_repetidas(self):
        from frontend.validators import validar_nombre_persona
        with self.assertRaises(ValidationError):
            validar_nombre_persona("wwwwwwww")

    def test_nombre_valido_pasa(self):
        from frontend.validators import validar_nombre_persona
        # No debe lanzar
        validar_nombre_persona("María José")
        validar_nombre_persona("O'Connor")
        validar_nombre_persona("Juan Carlos Pérez Rodríguez")
