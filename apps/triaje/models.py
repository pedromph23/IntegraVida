import uuid

from django.conf import settings
from django.db import models


class Triaje(models.Model):
    """
    Evaluación de triaje asociada a un Episodio.

    Sistema de clasificación: 3 niveles (ROJO/AMARILLO/VERDE) según práctica
    común en servicios de urgencia venezolanos y en el repositorio de origen
    `sistema-derivacion-hospitalaria`.

    Un episodio tiene MÚLTIPLES Triajes a lo largo del tiempo (inicial + 
    reevaluaciones). Solo uno tiene `vigente=True` en cada momento (garantizado
    por UniqueConstraint condicional).
    """

    class Clasificacion(models.TextChoices):
        ROJO = "ROJO", "Rojo — Emergencia vital, atención inmediata"
        AMARILLO = "AMARILLO", "Amarillo — Urgencia, atención prioritaria"
        VERDE = "VERDE", "Verde — No urgente, atención diferible"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    episodio = models.ForeignKey(
        "pacientes.Episodio",
        on_delete=models.PROTECT,
        related_name="triajes",
    )
    clasificacion = models.CharField(
        max_length=10, choices=Clasificacion.choices, db_index=True
    )
    signos_vitales = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Claves esperadas: temperatura (C), frecuencia_cardiaca (lpm), "
            "frecuencia_respiratoria (rpm), presion_arterial_sistolica (mmHg), "
            "presion_arterial_diastolica (mmHg), saturacion_oxigeno (%), "
            "escala_glasgow (3-15), peso_kg, talla_cm."
        ),
    )
    observaciones = models.TextField(blank=True)
    evaluado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="triajes_evaluados",
    )
    evaluado_en = models.DateTimeField(auto_now_add=True, db_index=True)

    es_reevaluacion = models.BooleanField(default=False)
    motivo_reevaluacion = models.CharField(max_length=300, blank=True)
    vigente = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["-evaluado_en"]
        constraints = [
            models.UniqueConstraint(
                fields=["episodio"],
                condition=models.Q(vigente=True),
                name="un_triaje_vigente_por_episodio",
            ),
        ]
        indexes = [
            models.Index(fields=["episodio", "-evaluado_en"]),
            models.Index(fields=["clasificacion", "-evaluado_en"]),
            models.Index(fields=["vigente", "-evaluado_en"]),
        ]
        verbose_name = "triaje"
        verbose_name_plural = "triajes"

    def __str__(self):
        return (
            f"{self.episodio_id} — {self.get_clasificacion_display()} "
            f"({'vigente' if self.vigente else 'histórico'})"
        )
