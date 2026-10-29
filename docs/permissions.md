# Política de Roles y Permisos — IntegraVida

> **Estado:** parcial — cubre los roles implementados y la matriz de las 5
> entidades existentes (usuarios, organizaciones, territorio, auditoría,
> emergencias). Los roles por fase se documentan en la sección 7.

## 1. Principios rectores

1. **Mínimo privilegio.** Un rol concede solo los permisos necesarios para
   su función. Sin roles "comodín".
2. **Frontera del backend.** El frontend no decide permisos; solo oculta o
   muestra. Toda verificación ocurre en el servidor (§8, §17).
3. **Necesidad de conocer.** El acceso a datos `PER` o `CLI` exige
   justificación funcional, no basta con tener rol.
4. **Autorización por objeto.** No basta con verificar rol. Se verifica
   también la organización, el ámbito y el estado del objeto (§8).
5. **Administración global separada.** El superusuario administra la
   plataforma. Los roles de organización solo operan dentro de su
   organización.

## 2. Roles implementados en `Membresia.Rol`

Definidos en `apps.organizaciones.models.Membresia.Rol` (6 roles).

| Valor | Descripción | Ámbito natural |
|---|---|---|
| `ADMIN_ORGANIZACION` | Administra la organización y sus membresías | Organización completa |
| `COORDINADOR` | Coordina operaciones de la organización | Organización completa |
| `OPERADOR` | Registra y actualiza datos operativos | Organización completa |
| `SANITARIO` | Personal de salud (triaje, expedientes) | Organización (hospital) |
| `LOGISTICA` | Inventario, distribución, entregas | Organización (almacén) |
| `CONSULTA` | Acceso de solo lectura a información autorizada | Organización completa |

**Restricción:** un usuario tiene **un solo rol por organización**
(`UniqueConstraint(usuario, organizacion)`). Si un usuario necesita dos
roles, debe crearse en otra organización o evaluarse en una fase posterior.

**Estados de membresía:** solo `ACTIVA` concede acceso. `PENDIENTE`,
`SUSPENDIDA` y `REVOCADA` se rechazan en todos los flujos.

## 3. Administración global

`puede_administrar_plataforma(usuario)` en
`apps/organizaciones.services` devuelve `True` solo si el usuario cumple
**las cuatro condiciones**:

- autenticado,
- activo,
- `is_superuser=True`,
- no es `AnonymousUser`.

**Importante:** un `is_superuser` **no** obtiene acceso automático a los
datos de una organización que no sea suya. La administración de plataforma
y el acceso operativo se comprueban por separado
(`tiene_acceso_a_organizacion`). Esto cumple §8: "no otorgar acceso a todos
los expedientes por el simple hecho de tener un rol administrativo".

## 4. Matriz de permisos por entidad implementada

Solo las 5 entidades con modelo real hoy. El símbolo `✅` indica que la
acción está implementada y verificada en código; `🟡` indica que existe
la función de verificación pero el endpoint aún no la usa; `❌` indica
que no está permitida.

### 4.1 `usuarios.Usuario`

| Acción | Anónimo | CONSULTA | OPERADOR | COORDINADOR | ADMIN_ORGANIZACION | Superusuario |
|---|---|---|---|---|---|---|
| Ver propio perfil | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Editar propio perfil | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Ver otros usuarios de su organización | ❌ | ❌ | ❌ | 🟡 | ✅ | ✅ |
| Crear usuario | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Desactivar usuario | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Ver todos los usuarios | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

### 4.2 `organizaciones.Organizacion` y `Membresia`

| Acción | Anónimo | CONSULTA | OPERADOR | COORDINADOR | ADMIN_ORGANIZACION | Superusuario |
|---|---|---|---|---|---|---|
| Ver datos públicos (nombre, tipo, contacto) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Ver todas las organizaciones | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Editar su propia organización | ❌ | ❌ | ❌ | 🟡 | ✅ | ✅ |
| Crear membresía | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Cambiar rol de membresía | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Suspender organización | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

### 4.3 `territorio.EntidadFederal` / `Municipio` / `Parroquia`

