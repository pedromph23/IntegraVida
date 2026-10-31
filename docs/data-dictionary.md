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
| ocurrido_en | DateTimeField | Sí | default=now, index | AUD | — |
| actor | FK Usuario | No | on_delete=**PROTECT** | AUD | — |
| organizacion_id | UUIDField | No | index (sin FK) | AUD | — |
| accion | CharField(100) | Sí | index | AUD | — |
| tipo_objeto | CharField(100) | No | — | AUD | — |
| objeto_id | CharField(100) | No | — | AUD | — |
| resultado | CharField(10) | Sí | TextChoices (EXITOSO/DENEGADO/ERROR) | AUD | — |
| justificacion | CharField(500) | No | — | AUD | — |
| direccion_ip | GenericIPAddressField | No | — | AUD | — |
| agente_usuario | CharField(500) | No | — | AUD | — |
| id_correlacion | CharField(100) | No | index | AUD | — |
| metadatos | JSONField | No | default=dict | AUD | — |
| hash_anterior | CharField(64) | Sí | **UNIQUE**, index | AUD | — |
| hash_actual | CharField(64) | Sí | **UNIQUE**, index | AUD | — |

> **Implementado en Fase 3 (commit `ec0accc`):** hash SHA-256 encadenado (§7.3),
> inmutabilidad a nivel de modelo y manager, escritura atómica vía
> `apps.auditoria.services.registrar_evento()` con `pg_advisory_xact_lock`.
> **7 tests** cubren: genesis, cadena secuencial, determinismo del hash,
> bloqueo de `update()`/`delete()` en instancia y en manager.
> **Pendiente:** decisión sobre `organizacion_id` (UUIDField vs FK);
> `docs/audit-and-security.md` con política completa (§7.5).

## 10. `refugios.Refugio`

| Campo | Tipo | Oblig. | Restricciones | Clasif. | Auditoría |
|---|---|---|---|---|---|
| id | UUID | Sí | PK | OPE | — |
| codigo | SlugField(100) | Sí | **UNIQUE** | PUB | Sí |
| nombre | CharField(200) | Sí | — | PUB | Sí |
| tipo | CharField(25) | Sí | TextChoices | PUB | Sí |
| organizacion | FK Organizacion | Sí | on_delete=PROTECT | OPE | Sí |
| responsable | FK Usuario | No | on_delete=PROTECT | OPE | Sí |
| ubicacion | PointField | No | SRID 4326 | PUB | Sí |
| direccion | CharField(300) | Sí | — | PUB | Sí |
| referencia_lugar | CharField(250) | No | — | PUB | Sí |
| municipio | FK Municipio | No | on_delete=PROTECT | PUB | Sí |
| parroquia | FK Parroquia | No | on_delete=PROTECT | PUB | Sí |
| capacidad_total | PositiveInteger | Sí | default=0 | PUB | Sí |
| ocupacion_actual | PositiveInteger | Sí | default=0, <= capacidad_total | OPE | Sí |
| servicios | JSONField | No | default=list | PUB | Sí |
| estado_operativo | CharField(20) | Sí | TextChoices, index | PUB | Sí |
| telefono_publico | CharField(30) | No | — | PUB | Sí |
| correo_publico | EmailField | No | — | PUB | Sí |
| notas_internas | TextField | No | — | OPE | Sí |
| creado_en | DateTimeField | Sí | auto_now_add | OPE | — |
| actualizado_en | DateTimeField | Sí | auto_now | OPE | — |

> **CheckConstraint:** `ocupacion_actual <= capacidad_total`.
> **`capacidad_disponible`** es una property calculada, **no** una columna.
> Imposible que se desincronice.

## 11. `refugios.Necesidad`

| Campo | Tipo | Oblig. | Restricciones | Clasif. | Auditoría |
|---|---|---|---|---|---|
| id | UUID | Sí | PK | OPE | — |
| refugio | FK Refugio | Sí | on_delete=PROTECT | OPE | Sí |
| categoria | CharField(20) | Sí | TextChoices | PUB | Sí |
| descripcion | TextField | Sí | — | OPE | Sí |
| prioridad | PositiveSmallInt | Sí | 1-4 (IntegerChoices) | PUB | Sí |
| cantidad_estimada | CharField(100) | No | — | PUB | Sí |
| cubierta | Boolean | Sí | default=False, index | PUB | Sí |
| cubierta_en | DateTimeField | No | — | OPE | Sí |
| creada_en | DateTimeField | Sí | auto_now_add | OPE | — |
| actualizada_en | DateTimeField | Sí | auto_now | OPE | — |

## 12. `refugios.RegistroOcupacion`

