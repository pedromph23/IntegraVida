# Arquitectura — IntegraVida

> **Estado:** sistema operativo, 12 apps, ~50 modelos, 246 tests.
> **Metodología:** monolito modular Django + PostgreSQL 17 + PostGIS 3.5.

## 1. Principios de diseño

1. **Monolito modular.** No hay microservicios. Cada app Django tiene
   responsabilidad clara y se comunica por imports Python, no por HTTP.
2. **Coherencia relacional.** FKs explícitas con `PROTECT` en todos los
   modelos. `on_delete=CASCADE` solo donde se justifica.
3. **Auditoría inmutable.** Todo evento crítico pasa por
   `auditoria.services.registrar_evento()` con hash SHA-256 encadenado.
4. **Kardex inmutable.** Movimientos de inventario no se modifican;
   correcciones vía `AJUSTE` compensatorio.
5. **Cifrado de PII/CLI.** Campos sensibles de Paciente cifrados con
   Fernet a nivel de campo.
6. **Separación de privilegios PG.** `integravida_app` (DML limitado) vs
   `integravida_migrator` (DDL).
7. **Acceso público sin registro.** 7 endpoints `AllowAny` explícitos
   para información PUB.
8. **Aislamiento por organización + ámbito municipal.** Membresías
   activas determinan qué recursos son visibles.

## 2. Stack

| Capa | Tecnología | Versión |
|---|---|---|
| Lenguaje | Python | 3.13.5 |
| Framework | Django | 6.1.2 |
| API REST | Django REST Framework | ≥3.16 |
| Base de datos | PostgreSQL | 17.11 |
| Geoespacial | PostGIS | 3.5.2 |
| Geo-Django | GeoDjango (GDAL 3.10.3) | — |
| Cifrado campo | cryptography (Fernet) | 50.0.2 |
| Driver DB | psycopg | 3.3.6 |
| Servidor WSGI | Gunicorn (producción) | — |

## 3. Estructura de apps

    apps/
    ├── usuarios/         Custom User (UUID, email condicional)
    ├── organizaciones/   Organizacion, Membresia (roles + ámbito)
    ├── territorio/       EntidadFederal → Municipio → Parroquia
    ├── auditoria/        EventoAuditoria (hash encadenado)
    ├── emergencias/      Emergencia, ReporteEmergencia + portal público
    ├── refugios/         Refugio, Necesidad, RegistroOcupacion
    ├── hospitales/       Hospital, Servicio, RecursoHospitalario
    ├── pacientes/        Paciente (cifrado), Episodio, ContactoEmergencia
    ├── triaje/           Triaje (ROJO/AMARILLO/VERDE)
    ├── derivaciones/     Derivacion, TransicionEstado
    ├── inventario/       Insumo, Almacen, Lote, Stock, Movimiento,
    │                     Transferencia, Entrega
    ├── reportes/         RegistroExportacion + 2 reportes operativos
    └── configuracion/    ReferenciaMigracion + management commands

## 4. Capas por app

Cada app sigue el patrón:

    <app>/
    ├── models.py       Modelos + constraints + properties
    ├── services.py     Operaciones transaccionales complejas
    ├── views.py        Endpoints HTTP (públicos o internos)
    ├── urls.py         Rutas
    ├── admin.py        Admin con inlines readonly donde aplica
    ├── tests.py        Tests del modelo + servicio
    ├── tests_<tema>.py Tests específicos por tema
    └── migrations/     Versionadas

**Regla:** lógica de negocio va en `services.py`, no en vistas ni modelos.
Los modelos solo garantizan integridad estructural (constraints, clean).

## 5. Flujos end-to-end

### 5.1 Portal público

    Ciudadano (sin cuenta)
      → GET /api/publico/emergencias/?q=...
      → Filtra estados públicos (CONFIRMADA/EN_ATENCION/RESUELTA)
      → Serializa solo campos PUB
      → Response JSON

### 5.2 Reporte ciudadano

    Ciudadano (sin cuenta)
      → POST /api/publico/emergencias/reportes/ (JSON, CSRF exempt)
      → recibir_reporte_publico() valida + rate limit por IP
      → ReporteEmergencia estado=PENDIENTE
      → EventoAuditoria (hash encadenado)
      → Response 201 con reporte_id

