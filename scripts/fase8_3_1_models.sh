#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

cat >> apps/inventario/models.py << 'EOF'


class Transferencia(models.Model):
    """Transferencia de stock entre dos almacenes.

    Máquina de estados: BORRADOR -> APROBADA -> EN_TRANSITO -> RECIBIDA.
    Cancelable en BORRADOR/APROBADA sin movimientos; en EN_TRANSITO
    con restauración al origen.
    """
    class Prioridad(models.TextChoices):
        BAJA = "BAJA", "Baja"
        MEDIA = "MEDIA", "Media"
        ALTA = "ALTA", "Alta"
        URGENTE = "URGENTE", "Urgente"

    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        APROBADA = "APROBADA", "Aprobada"
        RECHAZADA = "RECHAZADA", "Rechazada"
        EN_TRANSITO = "EN_TRANSITO", "En tránsito"
        RECIBIDA = "RECIBIDA", "Recibida"
        CANCELADA = "CANCELADA", "Cancelada"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo = models.SlugField(max_length=80, unique=True)
    almacen_origen = models.ForeignKey(
        Almacen, on_delete=models.PROTECT,
        related_name="transferencias_emitidas",
    )
    almacen_destino = models.ForeignKey(
        Almacen, on_delete=models.PROTECT,
        related_name="transferencias_recibidas",
    )
    prioridad = models.CharField(
        max_length=10, choices=Prioridad.choices,
        default=Prioridad.MEDIA, db_index=True,
    )
    estado = models.CharField(
        max_length=15, choices=Estado.choices,
        default=Estado.BORRADOR, db_index=True,
    )
    motivo = models.TextField()
    solicitada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="transferencias_solicitadas",
    )
    aprobada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        null=True, blank=True, related_name="transferencias_aprobadas",
    )
    despachada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        null=True, blank=True, related_name="transferencias_despachadas",
    )
    recibida_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        null=True, blank=True, related_name="transferencias_recibidas_por",
    )
    solicitada_en = models.DateTimeField(default=timezone.now, db_index=True)
    aprobada_en = models.DateTimeField(null=True, blank=True)
    despachada_en = models.DateTimeField(null=True, blank=True)
    recibida_en = models.DateTimeField(null=True, blank=True)
    notas = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-solicitada_en"]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(
                    almacen_origen=models.F("almacen_destino")
                ),
                name="transferencia_origen_distinto_destino",
            ),
        ]
        indexes = [
            models.Index(fields=["estado", "-solicitada_en"]),
            models.Index(fields=["almacen_origen", "estado"]),
            models.Index(fields=["almacen_destino", "estado"]),
        ]
        verbose_name = "transferencia"
        verbose_name_plural = "transferencias"

    def __str__(self):
        return (
            f"{self.codigo}: {self.almacen_origen.codigo} -> "
            f"{self.almacen_destino.codigo} ({self.get_estado_display()})"
        )


class DetalleTransferencia(models.Model):
    """Línea de una transferencia: un lote específico con cantidad."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transferencia = models.ForeignKey(
        Transferencia, on_delete=models.PROTECT, related_name="detalles"
    )
    insumo = models.ForeignKey(
        Insumo, on_delete=models.PROTECT,
        related_name="detalles_transferencia",
    )
    lote_origen = models.ForeignKey(
        Lote, on_delete=models.PROTECT,
        related_name="detalles_transferencia",
    )
    cantidad = models.DecimalField(max_digits=12, decimal_places=3)
    cantidad_despachada = models.DecimalField(
        max_digits=12, decimal_places=3, default=0
    )
    cantidad_recibida = models.DecimalField(
        max_digits=12, decimal_places=3, default=0
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cantidad__gt=0),
                name="detalle_transferencia_cantidad_positiva",
            ),
        ]
        verbose_name = "detalle de transferencia"
        verbose_name_plural = "detalles de transferencia"

    def __str__(self):
        return (
            f"{self.transferencia.codigo}: "
            f"{self.insumo.codigo}/{self.lote_origen.codigo} x {self.cantidad}"
        )

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.lote_origen_id and self.insumo_id:
            if self.lote_origen.insumo_id != self.insumo_id:
                raise ValidationError(
                    {"insumo": "El insumo no coincide con el del lote."}
                )


class TransicionTransferencia(models.Model):
    """Historial inmutable de transiciones de estado de una transferencia."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transferencia = models.ForeignKey(
        Transferencia, on_delete=models.PROTECT, related_name="transiciones"
    )
    estado_anterior = models.CharField(max_length=15, blank=True)
    estado_nuevo = models.CharField(max_length=15)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="transiciones_transferencia",
    )
    motivo = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-creado_en"]
        indexes = [models.Index(fields=["transferencia", "-creado_en"])]
        verbose_name = "transición de transferencia"
        verbose_name_plural = "transiciones de transferencia"

    def __str__(self):
        return (
            f"{self.transferencia_id}: "
            f"{self.estado_anterior or 'INICIO'} -> {self.estado_nuevo}"
        )
EOF

echo "OK: Transferencia + Detalle + Transicion añadidos"
