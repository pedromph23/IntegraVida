#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

cat >> apps/inventario/models.py << 'EOF'


class Entrega(models.Model):
    """Entrega de insumos desde un almacén a un destinatario final.

    Estados: BORRADOR -> ENVIADA -> RECIBIDA / CANCELADA.
    A diferencia de Transferencia, el destino NO es un almacén con Stock:
    es un refugio/hospital/población que consume los insumos.
    """
    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        ENVIADA = "ENVIADA", "Enviada"
        RECIBIDA = "RECIBIDA", "Recibida"
        CANCELADA = "CANCELADA", "Cancelada"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo = models.SlugField(max_length=80, unique=True)
    almacen_origen = models.ForeignKey(
        Almacen, on_delete=models.PROTECT, related_name="entregas",
    )
    refugio = models.ForeignKey(
        "refugios.Refugio", on_delete=models.PROTECT,
        null=True, blank=True, related_name="entregas",
    )
    hospital = models.ForeignKey(
        "hospitales.Hospital", on_delete=models.PROTECT,
        null=True, blank=True, related_name="entregas",
    )
    destinatario_texto = models.CharField(
        max_length=300, blank=True,
        help_text="Destinatario externo no registrado (comunidad, punto)."
    )
    estado = models.CharField(
        max_length=15, choices=Estado.choices,
        default=Estado.BORRADOR, db_index=True,
    )
    motivo = models.TextField()
    solicitada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="entregas_solicitadas",
    )
    enviada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        null=True, blank=True, related_name="entregas_enviadas",
    )
    recibida_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        null=True, blank=True, related_name="entregas_recibidas",
    )
    solicitada_en = models.DateTimeField(default=timezone.now, db_index=True)
    enviada_en = models.DateTimeField(null=True, blank=True)
    recibida_en = models.DateTimeField(null=True, blank=True)
    notas = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-solicitada_en"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(destinatario_texto__gt="")
                    | models.Q(refugio__isnull=False)
                    | models.Q(hospital__isnull=False)
                ),
                name="entrega_con_destino",
            ),
            models.CheckConstraint(
                condition=~(
                    models.Q(refugio__isnull=False)
                    & models.Q(hospital__isnull=False)
                ),
                name="entrega_no_ambos_refugio_hospital",
            ),
        ]
        indexes = [
            models.Index(fields=["estado", "-solicitada_en"]),
            models.Index(fields=["almacen_origen", "estado"]),
            models.Index(fields=["refugio", "-solicitada_en"]),
            models.Index(fields=["hospital", "-solicitada_en"]),
        ]
        verbose_name = "entrega"
        verbose_name_plural = "entregas"

    def __str__(self):
        destino = (
            self.refugio or self.hospital or self.destinatario_texto or "?"
        )
        return f"{self.codigo} -> {destino} ({self.get_estado_display()})"


class DetalleEntrega(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entrega = models.ForeignKey(
        Entrega, on_delete=models.PROTECT, related_name="detalles",
    )
    insumo = models.ForeignKey(
        Insumo, on_delete=models.PROTECT, related_name="detalles_entrega",
    )
    lote = models.ForeignKey(
        Lote, on_delete=models.PROTECT, related_name="detalles_entrega",
    )
    cantidad = models.DecimalField(max_digits=12, decimal_places=3)
    cantidad_entregada = models.DecimalField(
        max_digits=12, decimal_places=3, default=0,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cantidad__gt=0),
                name="detalle_entrega_cantidad_positiva",
            ),
        ]
        verbose_name = "detalle de entrega"
        verbose_name_plural = "detalles de entrega"

    def __str__(self):
        return f"{self.entrega.codigo}: {self.insumo.codigo} x {self.cantidad}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.lote_id and self.insumo_id:
            if self.lote.insumo_id != self.insumo_id:
                raise ValidationError(
                    {"insumo": "El insumo no coincide con el del lote."}
                )


class TransicionEntrega(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entrega = models.ForeignKey(
        Entrega, on_delete=models.PROTECT, related_name="transiciones",
    )
    estado_anterior = models.CharField(max_length=15, blank=True)
    estado_nuevo = models.CharField(max_length=15)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="transiciones_entrega",
    )
    motivo = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-creado_en"]
        indexes = [models.Index(fields=["entrega", "-creado_en"])]
        verbose_name = "transición de entrega"
        verbose_name_plural = "transiciones de entrega"

    def __str__(self):
        return (
            f"{self.entrega_id}: "
            f"{self.estado_anterior or 'INICIO'} -> {self.estado_nuevo}"
        )
EOF

echo "OK: Entrega + Detalle + Transicion añadidos"

# Verificación de imports antes de seguir
python3 manage.py shell -c "from apps.inventario import models; print('OK: models importan')"