| Campo | Tipo | Oblig. | Restricciones | Clasif. | Auditoría |
|---|---|---|---|---|---|
| id | UUID | Sí | PK | OPE | — |
| refugio | FK Refugio | Sí | on_delete=PROTECT | OPE | Sí |
| cantidad_anterior | PositiveInt | Sí | — | OPE | Sí |
| cantidad_nueva | PositiveInt | Sí | — | OPE | Sí |
| diferencia | Integer | Sí | puede ser negativo | OPE | Sí |
| fuente | CharField(15) | Sí | MANUAL/IMPORTACION/AJUSTE | OPE | Sí |
| notas | TextField | No | — | OPE | Sí |
| registrado_por | FK Usuario | No | on_delete=PROTECT | PER | Sí |
| creado_en | DateTimeField | Sí | auto_now_add, index | OPE | — |

> **Historial inmutable.** Solo se crea desde `registrar_ocupacion()`.
> El admin no permite crear ni modificar manualmente.
> Cada registro va acompañado de un `EventoAuditoria` encadenado.

## 13. `hospitales.Hospital`

| Campo | Tipo | Oblig. | Restricciones | Clasif. | Auditoría |
|---|---|---|---|---|---|
| id | UUID | Sí | PK | OPE | — |
| codigo | SlugField(100) | Sí | **UNIQUE** | PUB | Sí |
| nombre | CharField(200) | Sí | — | PUB | Sí |
| tipo | CharField(20) | Sí | TextChoices | PUB | Sí |
| nivel | CharField(15) | Sí | TextChoices (Nivel I-IV) | PUB | Sí |
| organizacion | FK Organizacion | Sí | on_delete=PROTECT | OPE | Sí |
| responsable | FK Usuario | No | on_delete=PROTECT | OPE | Sí |
| ubicacion | PointField | No | SRID 4326 | PUB | Sí |
| direccion | CharField(300) | Sí | — | PUB | Sí |
| referencia_lugar | CharField(250) | No | — | PUB | Sí |
| municipio | FK Municipio | No | on_delete=PROTECT | PUB | Sí |
| parroquia | FK Parroquia | No | on_delete=PROTECT | PUB | Sí |
| telefono_publico | CharField(30) | No | — | PUB | Sí |
| correo_publico | EmailField | No | — | PUB | Sí |
| notas_internas | TextField | No | — | OPE | Sí |
| estado_operativo | CharField(20) | Sí | TextChoices, index | PUB | Sí |
| creado_en | DateTimeField | Sí | auto_now_add | OPE | — |
| actualizado_en | DateTimeField | Sí | auto_now | OPE | — |

## 14. `hospitales.Servicio`

| Campo | Tipo | Oblig. | Restricciones | Clasif. | Auditoría |
|---|---|---|---|---|---|
| id | UUID | Sí | PK | OPE | — |
| codigo | SlugField(80) | Sí | **UNIQUE** | PUB | — |
| nombre | CharField(150) | Sí | — | PUB | — |
| tipo | CharField(15) | Sí | SERVICIO/ESPECIALIDAD | PUB | — |
| activo | Boolean | Sí | default=True | PUB | — |

## 15. `hospitales.HospitalServicio`

| Campo | Tipo | Oblig. | Restricciones | Clasif. | Auditoría |
|---|---|---|---|---|---|
| id | UUID | Sí | PK | OPE | — |
| hospital | FK Hospital | Sí | on_delete=PROTECT | OPE | Sí |
| servicio | FK Servicio | Sí | on_delete=PROTECT | OPE | Sí |
| disponible | Boolean | Sí | default=True | PUB | Sí |
| notas | TextField | No | — | OPE | Sí |
| actualizado_en | DateTimeField | Sí | auto_now | OPE | — |

> **UniqueConstraint(hospital, servicio).** Un hospital no puede declarar el
> mismo servicio dos veces.

## 16. `hospitales.RecursoHospitalario`

| Campo | Tipo | Oblig. | Restricciones | Clasif. | Auditoría |
|---|---|---|---|---|---|
| id | UUID | Sí | PK | OPE | — |
| hospital | FK Hospital | Sí | on_delete=PROTECT | OPE | Sí |
| tipo | CharField(20) | Sí | UCI/URGENCIA/QUIROFANO/HOSPITALIZACION | PUB | Sí |
| capacidad_total | PositiveInteger | Sí | default=0 | PUB | Sí |
| disponible | PositiveInteger | Sí | default=0, <= capacidad_total | PUB | Sí |
| actualizado_en | DateTimeField | Sí | auto_now | OPE | — |

> **CheckConstraint:** `disponible <= capacidad_total`.
> **UniqueConstraint(hospital, tipo).**

## 17. `hospitales.RegistroDisponibilidad`

| Campo | Tipo | Oblig. | Restricciones | Clasif. | Auditoría |
|---|---|---|---|---|---|
| id | UUID | Sí | PK | OPE | — |
| recurso | FK RecursoHospitalario | Sí | on_delete=PROTECT | OPE | Sí |
| cantidad_anterior | PositiveInteger | Sí | — | OPE | Sí |
| cantidad_nueva | PositiveInteger | Sí | — | OPE | Sí |
| diferencia | Integer | Sí | puede ser negativo | OPE | Sí |
| registrado_por | FK Usuario | No | on_delete=PROTECT | PER | Sí |
| notas | TextField | No | — | OPE | Sí |
| creado_en | DateTimeField | Sí | auto_now_add, index | OPE | — |

