#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida

cat >> docs/data-dictionary.md << 'DOC'

## 22. `derivaciones.Derivacion`

| Campo | Tipo | Oblig. | Restricciones | Clasif. | Auditoría |
|---|---|---|---|---|---|
| id | UUID | Sí | PK | OPE | — |
| episodio | FK Episodio | Sí | on_delete=PROTECT | CLI | Sí |
| hospital_origen | FK Hospital | Sí | on_delete=PROTECT | OPE | Sí |
| hospital_destino | FK Hospital | Sí | on_delete=PROTECT | OPE | Sí |
| prioridad | CharField(10) | Sí | BAJA/MEDIA/ALTA/CRITICA | OPE | Sí |
| estado | CharField(15) | Sí | TextChoices, index | OPE | Sí |
| motivo | TextField | Sí | — | CLI | Sí |
| solicitada_por | FK Usuario | Sí | on_delete=PROTECT | PER | Sí |
| aceptada_por | FK Usuario | No | on_delete=PROTECT | PER | Sí |
| solicitada_en | DateTimeField | Sí | default=now, index | OPE | — |
| aceptada_en | DateTimeField | No | — | OPE | Sí |
| iniciada_en | DateTimeField | No | — | OPE | Sí |
| completada_en | DateTimeField | No | — | OPE | Sí |
| notas | TextField | No | — | CLI | Sí |
| creado_en / actualizado_en | DateTimeField | Sí | auto | OPE | — |

> **CheckConstraint** `derivacion_origen_distinto_destino`:
> `hospital_origen_id != hospital_destino_id`.
>
> **Regla de prioridad**: en `solicitar_derivacion`, `prioridad` debe ser
> >= mínimo dictado por el `Triaje` vigente del episodio. Mapeo:
> ROJO→ALTA, AMARILLO→MEDIA, VERDE→BAJA. Sin triaje → BAJA.

## 23. `derivaciones.TransicionEstado`

| Campo | Tipo | Oblig. | Restricciones | Clasif. | Auditoría |
|---|---|---|---|---|---|
| id | UUID | Sí | PK | OPE | — |
| derivacion | FK Derivacion | Sí | on_delete=PROTECT | OPE | Sí |
| estado_anterior | CharField(15) | No | blank (vacío=inicio) | OPE | — |
| estado_nuevo | CharField(15) | Sí | TextChoices | OPE | — |
| usuario | FK Usuario | Sí | on_delete=PROTECT | PER | Sí |
| motivo | TextField | No | — | OPE | — |
| creado_en | DateTimeField | Sí | auto_now_add, index | OPE | — |

> **Historial inmutable.** Solo se crea desde `solicitar_derivacion()` y
> `transicionar_derivacion()`. El admin no permite crear, modificar ni eliminar.
DOC

cat >> docs/permissions.md << 'DOC'

### Fase 7 — Derivaciones (IMPLEMENTADO)

- `ADMIN_ORGANIZACION`, `COORDINADOR`, `SANITARIO`: crear y transicionar
  derivaciones en hospitales donde tienen membresía.
- `OPERADOR`: solo lectura de derivaciones de su organización.
- `CONSULTA`: sin acceso a datos clínicos, solo agregados.
- Regla de operación: usuario debe tener membresía ACTIVA en el hospital
  origen o destino (`_usuario_puede_operar` en `services.py`).
- Fase 7.5 (mejora): refinar por transición específica (aceptar solo
  destino, iniciar solo origen, etc.).
DOC

echo ""
echo "▶ Verificación: check + makemigrations"
python3 manage.py check
python3 manage.py makemigrations derivaciones
python3 manage.py migrate derivaciones

echo ""
echo "▶ Tests derivaciones + regresión completa"
python3 manage.py test apps.derivaciones -v 2
python3 manage.py test apps.usuarios apps.triaje apps.organizaciones apps.pacientes apps.hospitales apps.refugios apps.emergencias apps.auditoria -v 1

echo ""
echo "✅ FASE 7 COMPLETADA"