| Acción | Anónimo | CONSULTA | OPERADOR | COORDINADOR | ADMIN_ORGANIZACION | Superusuario |
|---|---|---|---|---|---|---|
| Consultar catálogo territorial | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Crear/modificar entidad territorial | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

> Catálogo administrado exclusivamente por superusuario. Los datos se
> cargan por migración o `management command` reproducible (§4.4).

### 4.4 `emergencias.Emergencia` y `ReporteEmergencia`

| Acción | Anónimo | CONSULTA | OPERADOR | COORDINADOR | ADMIN_ORGANIZACION | Superusuario |
|---|---|---|---|---|---|---|
| Listar emergencias en estado público | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Ver detalle de emergencia pública | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Enviar reporte ciudadano | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Ver emergencias en cualquier estado | ❌ | 🟡 | 🟡 | ✅ | ✅ | ✅ |
| Crear emergencia oficial | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| Cambiar estado de emergencia | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| Listar reportes pendientes | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Revisar reporte (cambiar estado) | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Vincular reporte a emergencia | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

> **Nota crítica:** la revisión de reportes ciudadanos está restringida a
> superusuario hoy (ver `servicios_revision.puede_revisar_reportes`). Cuando
> existan roles con ámbito territorial (Fase 5+), esta función se ampliará
> a `COORDINADOR` con delimitación geográfica. Documentado como pendiente.

### 4.5 `auditoria.EventoAuditoria`

| Acción | Anónimo | CONSULTA | OPERADOR | COORDINADOR | ADMIN_ORGANIZACION | Superusuario |
|---|---|---|---|---|---|---|
| Consultar auditoría general | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Consultar eventos de su organización | ❌ | ❌ | ❌ | ❌ | 🟡 | ✅ |
| Exportar auditoría | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

> **§7.5 lo exige:** el rol de auditor es distinto del rol de administrador.
> Un `ADMIN_ORGANIZACION` no debería poder leer toda la auditoría. Hoy solo
> superusuario puede. El rol `AUDITOR` se introducirá cuando se implemente
> la primera vista de lectura de auditoría (Fase 9).

## 5. Regla de organización (aislamiento entre organizaciones)

**Regla:** un usuario solo accede a datos `PER` u `OPE` de organizaciones
donde tiene membresía `ACTIVA`.

`tiene_acceso_a_organizacion(usuario, organizacion, roles_permitidos=None)`
en `apps/organizaciones.services` implementa esta regla. Devuelve `True`
solo si se cumplen **todas** las condiciones:

1. El usuario está autenticado y activo.
2. La organización existe y está en estado `ACTIVA`.
3. Existe una `Membresia` con `estado=ACTIVA` entre ambos.
4. Si se pasan `roles_permitidos`, la membresía tiene uno de esos roles.

**Corolario (§8):** un usuario **no** debe acceder a expedientes de otra
organización cambiando el UUID en la URL o el cuerpo JSON. Todos los
endpoints internos deben llamar a esta función antes de devolver o
modificar datos.

**Caso análogo:** un usuario de la organización A que conoce el UUID de
un expediente de la organización B recibe **404**, no 403. No se filtra
la existencia del recurso.

## 6. Regla de ámbito territorial

**Estado actual:** no implementada. `Membresia` no tiene campo de
región, estado o municipio. Un usuario con membresía en una organización
nacional puede operar cualquier ubicación dentro de esa organización.

**Riesgo:** en Fase 5 (refugios) esta limitación es aceptable si las
organizaciones son locales (un refugio, un hospital). En Fase 6 (pacientes)
el riesgo crece: un coordinador de salud nacional podría ver expedientes
de cualquier región.

**Mitigación adoptada hasta ahora:**
- Solo los roles `ADMIN_ORGANIZACION` y `COORDINADOR` pueden modificar
  datos. `CONSULTA` solo lee.
- Las operaciones sensibles (`revisar_reporte_interno`,
  `vincular_reporte_interno`) requieren superusuario. Ver §4.4.

**Pendiente por fase:**

