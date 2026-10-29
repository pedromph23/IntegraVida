# Política de Privacidad, Retención y Protección de Información — IntegraVida

> Documento exigido por §11 y §24 del prompt maestro.
> **Estado:** borrador inicial. Debe revisarse antes de implementar
> cualquier modelo de `pacientes`, `triaje` o `derivaciones` (Fase 6–7).

## 1. Principios rectores

1. **Minimización de datos.** Solo se recopila lo necesario para la
   atención. Un campo que no sirve para una decisión operativa no se
   almacena.
2. **Finalidad explícita.** Cada campo tiene un propósito documentado
   en `docs/data-dictionary.md`. Sin finalidad, no hay campo.
3. **Necesidad de conocer.** El acceso se concede por rol + organización
   + ámbito territorial + tipo de dato + acción solicitada (§8).
4. **Trazabilidad.** Todo acceso, modificación o exportación de datos
   personales o clínicos genera un evento de auditoría (§7).
5. **Privacidad por defecto.** Un endpoint nuevo es privado salvo
   que declare explícitamente lo contrario (§6.3).

## 2. Clasificación de sensibilidad (§6.2)

| Clase | Definición | Ejemplos | Acceso |
|---|---|---|---|
| **PUB** | Publicable sin restricción | Nombre de hospital, teléfono público, estado operativo | Cualquiera sin login |
| **OPE** | Operativo interno | Capacidad, ocupación agregada, movimientos de inventario | Usuarios autenticados con rol adecuado |
| **PER** | Personal identificable | Cédula, nombre completo, contacto, dirección | Rol + organización + ámbito + necesidad |
| **CLI** | Clínico / especialmente protegido | Diagnóstico, síntomas, triaje, historia clínica | Rol sanitario + organización + necesidad |
| **SEC** | Secreto de autenticación | `SECRET_KEY`, hashes de contraseña, tokens | Nunca consultable vía API |
| **AUD** | Auditoría restringida | `EventoAuditoria` | Solo roles de auditoría explícitos |

## 3. Finalidad por tipo de dato

| Tipo de dato | Finalidad operativa | Clase | Retención |
|---|---|---|---|
| Identificación del paciente | Vincular episodios de atención | PER | Mientras dure el episodio + plazo legal |
| Datos demográficos pertinentes | Adecuar atención (edad, sexo biológico cuando relevante) | PER | Igual que identificación |
| Contacto de familiar/tutor | Notificación y seguimiento | PER | Igual que identificación |
| Referencias clínicas | Decisión médica | CLI | Plazo legal |
| Triaje | Priorizar atención | CLI | Plazo legal |
| Derivaciones | Coordinación entre centros | CLI / OPE | Plazo legal |
| Ubicación de refugio | Coordinación logística | PUB / OPE | Operativa |
| Inventario y lotes | Control de suministros | OPE | Operativa + auditoría |

## 4. Control de acceso

Cada petición a un dato sensible debe pasar por:

