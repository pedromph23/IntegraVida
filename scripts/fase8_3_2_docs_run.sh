#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

cat >> docs/data-dictionary.md << 'DOC'

## 32. `inventario.Entrega`

| Campo | Tipo | Oblig. | Restricciones | Clasif. | Auditoría |
|---|---|---|---|---|---|
| id | UUID | Sí | PK | OPE | — |
| codigo | SlugField(80) | Sí | UNIQUE | OPE | Sí |
| almacen_origen | FK Almacen | Sí | PROTECT | OPE | Sí |
| refugio | FK Refugio | No | PROTECT | OPE | Sí |
| hospital | FK Hospital | No | PROTECT | OPE | Sí |
| destinatario_texto | CharField(300) | No | — | OPE | Sí |
| estado | CharField(15) | Sí | BORRADOR/ENVIADA/RECIBIDA/CANCELADA | OPE | Sí |
| motivo | TextField | Sí | — | OPE | Sí |
| solicitada_por / enviada_por / recibida_por | FK Usuario | Varía | PROTECT | PER | Sí |
| solicitada_en / enviada_en / recibida_en | DateTimeField | Varía | — | OPE | — |
| notas | TextField | No | — | OPE | Sí |

> **CheckConstraint `entrega_con_destino`:** al menos uno de
> `refugio`, `hospital` o `destinatario_texto` no vacío.
> **CheckConstraint `entrega_no_ambos_refugio_hospital`:**
> `refugio` y `hospital` nunca simultáneos.
>
> **Diferencia con Transferencia:** el destino NO tiene `Stock`. Es un
> punto de consumo humanitario. Al enviar, solo se descuenta del origen
> (`Movimiento.SALIDA`). Al recibir, solo se actualiza `recibida_en`.
>
> **Estados:** BORRADOR → ENVIADA → RECIBIDA / CANCELADA.
> Simplificado respecto a Transferencia: no hay APROBADA separada
> porque la entrega humanitaria se envía en un solo paso operativo.

## 33. `inventario.DetalleEntrega`

| Campo | Tipo | Oblig. | Restricciones | Clasif. | Auditoría |
|---|---|---|---|---|---|
| id | UUID | Sí | PK | OPE | — |
| entrega | FK Entrega | Sí | PROTECT | OPE | Sí |
| insumo | FK Insumo | Sí | PROTECT | OPE | Sí |
| lote | FK Lote | Sí | PROTECT | OPE | Sí |
| cantidad | Decimal(12,3) | Sí | > 0 | OPE | Sí |
| cantidad_entregada | Decimal(12,3) | Sí | default=0 | OPE | Sí |

## 34. `inventario.TransicionEntrega`

Análogo a `TransicionTransferencia`. Historial inmutable.
DOC

echo ""
echo "▶ check + makemigrations + migrate"
python3 manage.py check
python3 manage.py makemigrations inventario
python3 manage.py migrate inventario

echo ""
echo "▶ Tests inventario (8.1 + 8.2 + 8.3.1 + 8.3.2)"
python3 manage.py test apps.inventario -v 2

echo ""
echo "▶ Regresión completa"
python3 manage.py test apps.derivaciones apps.usuarios apps.triaje apps.organizaciones apps.pacientes apps.hospitales apps.refugios apps.emergencias apps.auditoria -v 1

echo ""
echo "✅ FASE 8.3.2 COMPLETADA — FASE 8 CERRADA"
