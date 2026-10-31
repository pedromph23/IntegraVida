# Análisis de sistemas de origen — Fase 0

> Los tres repositorios de origen **no se modifican, ni se copian** (§3, §16).
> Se analizan para identificar funcionalidades reutilizables que se **rediseñan**
> en IntegraVida con su propio código y base de datos.

## Repositorios analizados

| # | Proyecto | URL | Funcionalidades potencialmente reutilizables |
|---|---|---|---|
| 1 | Cobijo VZLA | https://github.com/pedromph23/cobijo_vzla.git | Refugios, zonas afectadas, reportes ciudadanos, catálogo territorial |
| 2 | Sistema de Derivación Hospitalaria | https://github.com/pedromph23/sistema-derivacion-hospitalaria.git | Hospitales, pacientes, triaje, derivaciones, traslados |
| 3 | NUTRILINK | https://github.com/jesusandrescardozo-lang/Pagina | Refugios, insumos, lotes, vencimientos, movimientos, distribución |

## Matriz de reutilización funcional (§16)

| Origen | Funcionalidad original | Estado en IntegraVida | Fase del prompt | Notas |
|---|---|---|---|---|
| Cobijo VZLA | Gestión de refugios | TBD | Fase 5 | Pendiente modelo propio |
| Cobijo VZLA | Reportes ciudadanos | Parcial | Fase 4–5 | `ReporteEmergencia` ya implementado |
| Cobijo VZLA | Zonas afectadas | TBD | Fase 5 | — |
| Cobijo VZLA | Catálogo territorial | Implementado | Fase 2 | Jerarquía `EntidadFederal → Municipio → Parroquia` |
| Cobijo VZLA | Auditoría de operaciones | Implementado | Fase 2–3 | Modelo `EventoAuditoria` base |
| Hosp. Derivación | Hospitales | TBD | Fase 6 | — |
| Hosp. Derivación | Pacientes | TBD | Fase 6 | Requiere `docs/privacy-and-retention.md` antes |
| Hosp. Derivación | Triaje | TBD | Fase 6 | Depende de pacientes |
| Hosp. Derivación | Derivaciones y traslados | TBD | Fase 7 | — |
| NUTRILINK | Inventario, lotes, vencimientos | TBD | Fase 8 | FEFO obligatorio §5.10 |
| NUTRILINK | Movimientos y transferencias | TBD | Fase 8 | Transaccionalidad obligatoria §10 |
| NUTRILINK | Distribución y entregas | TBD | Fase 8 | — |
| Cobijo VZLA | **Optimización de rutas** | **Excluido** | — | **Prohibido** §3.6, §15. App existe pero está vacía (3 líneas). |

## Decisiones de diseño tomadas hasta la fecha

- Base de datos nueva e independiente: `integravida_db` (PostgreSQL 17.11 + PostGIS 3.5.2).
- No se importan datos reales de los sistemas de origen (§16).
- No se copia código de los repositorios originales (§3).
- No hay dependencia de Supabase ni de otro proveedor externo todavía (§4.1).
- Apps implementadas con modelos reales: `usuarios`, `organizaciones`, `territorio`, `auditoria`, `emergencias`.
- App `notificaciones` **eliminada**: no estaba justificada en §5 (§12.3).
- Apps vacías restantes **eliminadas**: `configuracion`, `derivaciones`, `distribucion`, `hospitales`, `inventario`, `pacientes`, `refugios`, `reportes`, `triaje`. Se recrearán con `startapp` cuando su fase lo requiera.
- DRF configurado con `IsAuthenticated` por defecto (§6.3, §17). Los endpoints públicos (§6.1) declararán `AllowAny` explícito.

## Pendientes de este análisis

- [ ] Clonar los 3 repositorios en un directorio separado (`~/analisis-origen/`) y revisar modelos reales.
- [ ] Inventariar entidades y campos de cada repo origen.
- [ ] Identificar campos con datos personales o clínicos en cada repo.
- [ ] Completar columna "Qué se descarta" con motivo por funcionalidad.
- [ ] Diseñar la entidad `ReferenciaMigracion` (§16) para trazabilidad futura.
- [ ] Clasificar cada entidad origen por sensibilidad (§4.4).

## Nota sobre migración de datos

No se migrarán datos reales de los sistemas de origen hasta completar Fase 10
(§24) y contar con un procedimiento validado y aprobado (§16.1).

## Hallazgos del análisis de Cobijo VZLA (Fase 0, retroactivo)

Repositorio clonado en `~/analisis-origen/cobijo_vzla` (fuera de `integravida/`).

### Estructura de apps

