#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

cat >> docs/data-dictionary.md << 'DOC'

## 29. `inventario.Transferencia`

| Campo | Tipo | Oblig. | Restricciones | Clasif. | Auditoría |
|---|---|---|---|---|---|
| id | UUID | Sí | PK | OPE | — |
| codigo | SlugField(80) | Sí | UNIQUE | OPE | Sí |
| almacen_origen | FK Almacen | Sí | PROTECT | OPE | Sí |
| almacen_destino | FK Almacen | Sí | PROTECT | OPE | Sí |
| prioridad | CharField(10) | Sí | BAJA/MEDIA/ALTA/URGENTE | OPE | Sí |
| estado | CharField(15) | Sí | TextChoices, index | OPE | Sí |
| motivo | TextField | Sí | — | OPE | Sí |
| solicitada_por | FK Usuario | Sí | PROTECT | PER | Sí |
| aprobada_por | FK Usuario | No | PROTECT | PER | Sí |
| despachada_por | FK Usuario | No | PROTECT | PER | Sí |
| recibida_por | FK Usuario | No | PROTECT | PER | Sí |
| solicitada_en | DateTimeField | Sí | default=now | OPE | — |
| aprobada_en / despachada_en / recibida_en | DateTimeField | No | — | OPE | Sí |
| notas | TextField | No | — | OPE | Sí |

> **CheckConstraint `transferencia_origen_distinto_destino`.**
> **Máquina de estados:** BORRADOR → APROBADA → EN_TRANSITO → RECIBIDA.
> Cancelable en BORRADOR/APROBADA (sin movimientos), EN_TRANSITO
> (restauración al origen). RECIBIDA/RECHAZADA/CANCELADA son terminales.

## 30. `inventario.DetalleTransferencia`

| Campo | Tipo | Oblig. | Restricciones | Clasif. | Auditoría |
|---|---|---|---|---|---|
| id | UUID | Sí | PK | OPE | — |
| transferencia | FK Transferencia | Sí | PROTECT | OPE | Sí |
| insumo | FK Insumo | Sí | PROTECT | OPE | Sí |
| lote_origen | FK Lote | Sí | PROTECT | OPE | Sí |
| cantidad | Decimal(12,3) | Sí | > 0 | OPE | Sí |
| cantidad_despachada | Decimal(12,3) | Sí | default=0 | OPE | Sí |
| cantidad_recibida | Decimal(12,3) | Sí | default=0 | OPE | Sí |

> **CheckConstraint `detalle_transferencia_cantidad_positiva`.**
> **`clean()`** valida `lote_origen.insumo == insumo`. Si no coinciden,
> se rechaza. Esto protege contra errores de UI.

## 31. `inventario.TransicionTransferencia`

| Campo | Tipo | Oblig. | Restricciones | Clasif. | Auditoría |
|---|---|---|---|---|---|
| id | UUID | Sí | PK | OPE | — |
| transferencia | FK Transferencia | Sí | PROTECT | OPE | Sí |
| estado_anterior | CharField(15) | No | blank (vacío=inicio) | OPE | — |
| estado_nuevo | CharField(15) | Sí | — | OPE | — |
| usuario | FK Usuario | Sí | PROTECT | PER | Sí |
| motivo | TextField | No | — | OPE | — |
| creado_en | DateTimeField | Sí | auto_now_add | OPE | — |

> **Historial inmutable.** Análogo a `TransicionEstado` de derivaciones.

## Notas de Fase 8.3.1

**Despacho transaccional:** `despachar_transferencia()` hace:
1. `select_for_update(of=("self",))` sobre la Transferencia.
2. Valida stock en TODAS las líneas antes de mover ninguna (fail-fast).
3. `select_for_update(of=("self",))` sobre cada Stock y `registrar_movimiento()`.
4. Actualiza `cantidad_despachada` en cada detalle.
5. Cambia estado y crea `TransicionTransferencia`.
Todo dentro de `@transaction.atomic` — si una línea falla, rollback completo.

**Recepción transaccional:** `recibir_transferencia()` usa `get_or_create` sobre
`Stock` destino (crea si el lote no existía allí) y `registrar_movimiento()`
con tipo `TRANSFERENCIA_ENTRADA`.

**Cancelación con restauración:** si la transferencia estaba `EN_TRANSITO`,
cancela genera `Movimiento.ENTRADA` en el origen por cada `cantidad_despachada`.
DOC

echo ""
echo "▶ check + makemigrations + migrate"
python3 manage.py check
python3 manage.py makemigrations inventario
python3 manage.py migrate inventario

echo ""
echo "▶ Tests transferencias"
python3 manage.py test apps.inventario -v 2

echo ""
echo "▶ Regresión completa"
python3 manage.py test apps.derivaciones apps.usuarios apps.triaje apps.organizaciones apps.pacientes apps.hospitales apps.refugios apps.emergencias apps.auditoria -v 1

echo ""
echo "✅ FASE 8.3.1 COMPLETADA"
