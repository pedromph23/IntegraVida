#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

cat >> docs/data-dictionary.md << 'DOC'

## 26. `inventario.Lote`

| Campo | Tipo | Oblig. | Restricciones | Clasif. | Auditoría |
|---|---|---|---|---|---|
| id | UUID | Sí | PK | OPE | — |
| insumo | FK Insumo | Sí | on_delete=PROTECT | OPE | Sí |
| codigo | CharField(80) | Sí | UNIQUE(insumo, codigo) | OPE | Sí |
| fecha_fabricacion | DateField | No | — | OPE | Sí |
| fecha_vencimiento | DateField | No | index | OPE | Sí |
| proveedor | CharField(200) | No | — | OPE | Sí |
| notas | TextField | No | — | OPE | Sí |

> **Global, no por almacén.** Corrige fallo de NUTRILINK: el mismo código
> de lote no puede tener fechas distintas en almacenes distintos. Si llega
> un lote duplicado con fecha diferente, el UniqueConstraint lo rechaza
> y el operador debe registrar dos lotes con códigos distintos (L-X y L-X-2).

## 27. `inventario.Stock`

| Campo | Tipo | Oblig. | Restricciones | Clasif. | Auditoría |
|---|---|---|---|---|---|
| id | UUID | Sí | PK | OPE | — |
| almacen | FK Almacen | Sí | on_delete=PROTECT | OPE | Sí |
| lote | FK Lote | Sí | on_delete=PROTECT | OPE | Sí |
| cantidad | Decimal(12,3) | Sí | default=0, >= 0 | OPE | Sí |
| actualizado_en | DateTimeField | Sí | auto_now | OPE | — |

> **UniqueConstraint(almacen, lote)** + **CheckConstraint(cantidad >= 0)**.
> Solo se modifica vía `registrar_movimiento()`.

## 28. `inventario.Movimiento`

| Campo | Tipo | Oblig. | Restricciones | Clasif. | Auditoría |
|---|---|---|---|---|---|
| id | UUID | Sí | PK | OPE | — |
| stock | FK Stock | Sí | on_delete=PROTECT | OPE | Sí |
| tipo | CharField(25) | Sí | ENTRADA/SALIDA/AJUSTE/TRANSFERENCIA_*/MERMA_VENCIMIENTO | OPE | Sí |
| cantidad | Decimal(12,3) | Sí | — | OPE | Sí |
| cantidad_anterior | Decimal(12,3) | Sí | — | OPE | Sí |
| cantidad_nueva | Decimal(12,3) | Sí | — | OPE | Sí |
| diferencia | Decimal(12,3) | Sí | — | OPE | Sí |
| referencia_tipo | CharField(30) | No | — | OPE | Sí |
| referencia_id | CharField(64) | No | — | OPE | Sí |
| registrado_por | FK Usuario | No | on_delete=PROTECT | PER | Sí |
| notas | TextField | No | — | OPE | Sí |

> **Inmutable.** `save()` sobre existente lanza `NotAllowed`. `delete()`
> siempre. Correcciones se hacen con `AJUSTE` compensatorio (§5.10).
> El admin no permite crear, modificar ni eliminar.

## Notas de Fase 8.2

**FEFO — First Expired, First Out:**
- Función: `seleccionar_stock_fefo(insumo, almacen, cantidad)`.
- Solo aplica a insumos con `requiere_vencimiento=True`.
- Ordena por `lote.fecha_vencimiento ASC NULLS LAST`, excluye vencidos.
- Devuelve el `Stock` (no reserva). La operación real es
  `registrar_movimiento()`.
- Si ningún lote cubre la cantidad solicitada en un solo lote, devuelve
  `None`. Repartir entre lotes está fuera de Fase 8.2 (se evalúa en 8.3
  para transferencias multi-lote).

**Concurrencia:** `registrar_movimiento()` usa `select_for_update(of=("self",))`
sobre el `Stock`. Evita cantidad negativa por salidas simultáneas.
DOC

echo ""
echo "▶ check + makemigrations + migrate"
python3 manage.py check
python3 manage.py makemigrations inventario
python3 manage.py migrate inventario

echo ""
echo "▶ Tests inventario (8.1 + 8.2)"
python3 manage.py test apps.inventario -v 2

echo ""
echo "▶ Regresión completa"
python3 manage.py test apps.derivaciones apps.usuarios apps.triaje apps.organizaciones apps.pacientes apps.hospitales apps.refugios apps.emergencias apps.auditoria -v 1

echo ""
echo "✅ FASE 8.2 COMPLETADA"
