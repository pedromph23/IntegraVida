#!/usr/bin/env python3
"""Actualiza data-dictionary.md y entity-relationship.md con refugios."""
from pathlib import Path
import sys

BASE = Path.cwd()
if not (BASE / "manage.py").exists():
    sys.exit("ERROR: ejecutar desde ~/proyectos/integravida")

BT = chr(96) * 3   # ``` de bloque Markdown

# ══════════════════════════════════════════════════════════════════
# 1) data-dictionary.md — añadir secciones 10, 11, 12
# ══════════════════════════════════════════════════════════════════
dd = BASE / "docs" / "data-dictionary.md"
text = dd.read_text(encoding="utf-8")

nuevas = f"""
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
"""

if "## 10. `refugios.Refugio`" not in text:
    dd.write_text(text.rstrip() + "\n" + nuevas, encoding="utf-8")
    print("OK: data-dictionary.md ampliado (secciones 10-12)")
else:
    print("ya aplicado: data-dictionary.md")

# ══════════════════════════════════════════════════════════════════
# 2) entity-relationship.md — insertar bloques Mermaid nuevos
# ══════════════════════════════════════════════════════════════════
er = BASE / "docs" / "entity-relationship.md"
text = er.read_text(encoding="utf-8")

# Insertar definiciones de entidades después del bloque EVENTO_AUDITORIA { ... }
needle = "    EVENTO_AUDITORIA {\n"
idx = text.find(needle)
if idx == -1:
    sys.exit("ERROR: no encontré EVENTO_AUDITORIA en el ER")

# Buscar el cierre de EVENTO_AUDITORIA
close = text.find("    }\n", idx)
if close == -1:
    sys.exit("ERROR: no encontré el cierre de EVENTO_AUDITORIA")
insert_at = close + len("    }\n")

nuevas_entidades = """
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
"""

# Insertar entidades
text = text[:insert_at] + nuevas_entidades + text[insert_at:]

# Insertar relaciones: buscar el bloque de relaciones (después del cierre erDiagram)
rel_needle = "    ORGANIZACION ||--o{ EMERGENCIA : \"declara\"\n"
if rel_needle not in text:
    sys.exit("ERROR: no encontré el bloque de relaciones")

nuevas_relaciones = rel_needle + """    ORGANIZACION ||--o{ REFUGIO : "administra"
    USUARIO ||--o{ REFUGIO : "responsable"
    MUNICIPIO ||--o{ REFUGIO : "ubica"
    PARROQUIA ||--o{ REFUGIO : "ubica"
    REFUGIO ||--o{ NECESIDAD : "requiere"
    REFUGIO ||--o{ REGISTRO_OCUPACION : "registra"
    USUARIO ||--o{ REGISTRO_OCUPACION : "registra"
"""
text = text.replace(rel_needle, nuevas_relaciones, 1)

# Actualizar tabla de "Entidades pendientes por fase"
text = text.replace(
    "| `refugios` | Fase 5 | territorio |",
    "| `refugios` | **✅ Fase 5 — implementado** | — |",
)

er.write_text(text, encoding="utf-8")
print("OK: entity-relationship.md ampliado con Refugio, Necesidad, RegistroOcupacion")
