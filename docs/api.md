# API de IntegraVida — Contrato publico

> **Estado:** parcial — cubre los endpoints publicos de emergencias.
> El resto de la API se documentara al cierre de su fase.

## Base URL (desarrollo)

```
http://127.0.0.1:8000/api/publico/
```

## Autenticacion

**Ningun endpoint publico requiere autenticacion ni cookies.**
Los endpoints internos (`/api/interno/...`) si requieren sesion.

## Justificacion de `@csrf_exempt` en endpoints publicos

`POST /api/publico/emergencias/reportes/` recibe JSON sin que exista
sesion previa. No hay cookies reutilizables para CSRF. El rate limiting
por IP (§6.4) es la defensa aplicable. Los endpoints internos NO son
`csrf_exempt`.

## Endpoints

### `GET /api/publico/emergencias/`

Lista eventos en estado publico.

**Query params opcionales:**
- `categoria`: valor de `Emergencia.Categoria`.
- `gravedad`: 1, 2, 3 o 4.
- `municipio`: busqueda `icontains`.
- `q`: busqueda en `ubicacion_texto` o `titulo`.
- `limite` (default 50): 1–100.
- `offset` (default 0): entero >= 0.

**Estados expuestos:** `CONFIRMADA`, `EN_ATENCION`, `RESUELTA`.

**Estados ocultos:** `RECIBIDA`, `EN_VERIFICACION`, `DESCARTADA` (§5.4, §6.4).

**Campos NO expuestos:** `reportada_por`, `organizacion` (§6.2, §11).

### `GET /api/publico/emergencias/{uuid}/`

Detalle de una emergencia publica.

**200:** `{"emergencia": {...}}`

**404:** si no existe o no esta en estado publico (no filtra existencia).

### `POST /api/publico/emergencias/reportes/`

Recibe un reporte ciudadano anonimo. Queda `PENDIENTE`.

**Content-Type:** `application/json` (acepta `; charset=utf-8`).

**Campos permitidos:** `descripcion`, `ubicacion_texto`, `categoria`, `referencia_lugar`.

**Respuesta 201:**

```
{
  "mensaje": "Reporte recibido. Quedara pendiente de verificacion.",
  "reporte_id": "uuid",
  "estado_revision": "PENDIENTE"
}
```

**Errores:** 400 (validacion), 415 (content-type), 429 (rate limit 5/min por IP).

### `GET /api/publico/emergencias/reportes/estado/`

Ping publico del servicio.

```
{"servicio": "recepcion_reportes", "disponible": true}
```

## Codigos HTTP

| Codigo | Significado |
|---|---|
| 200 | OK |
| 201 | Recurso creado |
| 400 | Solicitud invalida |
| 404 | No encontrado o no publico |
| 405 | Metodo no permitido |
| 415 | Content-Type incorrecto |
| 429 | Rate limit excedido |

## Refugios (Fase 5.5)

### `GET /api/publico/refugios/`

Lista refugios operativos públicos.

**Estados expuestos:** `ACTIVO`, `LLENO`.
**Estados ocultos:** `MANTENIMIENTO`, `CERRADO`, `INACTIVO` (§5.5).

**Query params opcionales:**
- `tipo`: valor de `Refugio.Tipo`.
- `estado_operativo`: solo `ACTIVO` o `LLENO` (otros → 400).
- `municipio`: `icontains` por nombre.
- `parroquia`: `icontains` por nombre.
- `q`: búsqueda en `nombre` o `direccion` (máx 100 chars).
- `limite` (default 50): 1–100.
- `offset` (default 0): entero >= 0.

**Campos NO expuestos:** `organizacion`, `responsable`, `notas_internas`.

**Respuesta 200:**

```
{
  "total": 5,
  "limite": 50,
  "offset": 0,
  "resultados": [
    {
      "id": "uuid",
      "codigo": "refugio-petare-1",
      "nombre": "...",
      "tipo": "REFUGIO",
      "tipo_texto": "Refugio",
      "direccion": "...",
      "referencia_lugar": "",
      "punto": {"latitud": 10.5, "longitud": -66.9},
      "municipio": "Sucre",
      "parroquia": "Petare",
      "capacidad_total": 100,
      "capacidad_disponible": 70,
      "porcentaje_ocupacion": 30.0,
      "esta_lleno": false,
      "servicios": ["agua", "cocina"],
      "estado_operativo": "ACTIVO",
      "estado_operativo_texto": "Activo",
      "telefono_publico": "...",
      "correo_publico": "",
      "ocupacion_actualizada_en": "2026-10-31T12:00:00-04:00"
    }
  ]
}
```

`ocupacion_actualizada_en` es `null` si el refugio no ha tenido cambios de ocupación desde su creación.

### `GET /api/publico/refugios/{codigo}/`

Detalle por `codigo` (slug único).

**200:** `{"refugio": {...}}` con los mismos campos del listado.

**404:** si no existe o no está en estado público. La respuesta es
idéntica en ambos casos (no filtra existencia).
