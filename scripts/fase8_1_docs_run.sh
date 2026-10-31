#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

cat >> docs/data-dictionary.md << 'DOC'

## 24. `inventario.Insumo`

| Campo | Tipo | Oblig. | Restricciones | Clasif. | Auditoría |
|---|---|---|---|---|---|
| id | UUID | Sí | PK | OPE | — |
| codigo | SlugField(80) | Sí | UNIQUE | PUB | Sí |
| nombre | CharField(200) | Sí | — | PUB | Sí |
| categoria | CharField(20) | Sí | TextChoices, index | PUB | Sí |
| subcategoria | CharField(80) | No | — | PUB | Sí |
| unidad_medida | CharField(15) | Sí | TextChoices | PUB | Sí |
| requiere_lote | Boolean | Sí | default=False | OPE | Sí |
| requiere_vencimiento | Boolean | Sí | default=False | OPE | Sí |
| vida_util_dias | PositiveInt | No | — | PUB | Sí |
| stock_minimo_global | Decimal(12,3) | Sí | default=0 | OPE | Sí |
| activo | Boolean | Sí | default=True, index | PUB | Sí |
| notas | TextField | No | — | OPE | Sí |
| creado_en / actualizado_en | DateTimeField | Sí | auto | OPE | — |

> **CheckConstraint `insumo_vencimiento_requiere_lote`:**
> `requiere_vencimiento=True` exige `requiere_lote=True`.
> Si un insumo vence, debe poder rastrearse por lote.
>
> **Insumo es global** (sin organización). Catálogo compartido entre
> todas las organizaciones.

## 25. `inventario.Almacen`

| Campo | Tipo | Oblig. | Restricciones | Clasif. | Auditoría |
|---|---|---|---|---|---|
| id | UUID | Sí | PK | OPE | — |
| codigo | SlugField(80) | Sí | UNIQUE | OPE | Sí |
| nombre | CharField(200) | Sí | — | OPE | Sí |
| organizacion | FK Organizacion | Sí | on_delete=PROTECT | OPE | Sí |
| hospital | FK Hospital | No | on_delete=PROTECT | OPE | Sí |
| refugio | FK Refugio | No | on_delete=PROTECT | OPE | Sí |
| ubicacion | PointField | No | SRID 4326 | OPE | Sí |
| direccion | CharField(300) | No | — | OPE | Sí |
| municipio | FK Municipio | No | on_delete=PROTECT | PUB | Sí |
| parroquia | FK Parroquia | No | on_delete=PROTECT | PUB | Sí |
| activo | Boolean | Sí | default=True | OPE | Sí |
| notas | TextField | No | — | OPE | Sí |
| creado_en / actualizado_en | DateTimeField | Sí | auto | OPE | — |

> **CheckConstraint `almacen_no_ambos_hospital_y_refugio`:**
> `NOT (hospital_id IS NOT NULL AND refugio_id IS NOT NULL)`.
>
> Los 3 estados válidos son:
> - `hospital` set, `refugio` null → almacén de hospital.
> - `refugio` set, `hospital` null → almacén de refugio.
> - ambos null → almacén independiente (centro de acopio).
>
> **Property `tipo_ubicacion`** devuelve `HOSPITAL`, `REFUGIO` o
> `INDEPENDIENTE`.
DOC

echo ""
echo "▶ check + makemigrations + migrate"
python3 manage.py check
python3 manage.py makemigrations inventario
python3 manage.py migrate inventario

echo ""
echo "▶ Tests inventario + regresión"
python3 manage.py test apps.inventario -v 2
python3 manage.py test apps.derivaciones apps.usuarios apps.triaje apps.organizaciones apps.pacientes apps.hospitales apps.refugios apps.emergencias apps.auditoria -v 1

echo ""
echo "✅ FASE 8.1 COMPLETADA"
