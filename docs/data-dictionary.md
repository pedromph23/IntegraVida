# Diccionario de datos — IntegraVida

> Clasificación: `PUB` público / `OPE` operativo / `PER` personal / `CLI` clínico / `SEC` secreto / `AUD` auditoría.
> Los campos `TBD` requieren revisión antes de exponer API pública (§6.3).

## 1. `usuarios.Usuario`

| Campo | Tipo | Oblig. | Restricciones | Clasif. | Auditoría | Validación |
|---|---|---|---|---|---|---|
| id | UUID | Sí | PK | OPE | No | — |
| username | CharField(150) | Sí | Único | SEC | Login | Django auth |
| email | EmailField | No | — | PER | Cambios | Email válido |
| first_name | CharField | No | — | PER | Cambios | — |
| last_name | CharField | No | — | PER | Cambios | — |
| is_active | Boolean | Sí | — | OPE | Sí | — |
| is_staff | Boolean | Sí | — | SEC | Sí | — |
| date_joined | DateTimeField | Sí | — | OPE | — | — |
| password | CharField | Sí | hash | SEC | **Nunca** | Nunca en logs |

## 2. `organizaciones.Organizacion`

| Campo | Tipo | Oblig. | Restricciones | Clasif. | Auditoría |
|---|---|---|---|---|---|
| id | UUID | Sí | PK | OPE | Sí |
| nombre | CharField(180) | Sí | — | PUB | Sí |
| tipo | CharField(30) | Sí | TextChoices | PUB | Sí |
| estado | CharField | Sí | TextChoices | OPE | Sí |
| telefono_publico | CharField(30) | No | — | PUB | Sí |

## 3. `organizaciones.Membresia`

| Campo | Tipo | Oblig. | Restricciones | Clasif. | Auditoría |
|---|---|---|---|---|---|
| id | UUID | Sí | PK | OPE | Sí |
| usuario | FK Usuario | Sí | — | PER | Sí |
| organizacion | FK Organizacion | Sí | — | OPE | Sí |
| rol | CharField(25) | Sí | TextChoices | OPE | Sí |
| estado | CharField | Sí | TextChoices | OPE | Sí |

> **Constraint pendiente:** `UniqueConstraint(usuario, organizacion, rol)`.

## 4. `territorio.EntidadFederal`

| Campo | Tipo | Oblig. | Restricciones | Clasif. |
|---|---|---|---|---|
| id | UUID | Sí | PK | PUB |
| nombre | CharField(120) | Sí | — | PUB |
| codigo | CharField(20) | Sí | **UNIQUE** | PUB |
| tipo | CharField(25) | Sí | TextChoices | PUB |

## 5. `territorio.Municipio`

| Campo | Tipo | Oblig. | Restricciones | Clasif. |
|---|---|---|---|---|
| id | UUID | Sí | PK | PUB |
| entidad_federal | FK EntidadFederal | Sí | — | PUB |
| nombre | CharField(150) | Sí | — | PUB |
| codigo | CharField(30) | Sí | Único por estado | PUB |

> **Constraint pendiente:** `UniqueConstraint(entidad_federal, codigo)`.

## 6. `territorio.Parroquia`

| Campo | Tipo | Oblig. | Restricciones | Clasif. |
|---|---|---|---|---|
| id | UUID | Sí | PK | PUB |
| municipio | FK Municipio | Sí | — | PUB |
| nombre | CharField(150) | Sí | — | PUB |
| codigo | CharField(30) | Sí | Único por municipio | PUB |

> **Constraint pendiente:** `UniqueConstraint(municipio, codigo)`.

## 7. `emergencias.Emergencia`

| Campo | Tipo | Oblig. | Restricciones | Clasif. | Auditoría |
|---|---|---|---|---|---|
| id | UUID | Sí | PK | OPE | Sí |
| titulo | CharField(180) | Sí | — | OPE | Sí |
| categoria | CharField | Sí | TextChoices | OPE | Sí |
| gravedad | Integer | Sí | IntegerChoices | OPE | Sí |
| estado | CharField | Sí | TextChoices | OPE | Sí |
| ubicacion_texto | CharField(300) | Sí | — | TBD | Sí |
| referencia_lugar | CharField(250) | No | — | TBD | Sí |
| punto | PointField | No | SRID 4326 | TBD | Sí |
| municipio | FK Municipio | TBD | — | PUB | Sí |
| parroquia | FK Parroquia | TBD | — | PUB | Sí |
| reportada_por | FK Usuario | TBD | — | PER | Sí |
| organizacion | FK Organizacion | TBD | — | OPE | Sí |

> **Validación pendiente:** coherencia `municipio.entidad_federal` ↔ `parroquia.municipio` en `clean()` y `CheckConstraint` si viable.

## 8. `emergencias.ReporteEmergencia`

| Campo | Tipo | Oblig. | Restricciones | Clasif. | Auditoría |
|---|---|---|---|---|---|
| id | UUID | Sí | PK | OPE | Sí |
| emergencia | FK Emergencia | Sí | — | OPE | Sí |
| reportante | FK Usuario | No | — | PER | Sí |
| categoria | CharField | Sí | TextChoices | OPE | Sí |
| ubicacion_texto | CharField(300) | Sí | — | TBD | Sí |
| referencia_lugar | CharField(250) | No | — | TBD | Sí |
| punto | PointField | No | SRID 4326 | TBD | Sí |
| municipio | FK Municipio | TBD | — | PUB | Sí |
| parroquia | FK Parroquia | TBD | — | PUB | Sí |
| canal | CharField | Sí | TextChoices | OPE | Sí |
| estado_revision | CharField | Sí | TextChoices | OPE | Sí |

## 9. `auditoria.EventoAuditoria`

| Campo | Tipo | Oblig. | Restricciones | Clasif. | Auditoría |
|---|---|---|---|---|---|
| id | UUID | Sí | PK | AUD | — |
| actor | FK Usuario | Sí | — | AUD | — |
| organizacion_id | UUIDField | No | **Sin FK** | AUD | — |
| accion | CharField(100) | Sí | — | AUD | — |
| tipo_objeto | CharField(100) | No | — | AUD | — |
| objeto_id | CharField(100) | No | — | AUD | — |
| resultado | CharField | Sí | TextChoices | AUD | — |
| justificacion | CharField(500) | No | — | AUD | — |
| agente_usuario | CharField(500) | No | — | AUD | — |
| id_correlacion | CharField(100) | No | — | AUD | — |

> **Faltantes (§7.3) — tarea de Fase 3:** `fecha_hora` (TIMESTAMPTZ), `ip_origen`, `hash_anterior`, `hash_actual`. Sin ellos no hay defensa contra alteración.
> **Decisión pendiente:** `organizacion_id` sin FK — convertir a `ForeignKey(Organizacion, null=True, on_delete=PROTECT)` o justificar el UUIDField.
