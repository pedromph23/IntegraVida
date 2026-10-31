# Modelo Entidad-Relación — IntegraVida

> **Estado:** parcial — cubre las 5 entidades implementadas (Fase 1 retroactiva).
> Las apps restantes se marcan como TBD y se documentarán al inicio de su fase.

## Diagrama

```mermaid
erDiagram
    USUARIO {
        uuid id PK
        string username
        string email
        boolean is_active
    }
    ORGANIZACION {
        uuid id PK
        string nombre
        string tipo
        string estado
        string telefono_publico
    }
    MEMBRESIA {
        uuid id PK
        uuid usuario_id FK
        uuid organizacion_id FK
        string rol
        string estado
    }
    ENTIDAD_FEDERAL {
        uuid id PK
        string nombre
        string codigo UK
        string tipo
    }
    MUNICIPIO {
        uuid id PK
        uuid entidad_federal_id FK
        string nombre
        string codigo
    }
    PARROQUIA {
        uuid id PK
        uuid municipio_id FK
        string nombre
        string codigo
    }
    EMERGENCIA {
        uuid id PK
        string titulo
        string categoria
        int gravedad
        string estado
        string ubicacion_texto
        string referencia_lugar
        geometry punto
        uuid municipio_id FK
        uuid parroquia_id FK
        uuid reportada_por_id FK
        uuid organizacion_id FK
    }
    REPORTE_EMERGENCIA {
        uuid id PK
        uuid emergencia_id FK
        uuid reportante_id FK
        string categoria
        string ubicacion_texto
        string referencia_lugar
        geometry punto
        uuid municipio_id FK
        uuid parroquia_id FK
        string canal
        string estado_revision
    }
    EVENTO_AUDITORIA {
        uuid id PK
        uuid actor_id FK
        uuid organizacion_id
        string accion
        string tipo_objeto
        string objeto_id
        string resultado
        string justificacion
        string agente_usuario
        string id_correlacion
    }

    REFUGIO {
        uuid id PK
        string codigo UK
        string nombre
        string tipo
        uuid organizacion_id FK
        uuid responsable_id FK
        geometry ubicacion
        string direccion
        uuid municipio_id FK
        uuid parroquia_id FK
        int capacidad_total
        int ocupacion_actual
        json servicios
        string estado_operativo
        string telefono_publico
    }
    NECESIDAD {
        uuid id PK
        uuid refugio_id FK
        string categoria
        string descripcion
        int prioridad
        string cantidad_estimada
        boolean cubierta
        datetime cubierta_en
    }
    REGISTRO_OCUPACION {
        uuid id PK
        uuid refugio_id FK
        int cantidad_anterior
        int cantidad_nueva
        int diferencia
        string fuente
        text notas
        uuid registrado_por_id FK
        datetime creado_en
    }
    HOSPITAL {
        uuid id PK
        string codigo UK
        string nombre
        string tipo
        string nivel
        uuid organizacion_id FK
        uuid responsable_id FK
        geometry ubicacion
        string direccion
        uuid municipio_id FK
        uuid parroquia_id FK
        string estado_operativo
        string telefono_publico
    }
    SERVICIO {
        uuid id PK
        string codigo UK
        string nombre
        string tipo
        boolean activo
    }
    HOSPITAL_SERVICIO {
        uuid id PK
        uuid hospital_id FK
        uuid servicio_id FK
        boolean disponible
    }
    RECURSO_HOSPITALARIO {
        uuid id PK
        uuid hospital_id FK
        string tipo
        int capacidad_total
        int disponible
    }
    REGISTRO_DISPONIBILIDAD {
        uuid id PK
        uuid recurso_id FK
        int cantidad_anterior
        int cantidad_nueva
        int diferencia
        uuid registrado_por_id FK
        datetime creado_en
    }

    PACIENTE {
        uuid id PK
        string cedula
        string cedula_hash UK
        string nombres
        string apellidos
        date fecha_nacimiento
        string sexo_biologico
        string telefono
        uuid cuenta_vinculada_id FK
    }
    CONTACTO_EMERGENCIA {
        uuid id PK
        uuid paciente_id FK
        string nombre
        string parentesco
        string telefono
        boolean es_principal
    }
    EPISODIO {
        uuid id PK
        uuid paciente_id FK
        uuid hospital_id FK
        uuid refugio_id FK
        text motivo_consulta
        string estado
        datetime fecha_ingreso
        datetime fecha_egreso
        uuid registrado_por_id FK
    }


    USUARIO ||--o{ MEMBRESIA : "tiene"
    ORGANIZACION ||--o{ MEMBRESIA : "agrupa"
    USUARIO ||--o{ EVENTO_AUDITORIA : "actua"
    ENTIDAD_FEDERAL ||--o{ MUNICIPIO : "contiene"
    MUNICIPIO ||--o{ PARROQUIA : "contiene"
    MUNICIPIO ||--o{ EMERGENCIA : "ubica"
    PARROQUIA ||--o{ EMERGENCIA : "ubica"
    EMERGENCIA ||--o{ REPORTE_EMERGENCIA : "recibe"
    ORGANIZACION ||--o{ EMERGENCIA : "declara"
    ORGANIZACION ||--o{ REFUGIO : "administra"
    USUARIO ||--o{ REFUGIO : "responsable"
    MUNICIPIO ||--o{ REFUGIO : "ubica"
    PARROQUIA ||--o{ REFUGIO : "ubica"
    REFUGIO ||--o{ NECESIDAD : "requiere"
    REFUGIO ||--o{ REGISTRO_OCUPACION : "registra"
    USUARIO ||--o{ REGISTRO_OCUPACION : "registra"
    ORGANIZACION ||--o{ HOSPITAL : "administra"
    USUARIO ||--o{ HOSPITAL : "responsable"
    MUNICIPIO ||--o{ HOSPITAL : "ubica"
    PARROQUIA ||--o{ HOSPITAL : "ubica"
    HOSPITAL ||--o{ HOSPITAL_SERVICIO : "ofrece"
    SERVICIO ||--o{ HOSPITAL_SERVICIO : "en"
    HOSPITAL ||--o{ RECURSO_HOSPITALARIO : "tiene"
    RECURSO_HOSPITALARIO ||--o{ REGISTRO_DISPONIBILIDAD : "registra"
    USUARIO ||--o{ REGISTRO_DISPONIBILIDAD : "registra"
    PACIENTE ||--o{ CONTACTO_EMERGENCIA : "tiene"
    PACIENTE ||--o{ EPISODIO : "tiene"
    HOSPITAL ||--o{ EPISODIO : "atiende"
    REFUGIO ||--o{ EPISODIO : "aloja"
    USUARIO ||--o{ EPISODIO : "registra"
    USUARIO ||--o| PACIENTE : "vinculado"
```

