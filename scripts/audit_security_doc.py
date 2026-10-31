#!/usr/bin/env python3
"""Escribe docs/audit-and-security.md (Fase 5 prerequisito §7.5)."""
from pathlib import Path
import sys

BASE = Path.cwd()
if not (BASE / "manage.py").exists():
    sys.exit("ERROR: ejecutar desde ~/proyectos/integravida")

BT = chr(96) * 3   # bloque de código Markdown
B = chr(96)        # backtick simple

doc = """# Política de Auditoría y Seguridad — IntegraVida

> Documento exigido por §7.5 y §23. **Estado:** parcial — describe la
> implementación actual de auditoría y las políticas operativas asociadas.
> Se actualizará cuando se implemente el rol AUDITOR (Fase 9).

## 1. Principios

1. **Inmutabilidad verificable.** Un evento de auditoría no se puede
   modificar ni borrar sin dejar rastro criptográfico (§7.3).
2. **Trazabilidad criptográfica.** Cadena SHA-256 encadenada, sin
   bifurcaciones posibles.
3. **Confidencialidad del registro.** No registrar contraseñas, tokens,
   cookies ni secretos (§7.2).
4. **Separación de privilegios.** El usuario de aplicación no puede
   alterar la tabla de auditoría (§7.3).
5. **Defensa en profundidad.** Modelo + manager + constraint + advisory
   lock + tests. Ningún mecanismo individual se considera suficiente.

## 2. Implementación actual

### 2.1 Modelo EVENTO_AUDITORIA

Archivo: APPS/AUDITORIA/MODELS.PY

Campos relevantes:

| Campo | Propósito |
|---|---|
| ID | UUID, PK |
| OCURRIDO_EN | TIMESTAMPTZ, indexado |
| ACTOR | FK USUARIO, on_delete=PROTECT |
| ACCION | VARCHAR(100), indexado |
| TIPO_OBJETO + OBJETO_ID | Identificación del recurso afectado |
| RESULTADO | EXITOSO / DENEGADO / ERROR |
| DIRECCION_IP | INET (IPv4 o IPv6) |
| METADATOS | JSONB (contexto adicional, sin datos sensibles) |
| HASH_ANTERIOR | VARCHAR(64), UNIQUE, index |
| HASH_ACTUAL | VARCHAR(64), UNIQUE, index |

### 2.2 Inmutabilidad

Tres capas de bloqueo:

1. **Modelo**: EVENTO_AUDITORIA.SAVE() lanza NOTALLOWED si no es creación.
   DELETE() siempre lanza NOTALLOWED.
2. **QuerySet**: EVENTOAUDITORIAQUERYSET.UPDATE() y DELETE() lanzan
   NOTALLOWED.
3. **Manager**: hereda del QuerySet, misma protección.

Ningún camino de Django ORM permite modificar un evento existente.

### 2.3 Hash encadenado

Función CALCULAR_HASH(EVENTO) en APPS/AUDITORIA/MODELS.PY:

- Serializa un payload canónico (JSON con SORT_KEYS y separadores fijos).
- Incluye HASH_ANTERIOR en el payload.
- Usa SHA-256.
- Resultado en HASH_ACTUAL.

El primer evento de la cadena usa HASH_GENESIS = "0000...0000" (64 ceros)
como HASH_ANTERIOR.

**Verificación:** para cada evento N, HASH_ANTERIOR == HASH_ACTUAL del
evento N-1 (verificado en TESTS.PY::TEST_CADENA_SECUENCIAL).

**Limitación documentada:** si dos eventos tienen el mismo OCURRIDO_EN
al microsegundo, el orden en la cadena se resuelve por el advisory lock
(§2.4), no por el timestamp. Si en el futuro se detecta ambigüedad,
añadir campo SECUENCIA monotónico.

### 2.4 Atomicidad y concurrencia

Servicio REGISTRAR_EVENTO() en APPS/AUDITORIA/SERVICES.PY:

- Dentro de TRANSACTION.ATOMIC().
- Toma PG_ADVISORY_XACT_LOCK con clave fija (0x41554449 = "AUDI").
- Lee el último HASH_ACTUAL, lo usa como HASH_ANTERIOR.
- Calcula y persiste el nuevo evento.
- El lock se libera al commit o rollback automáticamente.

**Consecuencia:** las inserciones de auditoría se serializan globalmente.
Aceptable para volumen humanitario (decenas/segundo). Si el volumen
crece, evaluar sharding por ORGANIZACION_ID con claves de lock distintas.

### 2.5 Tests

APPS/AUDITORIA/TESTS.PY contiene 7 tests:

| Test | Demuestra |
|---|---|
| TEST_PRIMER_EVENTO_USA_GENESIS | Genesis correcto |
| TEST_CADENA_SECUENCIAL | Encadenamiento N-1 → N |
| TEST_HASH_DETERMINISTA | Mismo payload → mismo hash |
| TEST_NO_UPDATE_INSTANCE | SAVE() sobre existente falla |
| TEST_NO_DELETE_INSTANCE | DELETE() falla |
| TEST_NO_MANAGER_UPDATE | QUERYSET.UPDATE() falla |
| TEST_NO_MANAGER_DELETE | QUERYSET.DELETE() falla |

## 3. Política de retención (§7.5)

| Evento | Retención mínima | Acción al vencer |
|---|---|---|
| Auditoría general | 2 años | Archivar en almacenamiento inmutable |
| Auditoría de datos clínicos | Plazo legal sanitario | Archivar |
| Eventos de seguridad | 2 años | Archivar |
| Acceso extraordinario (§6.5) | 3 años | Archivar con revisión |

**Prohibición:** nunca borrar eventos individuales. Solo archivado masivo
por política, con justificación registrada.

## 4. Separación de privilegios en la BD

**Requisito:** el usuario POSTGRES de la aplicación (`INTEGRAVIDA`) no
debe poder ejecutar `DROP`, `ALTER` ni `TRUNCATE` sobre
`AUDITORIA_EVENTOAUDITORIA`.

**Estado actual:** el usuario tiene permisos DDL porque es el dueño de la
base (Django lo necesita para migraciones). **Pendiente para producción:**

1. Crear rol `INTEGRAVIDA_MIGRATOR` (dueño de tablas, usado solo en
   migraciones).
2. Crear rol `INTEGRAVIDA_APP` (usuario operativo, solo SELECT/INSERT/
   UPDATE/DELETE en tablas operativas, solo SELECT/INSERT en auditoría).
3. Configurar Django con `INTEGRAVIDA_APP` en runtime.
4. Ejecutar migraciones con `INTEGRAVIDA_MIGRATOR`.

Esto se implementa en Fase 11 (despliegue).

## 5. Backups y restauración (§7.3)

**Política:**

- Backup diario de `INTEGRAVIDA_DB` con `PG_DUMP`.
- Backup semanal completo (incluye auditoría) cifrado con GPG.
- Almacenamiento separado del servidor de aplicación.
- Retención: 30 días para diarios, 1 año para semanales.

**Pruebas de restauración:** obligatorias mensualmente. Restaurar en
entorno aislado y verificar:

1. Count de eventos de auditoría coincide con el original.
2. HASH_ACTUAL del último evento es idéntico al respaldado.
3. La cadena de hashes se verifica correctamente de extremo a extremo.

**Script de verificación:** pendiente de escribir en
`scripts/verify_audit_chain.py` (Fase 10).

## 6. Acceso al módulo de auditoría (§7.5)

**Estado actual:** solo `IS_SUPERUSER=True` puede consultar auditoría.
No hay rol `AUDITOR` separado (documentado en
`docs/permissions.md` §4.5).

**Fase 9 implementará:**

- Campo `IS_AUDITOR` (BooleanField) en `USUARIO`.
- Permiso de lectura sobre `EVENTO_AUDITORIA` sin permiso de escritura.
- Posibilidad de limitar por organización (filtro `ORGANIZACION_ID`).

**Regla:** un AUDITOR no accede a expedientes clínicos por tener el rol.
Solo lee eventos de auditoría. Para leer un expediente, debe tener
además permisos operativos sobre ese recurso (§7.5).

## 7. Gestión de incidentes de auditoría (§7.4)

**Si `REGISTRAR_EVENTO` falla:**

- La transacción completa hace rollback.
- El llamador recibe la excepción.
- El cliente HTTP recibe 500.
- Se registra en logs de aplicación (ERROR).
- No se silencia nunca.

**Si se detecta alteración de la cadena:**

1. Detener operaciones de escritura sobre auditoría.
2. Notificar al responsable de seguridad.
3. Comparar con backup más reciente.
4. Reconstruir cadena desde el último evento íntegro conocido.
5. Documentar el incidente en `docs/incidents/YYYY-MM-DD-audit.md`.

**Si `PG_ADVISORY_XACT_LOCK` falla (deadlock):**

- PostgreSQL aborta la transacción.
- Django reintenta si `ATOMIC_REQUESTS=False` (configurado así hoy).
- Si persiste, es señal de saturación. Escalar.

## 8. Qué NO se registra (§7.2)

Explícitamente **prohibido** en `METADATOS`:

- Contraseñas o hashes de contraseñas.
- Tokens de sesión o JWT.
- Cookies (ni nombres ni valores).
- Claves privadas o secretos MFA.
- Números de tarjeta o datos financieros.
- Diagnósticos médicos completos.
- Nombres completos de pacientes.
- Números de cédula completos.

Si un flujo necesita registrar algo de esto, debe enmascararse
(ej. últimos 4 dígitos) o usar un campo específico en un modelo operativo,
no en auditoría.

## 9. Referencias

- Prompt maestro §7 (todos), §6.5, §11, §26.
- `apps/auditoria/models.py` — modelo y calcular_hash
- `apps/auditoria/services.py` — registrar_evento
- `apps/auditoria/tests.py` — 7 tests
- `docs/permissions.md` §4.5 — acceso a auditoría
- `docs/privacy-and-retention.md` — retención de datos sensibles

## 10. Pendientes

- [ ] Script `verify_audit_chain.py` para verificar cadena completa
      (Fase 10).
- [ ] Rol `INTEGRAVIDA_APP` vs `INTEGRAVIDA_MIGRATOR` (Fase 11).
- [ ] Campo `is_auditor` en Usuario + rol AUDITOR (Fase 9).
- [ ] Documento `docs/incidents/` con template de post-mortem.
- [ ] Prueba de restauración mensual documentada.
- [ ] Evaluar sharding por organización si volumen supera 100 eventos/min.
- [ ] Campo `secuencia` monotónico si se detecta ambigüedad de orden.
"""

p = BASE / "docs/audit-and-security.md"
p.write_text(doc, encoding="utf-8")
print(f"escrito: {p} ({len(doc)} chars)")
print(f"lineas: {len(doc.splitlines())}")
print(f"secciones '## ': {sum(1 for l in doc.splitlines() if l.startswith('## '))}")
