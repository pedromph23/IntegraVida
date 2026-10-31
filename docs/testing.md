# Estrategia de Pruebas — IntegraVida

> **Estado:** documentado al cierre de Fase 10.4.
> **Cifra actual:** 241 tests automatizados, todos verdes.

## 1. Principios

1. **Pruebas desde el inicio** (§18). Cada módulo nuevo trae tests en
   el mismo commit que el código.
2. **Cobertura por riesgo**, no por métrica.
3. **Tests que demuestran §18.2 y §18.3**: aislamiento entre
   organizaciones y atomicidad de operaciones críticas.
4. **Sin datos reales** en fixtures o tests.
5. **Los tests preceden al commit** (§3.8).

## 2. Distribución de los 241 tests

| App | Tests | Cubre |
|---|---|---|
| `usuarios` | 4 | Creación, unicidad email condicional |
| `organizaciones` | 13 | Membresías, ámbitos, roles |
| `auditoria` | 7 | Hash encadenado, inmutabilidad |
| `emergencias` | 12 | Portal público, reportes ciudadanos |
| `refugios` | 25 | Modelo, servicio, portal público |
| `hospitales` | 31 | Modelo, recursos, servicios, portal |
| `pacientes` | 23 | Paciente, episodio, cedula_hash |
| `triaje` | 15 | Triaje, reevaluación, ámbito |
| `derivaciones` | 13 | Flujo completo, transiciones |
| `inventario` | 52 | Catálogo, stock, kardex, transferencia, entrega |
| `reportes` | 12 | Reportes operativos, RegistroExportacion |
| `configuracion` | 34 | ReferenciaMigracion, integridad, migración |

## 3. Categorías de tests

### 3.1 Modelo

Restricciones, `__str__`, properties, UniqueConstraint, CheckConstraint,
`clean()`. Ejemplos: `test_codigo_unico`,
`test_check_disponible_le_capacidad_db`, `test_origen_igual_destino_falla`.

### 3.2 Servicio (transaccionalidad §10)

- `test_salida_sin_stock_falla`
- `test_despacho_sin_stock_falla`
- `test_recibir_cancelada_falla`

### 3.3 Concurrencia (§18.3)

`TransactionTestCase` + `ThreadPoolExecutor`:

- `test_dos_salidas_simultaneas_no_dejan_stock_negativo`
- `test_entrada_y_salida_simultaneas_conservan_consistencia`
- `test_dos_aceptaciones_simultaneas_solo_una_pasa`

**Nota técnica:** cada worker cierra su `connection` en `finally`, y
`tearDown()` llama `connections.close_all()`. Sin esto, PostgreSQL
lanza `ObjectInUse` al dropear la DB de test.

### 3.4 Permisos (§18.2)

- `test_usuario_a_no_ve_episodios_de_org_b`
- `test_usuario_restringido_solo_ve_su_municipio`
- `test_superuser_sin_membresia_no_accede_por_ambito` (§7.5)
- `test_usuario_de_org_a_no_puede_solicitar_derivacion_de_org_b`

### 3.5 Portal público (§18.1)

- `test_solo_estados_publicos`
- `test_no_expone_campos_prohibidos`
- `test_anonymo_401`
- `test_post_sin_csrf_funciona`

### 3.6 Auditoría (§7.3)

- `test_primer_evento_usa_genesis`
- `test_cadena_secuencial`
- `test_no_update_instance` / `test_no_delete_instance`
- `test_no_manager_update` / `test_no_manager_delete`

### 3.7 Migración (§16.1)

- `test_idempotencia_no_duplica`
- `test_hash_origen_se_guarda`
- `test_mapeo_medico_a_medicina_con_vencimiento`

## 4. Lo que NO se testea (y por qué)

| Aspecto | Razón |
|---|---|
| Migración de datos reales | Fase 11 (requiere autorización) |
| Interfaz HTML | No hay frontend HTML |
| Envío de emails reales | `EMAIL_BACKEND=console` en dev |
| Cifrado AES de campos CLI | Diferido a Fase 11 |
| Rate limiting distribuido | Cache en memoria |
| Cobertura del 100% | Cobertura por riesgo |

## 5. Cómo ejecutar

Todos los tests:

    python3 manage.py test

Una app:

    python3 manage.py test apps.inventario

Un archivo:

    python3 manage.py test apps.configuracion.tests_integridad

Regresión completa de apps críticas:

    python3 manage.py test apps.configuracion apps.reportes apps.inventario \
        apps.derivaciones apps.usuarios apps.triaje apps.organizaciones \
        apps.pacientes apps.hospitales apps.refugios apps.emergencias apps.auditoria

## 6. Limitaciones conocidas

- Sin prueba de restauración de backups (Fase 11).
- Sin prueba de carga (volumen <100 ops/min esperado).
- Sin prueba de disaster recovery (Fase 11).
- Sin prueba E2E de navegador (no hay frontend HTML).
- `TransactionTestCase` es lento (~17s vs 3s). Solo se usa en 3 tests.
