# Plan de Migración — IntegraVida

> **Estado:** procedimiento validado con fixtures sintéticos.
> **Migración real:** pendiente de autorización, Fase 11.

## 1. Principios (§16)

1. **No fusionar bases de datos.** Cada sistema origen tiene su schema.
2. **No copiar código.** Los repos origen son referencia, no dependencia.
3. **Procedimiento validado antes de tocar datos reales.**
4. **Trazabilidad completa** vía `ReferenciaMigracion`.
5. **Idempotencia.** Correr el proceso dos veces no duplica registros.
6. **Los repos origen no se modifican.** Solo se leen sus exports.

## 2. Matriz de correspondencia

| Sistema origen | Entidad origen | Entidad destino | Transformación | Estado |
|---|---|---|---|---|
| Cobijo VZLA | `RefugioExistente` | `refugios.Refugio` | capacidad_disponible → ocupacion_actual = total - disponible; operativo → estado_operativo | Piloto |
| Cobijo VZLA | `ZonaAfectada` | `emergencias.Emergencia` (parcial) | Pendiente: Polygon vs Point | Fase 11+ |
| Cobijo VZLA | `PuntoDemanda`, `SitioCandidato`, `Simulacion`, `ResultadoOptimizacion` | — | Descartado: optimización de rutas (§3.6) | ❌ |
| Deriv. Hosp. | `Paciente` (Sequelize) | `pacientes.Paciente` | triage → Triaje (tabla); edad → fecha_nacimiento; requiere_uci → Triaje | Fase 11+ |
| Deriv. Hosp. | `Hospital` (Sequelize) | `hospitales.Hospital` | lat/lng → PointField; camas_* → RecursoHospitalario | Fase 11+ |
| Deriv. Hosp. | `Traslado` (Sequelize) | `derivaciones.Derivacion` | tiempo_estimado_min / distancia_km / score_prioridad descartados | Fase 11+ |
| NUTRILINK | `supplies` (Laravel) | `inventario.Insumo` | categoria mapeado, es_perecedero → requiere_vencimiento | Piloto |
| NUTRILINK | `shelters` | `refugios.Refugio` (parcial) | poblacion_* no se migra (datos agregados) | Fase 11+ |
| NUTRILINK | `inventory_batches` | `inventario.Lote` + `Stock` | Lote por almacén → Lote global + Stock | Fase 11+ |
| NUTRILINK | `inventory_movements` | `inventario.Movimiento` | tipo mapeado, user_id nullable → PROTECT | Fase 11+ |
| NUTRILINK | `supply_transfers` | `inventario.Transferencia` | Estados sin historial → con TransicionTransferencia | Fase 11+ |
| NUTRILINK | EOQ, Newsvendor, ABC | — | Descartado (§3.5, §3.6) | ❌ |

## 3. Lo que se descarta explícitamente

### Cobijo VZLA

- `optimizacion/` (app completa) — §3.6, §15.
- `PuntoDemanda`, `SitioCandidato`, `Simulacion`, `ResultadoOptimizacion`.

### Derivación Hospitalaria

- `optimization.service.js` — §3.6, §15.
- `tiempo_estimado_min`, `distancia_km`, `score_prioridad`.

### NUTRILINK

- `InventoryOptimizationService.php` — EOQ, Newsvendor, ABC.
- `costo_unitario`, `costo_pedido`, `costo_mantenimiento_anual`,
  `tiempo_entrega_dias`, `stock_seguridad_sugerido`, `punto_reorden`.
- `GoogleAuthenticatorService.php` — 2FA retirado del flujo origen.

## 4. Procedimiento validado (fixtures sintéticos)

### 4.1 Cobijo VZLA → Refugio

Comando:

    python manage.py migrate_cobijo_vzla \
        --fixture=data/fixtures/cobijo_vzla_refugios.json \
        --organizacion=UUID-DE-ORG-DESTINO

Transformación:

- `id` original → `Refugio.codigo` (prefijo `cobijo-`)
- `capacidad_disponible` → `ocupacion_actual = capacidad_total - disponible`
- `operativo` → `estado_operativo` (ACTIVO/INACTIVO)
- Cada registro genera `ReferenciaMigracion` con hash SHA-256.

Idempotencia: si ya existe `ReferenciaMigracion(sistema, entidad,
identificador)`, se omite.

### 4.2 NUTRILINK → Insumo

Comando:

    python manage.py migrate_nutrilink \
        --fixture=data/fixtures/nutrilink_supplies.json \
        --organizacion=UUID-CUALQUIERA

Transformación:

- `codigo` → `Insumo.codigo` (prefijo `nutrilink-`)
- `categoria`: alimento → ALIMENTO, medico → MEDICINA
- `unidad_medida`: kg → KILOGRAMO, cajas → CAJA, etc.
- `es_perecedero=true` → `requiere_lote=True` + `requiere_vencimiento=True`
- `dias_vida_util_promedio` → `vida_util_dias`

Advertencias: si un mapeo no reconoce el valor, la migración continúa
pero marca `resultado_validacion=CON_ADVERTENCIA`.

## 5. Procedimiento para migración real (Fase 11)

### 5.1 Preparación

1. Obtener copia autorizada de los datos origen.
2. Crear respaldos verificables (pg_dump + SHA-256).
3. Verificar compatibilidad de schema (referencia: fixtures piloto).
4. Crear organización destino en IntegraVida.
5. Crear superusuario migrador activo.

### 5.2 Ejecución en staging

1. Ejecutar comandos en staging.
2. Comparar conteos: origen vs ReferenciaMigracion.
3. Revisar `CON_ADVERTENCIA` y `RECHAZADO`.
4. Validar manualmente 5-10 registros al azar.

### 5.3 Ejecución en producción

1. Repetir pasos de staging.
2. Ejecutar en ventana de mantenimiento.
3. Verificar conteos y hashes.
4. Conservar los sistemas origen hasta validación formal (§16.1).

### 5.4 Criterios de aceptación

- [ ] Todos los registros origen tienen `ReferenciaMigracion`.
- [ ] Conteos origen = conteos destino (o exclusiones documentadas).
- [ ] Hashes coinciden entre origen y `hash_origen`.
- [ ] `CON_ADVERTENCIA` revisados y aprobados manualmente.
- [ ] `RECHAZADO` documentados con motivo.
- [ ] Aprobación escrita del responsable institucional.

## 6. Riesgos conocidos

| Riesgo | Mitigación |
|---|---|
| Datos origen con codificaciones raras (mojibake) | Validar UTF-8 antes de migrar |
| Registros con campos NOT NULL vacíos en destino | Revisar `CON_ADVERTENCIA`, corregir a mano |
| Duplicados entre sistemas | §16.1: no fusionar por nombre; revisar caso por caso |
| Cambios en repos origen después del análisis | Re-analizar antes de Fase 11 |
| Volumen grande (>100k registros) | Ejecutar en batches; medir tiempo |

## 7. Referencias

- §16 del prompt maestro.
- `apps/configuracion/models.py` — `ReferenciaMigracion`.
- `apps/configuracion/management/commands/` — comandos.
- `data/fixtures/README.md` — documentación de fixtures.
- `docs/analisis-origen.md` — análisis de los 3 repos origen.
