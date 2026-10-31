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
