"""Tests de validadores reutilizables (frontend/validators.py)."""
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from frontend.validators import (
    validar_cedula, validar_codigo, validar_edad_aproximada,
    validar_estatura_cm, validar_nombre_persona, validar_peso_kg,
    validar_telefono, validar_texto_libre,
)


class TelefonoTests(SimpleTestCase):
    def test_telefono_ve_valido(self):
        for t in ["0414-1234567", "+58 414 1234567", "(0212) 555-4433", "04141234567"]:
            validar_telefono(t)  # no debe lanzar

    def test_telefono_muy_corto(self):
        with self.assertRaises(ValidationError):
            validar_telefono("123")

    def test_telefono_muy_largo(self):
        with self.assertRaises(ValidationError):
            validar_telefono("+" + "1" * 16)

    def test_telefono_con_letras(self):
        with self.assertRaises(ValidationError):
            validar_telefono("0414-ABC-1234")

    def test_telefono_vacio_ok(self):
        validar_telefono("")  # opcional, no lanza


class CedulaTests(SimpleTestCase):
    def test_cedula_ve_valida(self):
        for c in ["V-12345678", "E-1234567", "12345678", "v-12345678", "J-123456789"]:
            validar_cedula(c)

    def test_cedula_invalida(self):
        for c in ["V-123", "ABC-12345678", "V12345678", "12345"]:
            with self.assertRaises(ValidationError):
                validar_cedula(c)

    def test_cedula_vacia_ok(self):
        validar_cedula("")


class NombreTests(SimpleTestCase):
    def test_nombres_validos(self):
        for n in ["María José", "O'Connor", "Ana-María", "Juan Carlos Pérez"]:
            validar_nombre_persona(n)

    def test_nombre_con_numeros(self):
        with self.assertRaises(ValidationError):
            validar_nombre_persona("Juan123")

    def test_nombre_muy_corto(self):
        with self.assertRaises(ValidationError):
            validar_nombre_persona("J")

    def test_nombre_con_espacios_dobles(self):
        with self.assertRaises(ValidationError):
            validar_nombre_persona("Juan  Carlos")


class CodigoTests(SimpleTestCase):
    def test_codigos_validos(self):
        for c in ["hosp-central", "ins-001", "org_2026", "abc"]:
            validar_codigo(c)

    def test_codigo_con_espacios(self):
        with self.assertRaises(ValidationError):
            validar_codigo("hosp central")

    def test_codigo_con_caracteres_especiales(self):
        with self.assertRaises(ValidationError):
            validar_codigo("hosp@central")

    def test_codigo_muy_corto(self):
        with self.assertRaises(ValidationError):
            validar_codigo("a")


class EstaturaPesoTests(SimpleTestCase):
    def test_estatura_valida(self):
        for e in [30, 170, 250]:
            validar_estatura_cm(e)

    def test_estatura_invalida(self):
        with self.assertRaises(ValidationError):
            validar_estatura_cm(10)
        with self.assertRaises(ValidationError):
            validar_estatura_cm(300)

    def test_peso_valido(self):
        for p in [0.5, 70, 500]:
            validar_peso_kg(p)

    def test_peso_invalido(self):
        with self.assertRaises(ValidationError):
            validar_peso_kg(0)
        with self.assertRaises(ValidationError):
            validar_peso_kg(1000)


class EdadAproximadaTests(SimpleTestCase):
    def test_edades_validas(self):
        for e in ["30-40", "menor de 18", "adulto mayor", "45"]:
            validar_edad_aproximada(e)

    def test_edad_con_simbolos_raros(self):
        with self.assertRaises(ValidationError):
            validar_edad_aproximada("30-40<script>")


class TextoLibreTests(SimpleTestCase):
    def test_texto_valido(self):
        validar_texto_libre("Motivo de consulta válido", min_len=5)

    def test_texto_muy_corto(self):
        with self.assertRaises(ValidationError):
            validar_texto_libre("Hola", min_len=10)
