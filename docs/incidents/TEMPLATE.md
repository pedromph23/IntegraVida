# Incidente: <título corto>

> **Fecha:** YYYY-MM-DD HH:MM (America/Caracas)
> **Duración:** <inicio> → <resolución>
> **Impacto:** <crítico / alto / medio / bajo>
> **Estado:** <resuelto / mitigado / en seguimiento>

## Resumen

Una o dos frases describiendo qué pasó y a quién afectó.

## Timeline

| Hora | Evento |
|---|---|
| HH:MM | Primer síntoma detectado |
| HH:MM | Alerta disparada / usuario reporta |
| HH:MM | Inicio de investigación |
| HH:MM | Causa raíz identificada |
| HH:MM | Mitigación aplicada |
| HH:MM | Sistema restaurado |
| HH:MM | Post-mortem iniciado |

## Causa raíz

Análisis técnico detallado. No basta "el servidor se cayó"; debe explicar
qué condición, cambio o falta de control permitió el incidente.

## Impacto

- Usuarios afectados (estimado).
- Datos afectados (si aplica).
- Funcionalidad degradada.
- Cumplimiento: ¿hubo exposición de datos personales/clínicos? (§11)

## Detección

¿Cómo se detectó? ¿Hubo alerta automática o fue reportado por usuario?
¿Cuánto tiempo pasó entre el inicio real y la detección?

## Respuesta

Acciones tomadas, en orden. Qué funcionó, qué no.

## Lecciones aprendidas

### Lo que funcionó bien

- ...

### Lo que falló

- ...

### Lo que faltaba

- ...

## Acciones correctivas

| # | Acción | Responsable | Plazo | Estado |
|---|---|---|---|---|
| 1 | ... | ... | ... | pendiente |
| 2 | ... | ... | ... | pendiente |

## Referencias

- Logs relevantes (paths).
- Tickets/commits relacionados.
- Documentación que debe actualizarse.

## Aprobación

- Preparado por: <nombre>
- Revisado por: <nombre>
- Fecha: YYYY-MM-DD
