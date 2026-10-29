# Política de Privacidad, Retención y Protección de Información — IntegraVida

> Documento exigido por §11 y §24 del prompt maestro.
> **Estado:** borrador inicial. Debe revisarse antes de implementar
> cualquier modelo de `pacientes`, `triaje` o `derivaciones` (Fase 6–7).

## 1. Principios rectores

1. **Minimización de datos.** Solo se recopila lo necesario para la atención.
2. **Finalidad explícita.** Cada campo tiene un propósito documentado en
   `docs/data-dictionary.md`. Sin finalidad, no hay campo.
3. **Necesidad de conocer.** El acceso se concede por rol + organización +
   ámbito territorial + tipo de dato + acción solicitada (§8).
4. **Trazabilidad.** Todo acceso a datos personales o clínicos genera un
   evento de auditoría (§7).
5. **Privacidad por defecto.** Un endpoint nuevo es privado salvo que
   declare explícitamente lo contrario (§6.3).

## 2. Clasificación de sensibilidad (§6.2)

| Clase | Definición | Ejemplos | Acceso |
|---|---|---|---|
| **PUB** | Publicable sin restricción | Nombre de hospital, teléfono público | Cualquiera sin login |
| **OPE** | Operativo interno | Capacidad, ocupación agregada, inventario | Autenticados con rol adecuado |
| **PER** | Personal identificable | Cédula, nombre completo, contacto | Rol + organización + necesidad |
| **CLI** | Clínico / especialmente protegido | Diagnóstico, triaje, historia clínica | Rol sanitario + organización |
| **SEC** | Secreto de autenticación | `SECRET_KEY`, hashes, tokens | Nunca vía API |
| **AUD** | Auditoría restringida | `EventoAuditoria` | Solo roles de auditoría |

## 3. Finalidad por tipo de dato

| Tipo de dato | Finalidad | Clase | Retención |
|---|---|---|---|
| Identificación del paciente | Vincular episodios | PER | Episodio + plazo legal |
| Demográficos pertinentes | Adecuar atención | PER | Igual que identificación |
| Contacto de familiar/tutor | Notificación | PER | Igual que identificación |
| Referencias clínicas | Decisión médica | CLI | Plazo legal |
| Triaje | Priorizar atención | CLI | Plazo legal |
| Derivaciones | Coordinación | CLI / OPE | Plazo legal |
| Ubicación de refugio | Logística | PUB / OPE | Operativa |
| Inventario y lotes | Suministros | OPE | Operativa + auditoría |

## 4. Control de acceso

Cada petición a un dato sensible debe pasar por:

```
Autenticación → Rol → Permiso específico → Organización
  → Ámbito territorial → Tipo de dato → Acción → Necesidad
```

- **Nunca** confiar en parámetros del frontend para determinar pertenencia
  a una organización (§8, §17).
- El backend verifica **siempre** el objeto antes de servir.
- Un usuario de la organización A **no** accede a expedientes de B cambiando
  el ID en la URL.

## 5. Cifrado y almacenamiento

- **En tránsito:** HTTPS obligatorio en producción
  (`SECURE_SSL_REDIRECT = True`, ver `config/settings.py`).
- **En reposo:** PostgreSQL con cifrado de disco del sistema operativo (LUKS)
  en producción. Evaluar cifrado a nivel de campo para los campos `CLI` que
  lo requieran (decisión pendiente antes de Fase 6).
- **Secretos:** solo en `.env`, nunca en el repositorio (§13).
- **Logs:** no incluir datos `PER`, `CLI` ni `SEC` en mensajes de depuración.
- **Backups:** cifrados, con control de acceso separado del operativo.

## 6. Retención

Política inicial (ajustable según legislación venezolana aplicable):

