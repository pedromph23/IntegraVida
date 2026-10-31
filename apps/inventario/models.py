import uuid

from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.db import models
from django.utils import timezone


class NotAllowed(Exception):
    """Excepción para bloquear mutaciones de registros inmutables."""


class Insumo(models.Model):
    class Categoria(models.TextChoices):
        AGUA = "AGUA", "Agua"
        ALIMENTO = "ALIMENTO", "Alimento"
        MEDICINA = "MEDICINA", "Medicina"
        HIGIENE = "HIGIENE", "Higiene"
        ABRIGO = "ABRIGO", "Abrigo"
        ROPA = "ROPA", "Ropa"
        EQUIPO_MEDICO = "EQUIPO_MEDICO", "Equipo médico"
        OTRO = "OTRO", "Otro"

    class UnidadMedida(models.TextChoices):
        UNIDAD = "UNIDAD", "Unidad"
        GRAMO = "GRAMO", "Gramo"
        KILOGRAMO = "KILOGRAMO", "Kilogramo"
        MILILITRO = "MILILITRO", "Mililitro"
        LITRO = "LITRO", "Litro"
        CAJA = "CAJA", "Caja"
        PAQUETE = "PAQUETE", "Paquete"
        RACION = "RACION", "Ración"
        FRASCO = "FRASCO", "Frasco"
        OTRO = "OTRO", "Otro"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo = models.SlugField(max_length=80, unique=True)
    nombre = models.CharField(max_length=200)
    categoria = models.CharField(
        max_length=20, choices=Categoria.choices, db_index=True
    )
    subcategoria = models.CharField(max_length=80, blank=True)
    unidad_medida = models.CharField(
        max_length=15, choices=UnidadMedida.choices
    )
    requiere_lote = models.BooleanField(default=False)
    requiere_vencimiento = models.BooleanField(default=False)
    vida_util_dias = models.PositiveIntegerField(null=True, blank=True)
    stock_minimo_global = models.DecimalField(
        max_digits=12, decimal_places=3, default=0
    )
    activo = models.BooleanField(default=True, db_index=True)
    notas = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True, db_index=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["categoria", "nombre"]
        indexes = [
            models.Index(fields=["categoria", "activo"]),
            models.Index(fields=["nombre"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(requiere_vencimiento=False)
                    | models.Q(requiere_lote=True)
                ),
                name="insumo_vencimiento_requiere_lote",
            ),
        ]
        verbose_name = "insumo"
        verbose_name_plural = "insumos"

    def __str__(self):
        return f"{self.nombre} ({self.codigo})"


class Almacen(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo = models.SlugField(max_length=80, unique=True)
    nombre = models.CharField(max_length=200)
    organizacion = models.ForeignKey(
        "organizaciones.Organizacion",
        on_delete=models.PROTECT,
        related_name="almacenes",
    )
    hospital = models.ForeignKey(
        "hospitales.Hospital",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="almacenes",
    )
    refugio = models.ForeignKey(
        "refugios.Refugio",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="almacenes",
    )
    ubicacion = gis_models.PointField(
        srid=4326, geography=True, null=True, blank=True
    )
    direccion = models.CharField(max_length=300, blank=True)
    municipio = models.ForeignKey(
        "territorio.Municipio",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="almacenes",
    )
    parroquia = models.ForeignKey(
        "territorio.Parroquia",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="almacenes",
    )
    activo = models.BooleanField(default=True, db_index=True)
    notas = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True, db_index=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-creado_en"]
        indexes = [
            models.Index(fields=["organizacion", "activo"]),
            models.Index(fields=["hospital", "activo"]),
            models.Index(fields=["refugio", "activo"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~(
                    models.Q(hospital__isnull=False)
                    & models.Q(refugio__isnull=False)
                ),
                name="almacen_no_ambos_hospital_y_refugio",
            ),
        ]
        verbose_name = "almacén"
        verbose_name_plural = "almacenes"

    def __str__(self):
        return f"{self.nombre} ({self.codigo})"

    @property
    def tipo_ubicacion(self):
        if self.hospital_id:
            return "HOSPITAL"
        if self.refugio_id:
            return "REFUGIO"
        return "INDEPENDIENTE"

    @property
    def lat(self):
        return self.ubicacion.y if self.ubicacion else None

    @property
    def lng(self):
        return self.ubicacion.x if self.ubicacion else None


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
