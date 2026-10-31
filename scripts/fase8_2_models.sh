#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

cat >> apps/inventario/models.py << 'EOF'


class Lote(models.Model):
    """Lote físico de un insumo, identificado por (insumo, código de fabricante).

    Global: un mismo lote puede estar distribuido en varios almacenes.
    La relación Lote ↔ Almacén vive en Stock.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    insumo = models.ForeignKey(
        Insumo, on_delete=models.PROTECT, related_name="lotes"
    )
    codigo = models.CharField(
        max_length=80, help_text="Código del lote de fabricante (L-2024-001, etc)."
    )
    fecha_fabricacion = models.DateField(null=True, blank=True)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    proveedor = models.CharField(max_length=200, blank=True)
    notas = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True, db_index=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["insumo", "fecha_vencimiento", "codigo"]
        constraints = [
            models.UniqueConstraint(
                fields=["insumo", "codigo"],
                name="unique_lote_insumo_codigo",
            ),
        ]
        indexes = [
            models.Index(fields=["insumo", "fecha_vencimiento"]),
        ]
        verbose_name = "lote"
        verbose_name_plural = "lotes"

    def __str__(self):
        return f"{self.insumo.codigo} / {self.codigo}"


class Stock(models.Model):
    """Existencia de un lote específico en un almacén específico.

    cantidad >= 0 garantizado por CheckConstraint.
    Modificación solo a través de registrar_movimiento() en services.py.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    almacen = models.ForeignKey(
        Almacen, on_delete=models.PROTECT, related_name="stocks"
    )
    lote = models.ForeignKey(
        Lote, on_delete=models.PROTECT, related_name="stocks"
    )
    cantidad = models.DecimalField(
        max_digits=12, decimal_places=3, default=0
    )
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["almacen", "lote"]
        constraints = [
            models.UniqueConstraint(
                fields=["almacen", "lote"],
                name="unique_stock_almacen_lote",
            ),
            models.CheckConstraint(
                condition=models.Q(cantidad__gte=0),
                name="stock_cantidad_no_negativa",
            ),
        ]
        indexes = [
            models.Index(fields=["almacen", "lote"]),
        ]
        verbose_name = "existencia"
        verbose_name_plural = "existencias"

    def __str__(self):
        return f"{self.almacen.codigo} / {self.lote} = {self.cantidad}"


class Movimiento(models.Model):
    """Movimiento de kardex inmutable.

    Cada cambio en Stock.cantidad genera un Movimiento.
    No se permite update ni delete (§5.10).
    """
    class Tipo(models.TextChoices):
        ENTRADA = "ENTRADA", "Entrada"
        SALIDA = "SALIDA", "Salida"
        AJUSTE = "AJUSTE", "Ajuste"
        TRANSFERENCIA_ENTRADA = "TRANSFERENCIA_ENTRADA", "Transferencia (entrada)"
        TRANSFERENCIA_SALIDA = "TRANSFERENCIA_SALIDA", "Transferencia (salida)"
        MERMA_VENCIMIENTO = "MERMA_VENCIMIENTO", "Merma por vencimiento"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stock = models.ForeignKey(
        Stock, on_delete=models.PROTECT, related_name="movimientos"
    )
    tipo = models.CharField(max_length=25, choices=Tipo.choices, db_index=True)
    cantidad = models.DecimalField(max_digits=12, decimal_places=3)
    cantidad_anterior = models.DecimalField(max_digits=12, decimal_places=3)
    cantidad_nueva = models.DecimalField(max_digits=12, decimal_places=3)
    diferencia = models.DecimalField(max_digits=12, decimal_places=3)
    referencia_tipo = models.CharField(max_length=30, blank=True)
    referencia_id = models.CharField(max_length=64, blank=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="movimientos_inventario",
    )
    notas = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-creado_en"]
        indexes = [
            models.Index(fields=["stock", "-creado_en"]),
            models.Index(fields=["referencia_tipo", "referencia_id"]),
        ]
        verbose_name = "movimiento de kardex"
        verbose_name_plural = "movimientos de kardex"

    def __str__(self):
        return (
            f"{self.stock} — {self.get_tipo_display()}: "
            f"{self.cantidad_anterior} -> {self.cantidad_nueva}"
        )

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise NotAllowed(
                "Los movimientos de kardex son inmutables."
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise NotAllowed(
            "Los movimientos de kardex son inmutables."
        )


class NotAllowed(Exception):
    """Excepción para bloquear mutaciones de registros inmutables."""
EOF

echo "OK: Lote, Stock, Movimiento añadidos a models.py"