> **Historial inmutable.** Solo `registrar_disponibilidad()` crea registros.
> El admin no permite crear, modificar ni eliminar.

## 18. `pacientes.Paciente`

| Campo | Tipo | Oblig. | Restricciones | Clasif. | Auditoría |
|---|---|---|---|---|---|
| id | UUID | Sí | PK | PER | — |
| cedula | CharField(20) | No | blank, plaintext | **PER** | Sí |
| cedula_hash | CharField(64) | No | **UNIQUE**, index, nullable | **PER** (seudonimizado) | — |
| nombres | CharField(200) | Sí | — | **PER** | Sí |
| apellidos | CharField(200) | Sí | — | **PER** | Sí |
| fecha_nacimiento | DateField | No | — | **PER** | Sí |
| sexo_biologico | CharField(1) | Sí | F/M/I/N | **PER** | Sí |
| telefono | CharField(30) | No | — | **PER** | Sí |
| email | EmailField | No | — | **PER** | Sí |
| cuenta_vinculada | FK Usuario | No | on_delete=SET_NULL | **PER** | Sí |
| notas_internas | TextField | No | — | **CLI** | Sí |
| creado_en | DateTimeField | Sí | auto_now_add | OPE | — |
| actualizado_en | DateTimeField | Sí | auto_now | OPE | — |

> **`cedula_hash`**: HMAC-SHA256 de la cédula normalizada (mayúsculas
> alfanuméricas). Permite detectar duplicados y buscar por cédula sin
> almacenar la cédula en claro indexada.
>
> **Cifrado diferido (decisión Fase 6.2):** los campos `PER` se almacenan
> en plaintext en Fase 6.2, protegidos por LUKS en producción (Fase 11)
> y HTTPS en tránsito. En Fase 11 se migran a cifrado a nivel de campo
> (AES) sin cambiar el schema relacional. **Decisión documentada en
> `docs/privacy-and-retention.md` §5.**
>
> **`__str__`**: `apellidos, nombres`. No incluye cédula (evita exposición
> en logs de Django).

## 19. `pacientes.ContactoEmergencia`

| Campo | Tipo | Oblig. | Restricciones | Clasif. | Auditoría |
|---|---|---|---|---|---|
| id | UUID | Sí | PK | PER | — |
| paciente | FK Paciente | Sí | on_delete=PROTECT | PER | Sí |
| nombre | CharField(200) | Sí | — | **PER** | Sí |
| parentesco | CharField(20) | Sí | TextChoices | PER | Sí |
| telefono | CharField(30) | Sí | — | **PER** | Sí |
| es_principal | Boolean | Sí | default=False | PER | Sí |
| creado_en | DateTimeField | Sí | auto_now_add | OPE | — |

> **UniqueConstraint** parcial: un solo `es_principal=True` por paciente
> (`condition=Q(es_principal=True)`). Múltiples contactos secundarios OK.

## 20. `pacientes.Episodio`

| Campo | Tipo | Oblig. | Restricciones | Clasif. | Auditoría |
|---|---|---|---|---|---|
| id | UUID | Sí | PK | CLI | — |
| paciente | FK Paciente | Sí | on_delete=PROTECT | CLI | Sí |
| hospital | FK Hospital | No* | on_delete=PROTECT | OPE | Sí |
| refugio | FK Refugio | No* | on_delete=PROTECT | OPE | Sí |
| motivo_consulta | TextField | Sí | — | **CLI** | Sí |
| estado | CharField(15) | Sí | TextChoices, index | CLI | Sí |
| fecha_ingreso | DateTimeField | Sí | default=now | CLI | Sí |
| fecha_egreso | DateTimeField | No | — | CLI | Sí |
| registrado_por | FK Usuario | Sí | on_delete=PROTECT | PER | Sí |
| notas_internas | TextField | No | — | **CLI** | Sí |
| creado_en | DateTimeField | Sí | auto_now_add | OPE | — |
| actualizado_en | DateTimeField | Sí | auto_now | OPE | — |

> **`CheckConstraint` XOR (`episodio_uno_y_solo_un_centro`):**
> exactamente uno de `hospital_id` o `refugio_id` debe estar presente.
> Un episodio ambulatorio puro no está permitido en esta fase — requiere
> al menos un centro (hospital o refugio).
>
> **`CheckConstraint` (`episodio_egreso_posterior_a_ingreso`):**
> `fecha_egreso IS NULL OR fecha_egreso >= fecha_ingreso`.
>
> **Estados:** ABIERTO, EN_ATENCION, DERIVADO, CERRADO, FALLECIDO, ABANDONO.