| App | Líneas en `models.py` | Contenido |
|---|---|---|
| `core` | 505 | Modelos de dominio principal (a analizar) |
| `emergencias` | 172 | Comparable al nuestro |
| `reportes` | 59 | Reportes ciudadanos |
| `publico` | 3 | Vacía |
| `mapa` | 3 | Vacía |
| `optimizacion` | 3 | **Vacía. Descartado por §3.6/§15.** |

### Apps descartadas explícitamente

- **`optimizacion`**: aunque la carpeta existe, está vacía. El prompt §3.6
  y §15 prohíben el módulo de optimización de rutas. No se implementará en
  IntegraVida bajo ninguna forma.

### Pendiente de este análisis

- [ ] Leer `apps/core/models.py` y extraer qué entidades son relevantes.
- [ ] Leer `apps/reportes/models.py` (cabe completo, 59 líneas).
- [ ] Comparar `apps/emergencias/models.py` con `apps/emergencias/models.py` de IntegraVida.

## Hallazgos del análisis de `core/models.py` (Cobijo VZLA)

Analizados selectivamente los modelos relevantes. Los modelos de
optimización (`Simulacion`, `ResultadoOptimizacion`, `SitioCandidato`)
**no se leyeron** por §3.6/§15.

### Matriz de decisiones

| Modelo original | Veredicto | Qué se toma | Qué se descarta |
|---|---|---|---|
| `UbicacionParroquiaMixin` | Descartar | — | Auto-asignación en `save()` con queries |
| `PuntoDemanda` | Descartar | — | Concepto de optimización de rutas |
| `RefugioExistente` | Rediseñar | constraint `disponible ≤ total`, properties, índices | `capacidad_disponible` mutable, `operativo` boolean, `SET_NULL`, falta de org/responsable/necesidades |
| `ZonaAfectada` | Considerar Fase 5.5 | `geom` Polygon, conteos heridos/fallecidos/damnificados | — |
| `RegistroAuditoria` | No copiar | — | Nuestro `EventoAuditoria` con hash es superior |
| `RegistroVersion` | Mejora futura | Idea de snapshots históricos | Implementación completa |
| `Simulacion` / `ResultadoOptimizacion` / `SitioCandidato` | **Prohibido** | — | §3.6, §15 del prompt |

### Modelo `RefugioExistente` — hallazgos específicos

**Lo útil:**
- `constraint capacidad_disponible <= capacidad_total` (copiar a nuestro `Refugio`)
- Properties `lat`, `lng`, `porcentaje_ocupacion`, `esta_lleno`
- `servicios` como `JSONField(default=list)` con validación de catálogo
- `ubicacion` como `PointField(srid=4326)`
- Índices en `operativo` y `parroquia`

**Lo mejorable:**
- `capacidad_disponible` mutable → **race condition** (§10). Nuestra solución:
  `ocupacion_actual` + `RegistroOcupacion` + `select_for_update()`.
- `operativo` boolean → usar `TextChoices` con estados operativos.
- `parroquia` con `SET_NULL` → `PROTECT` + añadir `municipio` y `entidad_federal`.
- Faltan: `organizacion` FK, `responsable` FK, `necesidades`, `creado_en`,
  `actualizado_en`, `codigo`.

### Modelo `ZonaAfectada` — para considerar en Fase 5.5

Aporta dos ideas nuevas respecto a nuestro `Emergencia`:
1. `geom = PolygonField(srid=4326)` en lugar de `punto = PointField`.
   Una emergencia puede afectar un área, no solo un punto.
2. Conteos humanitarios: `heridos`, `fallecidos`, `damnificados`.

**No se implementa en Fase 5.** Se evalúa en Fase 5.5 o Fase 6.

### Modelos de versionado — para Fase 5.5

- `RegistroAuditoria` del original: sin hash, sin inmutabilidad.
  Nuestro `EventoAuditoria` es estrictamente superior.
- `RegistroVersion`: snapshots completos por cambio. Podría añadirse
  como mejora opcional en Fase 5.5 para permitir "cómo era este refugio
  en fecha X". No es bloqueante.

## Hallazgos del análisis de Sistema Derivación Hospitalaria

Repositorio clonado en `~/analisis-origen/sistema-derivacion-hospitalaria`
(fuera de `integravida/`). Stack: **Node.js + Express + Sequelize (SQL) + React**.

### Archivos leídos

- `backend/src/models/Hospital.js`
- `backend/src/models/index.js`
- `backend/src/models/Paciente.js`
- `backend/src/models/Traslado.js`
- `frontend/src/schemas/hospital.schemas.js`

### Archivos descartados explícitamente

- `backend/src/services/optimization.service.js` — **Prohibido** §3.6, §15.
- Todo `frontend/src/components/` — interfaz visual.
- `backend/src/config/` — conexión y seeder.
- `backend/src/controllers/`, `backend/src/routes/` — lógica de HTTP.

### Matriz de decisiones