## Entidades pendientes por fase

| App | Fase del prompt §24 | Dependencias |
|---|---|---|
| `refugios` | **✅ Fase 5 — implementado** | — |
| `hospitales` | **Fase 6.1 — implementado** | — |
| `pacientes` | **Fase 6.2 — implementado** | — |
| `triaje` | Fase 6 | pacientes |
| `derivaciones` | Fase 7 | hospitales |
| `inventario` | Fase 8 | organizaciones |
| `distribucion` | Fase 8 | inventario |
| `configuracion` | Fase 9 | — |
| `reportes` | Fase 9 | transversal |

## Clasificación por sensibilidad (§6.2)

| Entidad | Clasificación predominante |
|---|---|
| EntidadFederal, Municipio, Parroquia | PUB |
| Organizacion | PUB (institucional) |
| Usuario | PER (con campos SEC) |
| Membresia | OPE / PER |
| Emergencia | OPE (con campos públicos autorizados) |
| ReporteEmergencia | OPE / PER |
| EventoAuditoria | AUD |

## Pendiente de diseño antes de Fase 3

- Añadir a `EventoAuditoria`: `fecha_hora` (TIMESTAMPTZ), `ip_origen`, `hash_anterior`, `hash_actual`.
- Evaluar convertir `EventoAuditoria.organizacion_id` (UUIDField) en `ForeignKey(Organizacion, null=True, on_delete=PROTECT)`.
- Definir `UniqueConstraint` en `Membresia(usuario, organizacion, rol)`.
- Definir `UniqueConstraint` en `Municipio(entidad_federal, codigo)` y `Parroquia(municipio, codigo)`.