### 5.3 Derivación hospitalaria

    Sanitario de Org A
      → solicitar_derivacion() (select_for_update)
      → Valida ámbito + prioridad vs triaje vigente
      → Derivacion BORRADOR
      → transicionar_derivacion() xN (máquina de estados)
      → EventoAuditoria por cada transición
      → TransicionEstado por cada transición

### 5.4 Movimiento de inventario

    Operador de Org A
      → registrar_movimiento() (select_for_update sobre Stock)
      → Valida cantidad >= 0 resultante
      → Actualiza Stock.cantidad
      → Crea Movimiento (inmutable)
      → EventoAuditoria

### 5.5 Transferencia entre almacenes

    Logística de Org A
      → crear_transferencia() → BORRADOR
      → transicionar_transferencia(APROBADA)
      → despachar_transferencia() → EN_TRANSITO
        → fail-fast: valida stock de todas las líneas
        → registrar_movimiento(TRANSFERENCIA_SALIDA) x línea
      → recibir_transferencia() → RECIBIDA
        → registrar_movimiento(TRANSFERENCIA_ENTRADA) x línea
        → get_or_create Stock destino

## 6. Modelo de datos resumido

- **Usuarios** → **Membresías** → **Organizaciones** (roles + ámbito).
- **Territorio** (EntidadFederal → Municipio → Parroquia) como catálogo.
- **Emergencias** con GeoDjango `PointField`.
- **Refugios** con capacidad/ocupación transaccional.
- **Hospitales** con recursos (UCI/urgencia/quirofano) y servicios M2M.
- **Pacientes** (cifrado) → **Episodios** (hospital XOR refugio) → **Triajes**.
- **Derivaciones** con máquina de estados.
- **Inventario** completo: Insumo → Lote → Stock → Movimiento (kardex).

## 7. Seguridad

| Capa | Implementación |
|---|---|
| Secretos | `.env` fuera de Git, `DJANGO_SECRET_KEY` obligatorio |
| Cifrado campo | Fernet (AES-128-CBC + HMAC) sobre PII/CLI de Paciente |
| Cifrado transporte | HTTPS + HSTS en producción (`if not DEBUG`) |
| Privilegios PG | `app` (DML) vs `migrator` (DDL) |
| Auditoría | SHA-256 encadenado, ORM inmutable, PG sin UPDATE/DELETE |
| Rate limiting | IP-based para reportes ciudadanos (60s window) |
| CSRF | Exempt solo en endpoints públicos JSON |

## 8. Despliegue

- **Local:** WSL2 + Debian 13 + PostgreSQL 17 local + PostGIS.
- **Producción:** pendiente de elegir proveedor (ver `docs/deployment.md`).
- **Backups:** `pg_dump -F c` diario + SHA-256 + rotación 30 días.
- **Restauración:** probada end-to-end con `-L` filtrada.

## 9. Testing

- **246 tests** automatizados.
- **Concurrencia:** `TransactionTestCase` + `ThreadPoolExecutor`.
- **Migración:** fixtures sintéticos idempotentes.
- **Integridad:** verificación de cadena de auditoría sobre backup restaurado.

Ver `docs/testing.md` para detalle.

## 10. Deuda técnica conocida

| Item | Fase de resolución |
|---|---|
| `Usuario.email` unique condicional | ✅ Resuelto en 6.3.1 |
| `EPISODIO` requiere hospital XOR refugio | ✅ Resuelto en 6.2 |
| Cifrado de `cedula` permitía búsqueda por hash | ✅ Resuelto en 11.1 |
| Roles PG app vs migrator | ✅ Resuelto en 11.2 |
| Backup/restore probado | ✅ Resuelto en 11.3 |
| Deployment real en proveedor | Pendiente autorización |
| Migración de datos reales | Pendiente autorización §16.1 |
| Dashboard HTML | Fase 9.5 (opcional) |

## 11. Referencias

- `docs/deployment.md` — procedimiento de deployment.
- `docs/operations.md` — runbook + backups.
- `docs/audit-and-security.md` — §7.3.
- `docs/privacy-and-retention.md` — §11.
- `docs/data-dictionary.md` — 35+ entidades.
- `docs/entity-relationship.md` — diagrama Mermaid.
- `docs/api.md` — contrato público + interno.
- `docs/testing.md` — estrategia de pruebas.
- `docs/migration-plan.md` — plan de migración desde repos origen.
- `docs/analisis-origen.md` — hallazgos de los 3 repos.
- `docs/permissions.md` — matriz de roles.