| Elemento original | Veredicto | Qué se toma | Qué se descarta |
|---|---|---|---|
| `Hospital.nivel` (Nivel I-IV) | Adoptar | `TextChoices` con valores venezolanos | STRING libre |
| `Hospital.camas_*_totales` / `*_libres` | Rediseñar | Modelo `RecursoHospitalario` + `RegistroDisponibilidad` | Columnas mutables directas |
| `Hospital.estado_operativo` | Adoptar corregido | `DISPONIBLE/SATURADO/COLAPSADO/NO_OPERATIVO` | Inconsistencia con `INACTIVO` del frontend |
| `Hospital.latitud` + `longitud` | Rediseñar | `PointField` único | Campos separados |
| `Hospital` sin `organizacion`, `responsable`, `municipio` | Corregir | Añadir FK PROTECT | Ausencia |
| `Paciente.triage` como campo | **Descartar** | `Triaje` como entidad separada en Fase 6.3 | Campo en Paciente |
| `Paciente.edad` | **Descartar** | `fecha_nacimiento` + property `edad` | Campo edad mutable |
| `Paciente.requiere_uci/quirofano` | **Descartar** | Van en `Triaje` (Fase 6.3) | Campos en Paciente |
| `Paciente.nombre` (un solo campo) | Rediseñar | `nombres` + `apellidos` separados | Nombre único |
| `Traslado.tiempo_estimado_min` / `distancia_km` / `score_prioridad` | **Descartar** | — | **Prohibido** §3.6/§15 |
| `Traslado.estado` (ASIGNADO/EN_CAMINO/COMPLETADO/CANCELADO) | Adoptar | `TextChoices` en `Derivacion` (Fase 7) | — |
| Relación `Traslado.belongsTo(Hospital, origen/destino)` | Adoptar | `Derivacion` con `hospital_origen` + `hospital_destino` | — |

### Errores del original documentados

1. **`Paciente.triage` como atributo** — viola §5.8. En IntegraVida el triaje
   es una entidad con historial propio (Fase 6.3).
2. **`Paciente.edad`** en vez de `fecha_nacimiento` — error de modelado.
3. **`requiere_uci` / `requiere_quirofano`** como campos del paciente —
   son necesidades detectadas en un evento de triaje.
4. **`score_prioridad` / `distancia_km` / `tiempo_estimado_min`** en
   `Traslado` — módulo de optimización prohibido (§3.6, §15).
5. **Inconsistencia** `NO_OPERATIVO` (backend) vs `INACTIVO` (frontend) —
   se define una sola versión en IntegraVida.
6. **Ausencia de `organizacion`** FK — sin aislamiento entre instituciones.
7. **`latitud` / `longitud` separados** — usamos `PointField` coherente con
   `Emergencia` y `Refugio`.
8. **`cedula` + `nombre`** en el mismo modelo sin clasificación explícita de
   sensibilidad — en IntegraVida se clasifican como PER con control de acceso.

### Pendiente

- [ ] Fase 6.1: implementar `Hospital`, `Servicio`, `HospitalServicio`,
      `RecursoHospitalario`, `RegistroDisponibilidad`.
- [ ] Fase 6.2: `Paciente`, `Episodio`, `ContactoEmergencia` (requiere
      decisión de cifrado).
- [ ] Fase 6.3: `Triaje`, `Reevaluacion`.
- [ ] Fase 7: `Derivacion`, `TransicionEstado` (aquí se aplica el ciclo
      ASIGNADO → EN_CAMINO → COMPLETADO → CANCELADO).

## Hallazgos del análisis de NUTRILINK (Fase 8)

Repositorio clonado en `~/analisis-origen/nutrilink` (fuera de `integravida/`).
Stack: **Laravel 9 (PHP 8) + Eloquent ORM**.

### Archivos analizados

- `database/migrations/2026_09_07_000001_create_shelters_and_supplies_tables.php`
- `database/migrations/2026_09_07_000002_create_movements_and_transfers_tables.php`
- `README.md` (descripción de funcionalidades)

### Archivos descartados explícitamente

- `app/Services/InventoryOptimizationService.php` — EOQ, Newsvendor,
  punto de reorden, clasificación ABC. **Prohibido** §3.5, §3.6, §15.
- `app/Services/GoogleAuthenticatorService.php` — 2FA retirado del flujo
  en el propio NUTRILINK.
- `app/Console/Commands/NeonSetup.php`,
  `app/Database/Connectors/NeonPostgresConnector.php` — específico de Neon.
- `app/Http/Controllers/*` — lógica HTTP, no modelos.

### Matriz de decisiones