| Categoría | Plazo | Acción al vencer |
|---|---|---|
| Datos operativos (`OPE`) | Operación + 2 años | Archivar o eliminar |
| Datos personales (`PER`) | Relación + plazo legal | Archivar |
| Datos clínicos (`CLI`) | Plazo legal sanitario | Archivar |
| Auditoría (`AUD`) | ≥ 2 años | Archivar en almacenamiento inmutable |
| Secretos (`SEC`) | Mientras el usuario esté activo | Eliminar al desactivar |

## 7. Derechos de las personas

- **Rectificación:** el titular puede solicitar corrección de datos erróneos.
  La corrección queda auditada.
- **Acceso:** el titular puede solicitar qué datos se almacenan sobre él.
- **Eliminación:** solo si no hay obligación legal de conservar. Los datos
  clínicos y de auditoría normalmente **no** son eliminables.
- **Oposición:** evaluación caso por caso por el responsable de privacidad
  institucional.

## 8. Anonimización y estadísticas públicas

- Las estadísticas públicas (`reportes` §5.13) deben agregarse.
- **Grupos < 5 personas** no se publican (riesgo de reidentificación).
- No se publican cruces que permitan deducir identidades por combinación
  de campos.
- Evaluación previa obligatoria antes de exponer cualquier cifra en el
  portal público.

## 9. Exportaciones

- Las exportaciones **heredan** los permisos de la consulta interactiva
  (§5.13, §17).
- Toda exportación de datos `PER` o `CLI` se registra en auditoría.
- Los archivos exportados deben:
  - Incluir marca de tiempo y usuario que exportó.
  - Aplicar límites de filas cuando sea viable.
  - Ser eliminables tras un plazo definido.

## 10. Acceso extraordinario durante emergencias (§6.5)

Mecanismo controlado para personal autorizado cuando una emergencia real
lo requiera:

1. **Identificación del usuario** que activa el modo.
2. **Justificación obligatoria** en el campo `justificacion` del
   `EventoAuditoria`.
3. **Alcance limitado** (por ejemplo, solo expedientes de la zona declarada
   en emergencia).
4. **Duración limitada** cuando sea viable (timeout configurable).
5. **Registro de auditoría** con `resultado=EXITOSO` y
   `metadatos={"modo": "extraordinario"}`.
6. **Revisión posterior** por rol de auditoría.

**Prohibición explícita:** este mecanismo **no** puede usarse para eludir
permisos en operaciones rutinarias.

## 11. Gestión de incidentes

Cuando se detecte un incidente de seguridad que afecte datos personales o
clínicos:

1. **Contener:** aislar el sistema afectado.
2. **Documentar:** registrar el evento en auditoría con la mayor información
   posible.
3. **Notificar:** al responsable de privacidad institucional.
4. **Evaluar:** alcance, datos afectados, personas afectadas.
5. **Remedar:** corregir la causa.
6. **Aprender:** actualizar esta política si aplica.

## 12. Cumplimiento y revisión

Este documento se revisa:

- **Antes de Fase 6** (pacientes, triaje).
- **Antes de Fase 7** (derivaciones).
- **Antes de cualquier despliegue a producción** (Fase 11).
- **Anualmente** o cuando cambie la legislación aplicable.

## 13. Pendientes de este documento

- [ ] Definir si se aplica cifrado a nivel de campo para datos `CLI`
      (decisión bloqueante para Fase 6).
- [ ] Confirmar plazos legales según normativa venezolana vigente.
- [ ] Diseñar el flujo de "derecho de acceso del titular".
- [ ] Diseñar la interfaz administrativa para "modo extraordinario".
- [ ] Definir política de backups cifrados y pruebas de restauración (§7.3).
- [ ] Nombrar un responsable de privacidad institucional (rol, no persona
      física en este documento).

## 14. Referencias

- Prompt maestro §6.2, §7, §8, §11, §17, §19.
- `docs/data-dictionary.md` — clasificación campo por campo.
- `docs/permissions.md` — matriz de roles (pendiente de crear).
- `docs/audit-and-security.md` — política completa de auditoría
  (pendiente de crear).
