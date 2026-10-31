import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.pacientes.fields import (
    EncryptedCharField, EncryptedEmailField, EncryptedTextField,
)


class Paciente(models.Model):
    class SexoBiologico(models.TextChoices):
        FEMENINO = "F", "Femenino"
        MASCULINO = "M", "Masculino"
        INTERSEX = "I", "Intersexual"
        NO_ESPECIFICADO = "N", "No especificado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Identificación (cedula_hash calculado en services.py)
    cedula = EncryptedCharField(max_length=500, blank=True, default="")
    cedula_hash = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="HMAC-SHA256 de la cédula normalizada. Calculado automáticamente.",
    )

    # Datos personales
    nombres = EncryptedCharField(max_length=500)
    apellidos = EncryptedCharField(max_length=500)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    sexo_biologico = models.CharField(
        max_length=1,
        choices=SexoBiologico.choices,
        default=SexoBiologico.NO_ESPECIFICADO,
    )

    # Contacto (opcional, puede existir sin paciente identificar)
    telefono = EncryptedCharField(max_length=500, blank=True)
    email = EncryptedEmailField(blank=True, max_length=500)

    # Cuenta vinculada (opcional, para futura consulta del titular)
    cuenta_vinculada = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pacientes_vinculados",
    )

    notas_internas = EncryptedTextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True, db_index=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-creado_en"]
        indexes = [
            models.Index(fields=["apellidos", "nombres"]),
            models.Index(fields=["-creado_en"]),
        ]
        verbose_name = "paciente"
        verbose_name_plural = "pacientes"

    def __str__(self):
        return f"{self.apellidos}, {self.nombres}"

    @property
    def nombre_completo(self):
        return f"{self.nombres} {self.apellidos}".strip()

    @property
    def edad(self):
        if not self.fecha_nacimiento:
            return None
        hoy = timezone.localdate()
        return (
            hoy.year
            - self.fecha_nacimiento.year
            - (
                (hoy.month, hoy.day)
                < (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
            )
        )


class ContactoEmergencia(models.Model):
    class Parentesco(models.TextChoices):
        PADRE = "PADRE", "Padre"
        MADRE = "MADRE", "Madre"
        HIJO = "HIJO", "Hijo/a"
        CONYUGE = "CONYUGE", "Cónyuge / Pareja"
        HERMANO = "HERMANO", "Hermano/a"
        TUTOR = "TUTOR", "Tutor legal"
        AMIGO = "AMIGO", "Amigo/a"
        OTRO = "OTRO", "Otro"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    paciente = models.ForeignKey(
        Paciente, on_delete=models.PROTECT, related_name="contactos"
    )
    nombre = models.CharField(max_length=200)
    parentesco = models.CharField(max_length=20, choices=Parentesco.choices)
    telefono = models.CharField(max_length=30)
    es_principal = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-es_principal", "-creado_en"]
        constraints = [
            models.UniqueConstraint(
                fields=["paciente"],
                condition=models.Q(es_principal=True),
                name="un_contacto_principal_por_paciente",
            ),
        ]
        indexes = [
            models.Index(fields=["paciente", "-es_principal"]),
        ]
        verbose_name = "contacto de emergencia"
        verbose_name_plural = "contactos de emergencia"

    def __str__(self):
        return f"{self.nombre} ({self.get_parentesco_display()})"


class Episodio(models.Model):
    class Estado(models.TextChoices):
        ABIERTO = "ABIERTO", "Abierto"
        EN_ATENCION = "EN_ATENCION", "En atención"
        DERIVADO = "DERIVADO", "Derivado"
        CERRADO = "CERRADO", "Cerrado"
        FALLECIDO = "FALLECIDO", "Fallecido"
        ABANDONO = "ABANDONO", "Abandono"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    paciente = models.ForeignKey(
        Paciente, on_delete=models.PROTECT, related_name="episodios"
    )
    hospital = models.ForeignKey(
        "hospitales.Hospital",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="episodios",
    )
    refugio = models.ForeignKey(
        "refugios.Refugio",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="episodios",
    )
    motivo_consulta = models.TextField()
    estado = models.CharField(
        max_length=15,
        choices=Estado.choices,
        default=Estado.ABIERTO,
        db_index=True,
    )
    fecha_ingreso = models.DateTimeField(default=timezone.now, db_index=True)
    fecha_egreso = models.DateTimeField(null=True, blank=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="episodios_registrados",
    )
    notas_internas = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_ingreso"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(hospital_id__isnull=False, refugio_id__isnull=True)
                    | models.Q(hospital_id__isnull=True, refugio_id__isnull=False)
                ),
                name="episodio_uno_y_solo_un_centro",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(fecha_egreso__isnull=True)
                    | models.Q(fecha_egreso__gte=models.F("fecha_ingreso"))
                ),
                name="episodio_egreso_posterior_a_ingreso",
            ),
        ]
        indexes = [
            models.Index(fields=["paciente", "-fecha_ingreso"]),
            models.Index(fields=["hospital", "estado"]),
            models.Index(fields=["refugio", "estado"]),
        ]
        verbose_name = "episodio"
        verbose_name_plural = "episodios"

    def __str__(self):
        centro = self.hospital or self.refugio
        return f"{self.paciente} — {centro} ({self.get_estado_display()})"
