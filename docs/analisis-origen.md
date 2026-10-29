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
| Cualquiera | **Optimización de rutas** | **Excluido** | — | **Prohibido** §3.6, §15 |

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