- **Fase 5 (refugios):** evaluar si se añade `Membresia.ambito_territorial`
  (UUIDField nullable con referencia a `EntidadFederal`). Decisión
  bloqueante antes de implementar refugios con múltiples sedes.
- **Fase 6 (pacientes):** implementación obligatoria. El riesgo de
  filtración clínica excede el costo de complejidad.

## 7. Roles pendientes por fase

Los roles del prompt §8 que aún no existen en código, y los que se
introducirán cuando la funcionalidad lo requiera.

### Fase 5 — Refugios

| Rol | Motivo | Ámbito |
|---|---|---|
| Gestor de refugios | Administra UN refugio específico | Refugio (FK) |
| Responsable de necesidades | Registra necesidades del refugio | Refugio (FK) |

**Decisión de diseño:** **no** se añade `Membresia.ambito_territorial`
todavía. En su lugar, cada `Refugio` tendrá `responsable = ForeignKey(Usuario)`.
Roles `ADMIN_ORGANIZACION` y `COORDINADOR` editan cualquiera de su
organización; `OPERADOR` solo los asignados.

Justificación: granularidad a nivel de recurso es más simple y auditable
que granularidad geográfica. Se reevalúa en Fase 6.

### Fase 6 — Hospitales, pacientes y triaje

| Rol | Motivo | Ámbito |
|---|---|---|
| Personal sanitario | Acceso a expedientes clínicos | Hospital (FK) |
| Jefe de servicio | Supervisa un servicio | Servicio (FK) |

**Decisión de diseño:** `Membresia.ambito_territorial` se evalúa aquí
**obligatoriamente**. El riesgo de filtración clínica excede el costo
de complejidad. Se añadirá un campo `ambito_municipio` nullable con
`ForeignKey(Municipio)`. Un usuario solo verá expedientes de su
municipio o de municipios explícitamente autorizados.

### Fase 7 — Derivaciones

| Rol | Motivo | Ámbito |
|---|---|---|
| Responsable de derivaciones | Autoriza/acepta traslados | Hospital origen y destino |

**Decisión de diseño:** el flujo de autorización puede implementarse con
`tiene_acceso_a_organizacion` extendido: el usuario debe tener membresía
ACTIVA en el hospital origen, **y** el hospital destino debe aceptar
la derivación. No requiere rol especial — es control de flujo, no de
permisos.

### Fase 8 — Inventario y distribución

| Rol | Motivo | Ámbito |
|---|---|---|
| `OPERADOR` (ya existe) | Registra movimientos | Almacén (FK) |
| `LOGISTICA` (ya existe) | Autoriza transferencias | Almacén (FK) |

**Decisión de diseño:** el rol `LOGISTICA` autoriza transferencias entre
almacenes de su organización; `OPERADOR` solo registra movimientos
individuales. Sin nuevos roles.

### Fase 9 — Auditoría y reportes

| Rol | Motivo | Ámbito |
|---|---|---|
| AUDITOR | Lee auditoría (sin modificar) | Global o por organización |
| Analista de reportes | Exporta estadísticas agregadas | Global |