| Elemento original | Veredicto | Qué se toma | Qué se descarta |
|---|---|---|---|
| `supplies` (catálogo) | Adoptar | codigo UNIQUE, nombre, categoria, subcategoria, unidad_medida, es_perecedero→requiere_vencimiento, dias_vida_util→vida_util_dias | clasificacion_abc, EOQ, Newsvendor, costos, lead time, stock_seguridad_sugerido |
| `shelter_inventories` (stock agregado) | Rediseñar | Idea de existencia por almacén | No incluye lote (corregido) |
| `inventory_batches` (lotes) | **Corregir** | numero_lote, cantidad_disponible, fecha_vencimiento | Colgaba de `shelter_inventory` (por almacén); IntegraVida lo hace global por (insumo, codigo) |
| `inventory_movements` (kardex) | Adoptar | stock_anterior, stock_nuevo, cantidad, tipo TextChoices, motivo, documento_referencia | tipos específicos de NUTRILINK, user_id nullable (en IntegraVida es PROTECT) |
| `supply_transfers` (transferencias) | Adoptar extendido | Estados, prioridad, vehículo, fechas | Sin máquina de estados rígida; IntegraVida la hace explícita |
| `cantidad Decimal(14,2)` | **Corregir** | — | Decimal(12,3) para gramos/mililitros |
| `shelters` (refugios) | **No aplica** | — | Ya implementado en Fase 5 |

### Errores del original documentados

1. **Lote por almacén, no global.** Dos refugios podían tener `numero_lote`
   idéntico con fechas distintas. IntegraVida rechaza esto con
   `UniqueConstraint(insumo, codigo)`.
2. **`cantidad decimal(14,2)`** insuficiente para gramos/mililitros.
   Corregido a `Decimal(12,3)`.
3. **Kardex sin inmutabilidad formal.** NUTRILINK permite conceptos de
   UPDATE en algunas rutas; IntegraVida bloquea `save()` y `delete()`
   sobre `Movimiento` con `NotAllowed`.
4. **FEFO con `lockForUpdate` en stock agregado** (no por lote). NUTRILINK
   no tiene granularidad lote-nivel para el lock; IntegraVida sí.

### Pendiente

- Fase 8 completada: 8.1 (Insumo + Almacen), 8.2 (Lote + Stock +
  Movimiento + FEFO), 8.3.1 (Transferencia), 8.3.2 (Entrega).
- 199 tests verdes en el proyecto (52 inventario + 147 otros apps).

## Hallazgos del análisis de NUTRILINK (Fase 8)

Repositorio clonado en `~/analisis-origen/nutrilink` (fuera de `integravida/`).
Stack: **Laravel 9 (PHP 8) + Eloquent ORM**.

### Archivos analizados
- `database/migrations/2026_09_07_000001_create_shelters_and_supplies_tables.php`
- `database/migrations/2026_09_07_000002_create_movements_and_transfers_tables.php`
- `README.md` (descripción funcional)

### Archivos descartados explícitamente
- `app/Services/InventoryOptimizationService.php` — EOQ, Newsvendor, ABC. **Prohibido** §3.5, §3.6, §15.
- `app/Services/GoogleAuthenticatorService.php` — 2FA retirado en el propio NUTRILINK.
- `app/Console/Commands/NeonSetup.php`, `app/Database/Connectors/NeonPostgresConnector.php` — específico de Neon.

### Matriz de decisiones

| Elemento | Veredicto | Se toma | Se descarta |
|---|---|---|---|
| `supplies` | Adoptar | codigo, nombre, categoria, subcategoria, unidad_medida, es_perecedero→requiere_vencimiento, dias_vida_util→vida_util_dias | clasificacion_abc, EOQ, Newsvendor, costos, lead time |
| `inventory_batches` | **Corregir** | numero_lote, cantidad_disponible, fecha_vencimiento | Colgaba de stock por almacén; IntegraVida lo hace global por (insumo, codigo) |
| `inventory_movements` | Adoptar extendido | stock_anterior, stock_nuevo, tipo, motivo, referencia | Ahora inmutable con `NotAllowed` |
| `supply_transfers` | Adoptar extendido | estados, prioridad, fechas | Sin máquina formal → ahora con `TRANSICIONES_PERMITIDAS` |
| `cantidad Decimal(14,2)` | **Corregir** | — | Decimal(12,3) para gramos |

### Errores del original documentados
1. **Lote por almacén, no global** → UniqueConstraint(insumo, codigo).
2. **Decimal(14,2)** insuficiente → Decimal(12,3).
3. **Kardex sin inmutabilidad formal** → `Movimiento.save/delete` bloquean.
4. **FEFO sin lock por stock** → `select_for_update(of=("self",))` sobre Stock.

### Cierre
Fase 8 completa: 8.1 (Insumo + Almacen), 8.2 (Lote + Stock + Movimiento + FEFO), 8.3.1 (Transferencia), 8.3.2 (Entrega). 199 tests verdes.