**Decisión de diseño (§7.5):** `AUDITOR` se implementa con un flag en
`Usuario` (`is_auditor`), **no** con `is_superuser`. Un `is_superuser`
puede todo; un `is_auditor` solo lee. La distinción es importante para
§7.5 ("no otorgar acceso a todos los expedientes por tener el rol de
auditor").

### Resumen de roles finales

Tras todas las fases, los roles de organización son:

- `ADMIN_ORGANIZACION`
- `COORDINADOR`
- `OPERADOR`
- `SANITARIO`
- `LOGISTICA`
- `CONSULTA`
- **Nuevo en Fase 5:** `GESTOR_REFUGIO` (evaluar si `responsable` basta)
- **Nuevo en Fase 6:** `JEFE_SERVICIO` (evaluar si `responsable` basta)

Roles de plataforma (**fuera** de `Membresia`, como flags en `Usuario`):

- `is_superuser` — administración técnica
- `is_auditor` — solo lectura de auditoría (Fase 9)
- Anónimo — acceso público §6.1

## 8. Reglas de aplicación en endpoints

Todo endpoint interno (bajo `/api/interno/`) debe aplicar la siguiente
secuencia antes de devolver o modificar datos:

```
1. Autenticación (¿usuario válido y activo?)
   ↓
2. Rol (¿la membresía ACTIVA concede este rol?)
   ↓
3. Organización (¿el recurso pertenece a su organización?)
   ↓
4. Ámbito (si aplica en esta fase — hoy no, Fase 6+)
   ↓
5. Estado del objeto (¿la transición es válida?)
   ↓
6. Necesidad de conocer (¿el campo es PER/CLI y el rol lo justifica?)
```

La autorización debe residir en el **backend**. Nunca en:
- El frontend (puede ser manipulado).
- El UUID enviado por el cliente.
- El `request.user` sin verificación adicional.

**Todos los endpoints internos** deben llamar a una de estas funciones
antes de operar sobre un recurso:

| Función | Cuándo usarla |
|---|---|
| `puede_administrar_plataforma(usuario)` | Operaciones globales (solo superusuario) |
| `tiene_acceso_a_organizacion(usuario, org, roles)` | Operaciones por organización |
| `puede_revisar_reportes(usuario)` | Revisión de reportes ciudadanos |

## 9. Verificación en tests

Cada regla de esta política debe tener al menos un test automatizado
que la demuestre (§18.2).

### Tests existentes

| Test | Demuestra |
|---|---|
| `apps/emergencias/tests.py::test_solo_estados_publicos` | §4.4: solo `CONFIRMADA`, `EN_ATENCION`, `RESUELTA` son públicos |
| `apps/emergencias/tests.py::test_no_expone_campos_prohibidos` | §4.4 + §6.2: `reportada_por` y `organizacion` no aparecen |
| `apps/emergencias/tests.py::test_detalle_no_verificado_devuelve_404` | §5: no filtra existencia de no públicos |
| `apps/auditoria/tests.py::test_no_update_instance` | §7.3: auditoría inmutable |
| `apps/auditoria/tests.py::test_no_delete_instance` | §7.3: auditoría inmutable |

### Tests pendientes por fase

| Fase | Test a implementar |
|---|---|
| 5 (refugios) | `test_operador_no_accede_refugio_de_otra_org` |
| 5 (refugios) | `test_gestor_solo_edita_su_refugio` |
| 6 (pacientes) | `test_sanitario_no_ve_expediente_de_otro_municipio` |
| 6 (pacientes) | `test_consulta_no_accede_datos_clinicos` |
| 6 (pacientes) | `test_superuser_puede_administrar_pero_no_lee_expedientes_automaticamente` |
| 7 (derivaciones) | `test_responsable_origen_autoriza_destino_confirma` |
| 8 (inventario) | `test_operador_no_autoriza_transferencia` |
| 9 (auditoría) | `test_auditor_lee_pero_no_modifica` |

## 10. Referencias

- Prompt maestro §6.2, §6.5, §7, §8, §17, §18.2.
- `docs/privacy-and-retention.md` — clasificación de sensibilidad.
- `docs/data-dictionary.md` — permisos por campo (columna `Permisos`).
- `docs/api.md` — endpoints públicos (sin autenticación).
- `apps/organizaciones/services.py` — funciones `puede_administrar_plataforma`
  y `tiene_acceso_a_organizacion`.
- `apps/emergencias/servicios_revision.py` — función `puede_revisar_reportes`.

## 11. Pendientes de este documento

- [ ] Implementar rol `AUDITOR` con flag `is_auditor` en `Usuario` (Fase 9).
- [ ] Decidir si `Membresia.ambito_territorial` se añade en Fase 5 o Fase 6.
- [ ] Evaluar si `responsable = ForeignKey(Usuario)` en `Refugio`/`Hospital`
      reemplaza la necesidad de nuevos roles `GESTOR_REFUGIO`/`JEFE_SERVICIO`.
- [ ] Documentar la regla de acceso excepcional de emergencia
      (§6.5) cuando se implemente el modo extraordinario.
- [ ] Añadir los 8 tests pendientes de §9 al cerrar cada fase.
