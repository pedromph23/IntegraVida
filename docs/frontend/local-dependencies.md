
## Deuda D-F5-01 — Leaflet en bundle principal

- **Estado:** abierta
- **Síntoma:** `static/js/dist/main.js` = 107 KB gzip (objetivo <80 KB).
- **Causa:** Leaflet se importa desde `main.js` en lugar de un chunk lazy.
- **Fix planificado:** split chunk con `esbuild --splitting --format=esm`;
  `maps.js` cargado solo en templates con `{% block scripts %}` y mapa.
  Verificar que `templates/public/hospitals_list.html` y `shelters_list.html`
  sólo piden `maps.js`.
- **Impacto:** no bloquea F3/F4; bloqueante para F5 (§10 rendimiento).
- **Añadida:** 2026-11-02


## Deuda D-F5-02 — djlint --check no está en verde

- **Estado:** abierta
- **Síntoma:** `djlint templates/ --check` reporta "77 files would be updated"
  (deviaciones de indentación/espaciado, sin impacto en render).
- **Causa:** DJLint nunca se ha ejecutado como gate en CI.
- **Fix planificado (F5):**
  1. `djlint templates/ --reformat` en una rama **dedicada**, sin tocar lógica.
  2. Verificar `get_template` sobre el 100 % y `test_a11y`/`test_no_cdn` en verde.
  3. Solo entonces añadir al CI: `djlint templates/ --check`.
- **Impacto:** cero funcional. El render no cambia.
- **Añadida:** 2026-11-02

## Deuda D-F5-03 — Auto-democión de ADMIN_ORGANIZACION

- **Estado:** abierta (decisión de producto pendiente)
- **Síntoma:** `_can_manage_membership` sólo valida "misma org o superuser".
  Un ADMIN_ORGANIZACION puede cambiar su propio rol a OPERADOR/COORDINADOR
  (o suspender/revocar su propia membresía). Si es el único ADMIN de la org,
  la organización queda sin administrador hasta que intervenga un superuser.
- **Test que lo documenta:**
  `test_admin_org_puede_autodemoverse_documenta_riesgo` en
  `frontend/tests/test_dashboard_configuracion.py`.
- **Fix sugerido (cuando el producto decida):** añadir en
  `_can_manage_membership` una comprobación `membresia.usuario_id == user.id`
  que devuelva `False` (o `True` sólo si existe otro ADMIN_ORGANIZACION ACTIVO
  en la misma org). Convertir el test citado a
  `assertEqual(r.status_code, 403)`.
- **Impacto:** seguridad operativa (org huérfana), no data leak.
- **Añadida:** 2026-11-02


## Deuda D-F5-04 — SESSION_COOKIE_AGE no reducido para admin

- **Estado:** abierta (decisión de producto)
- **Síntoma:** `SESSION_COOKIE_AGE` mantiene el default Django (2 semanas).
  Un atacante con cookie robada tras MFA tendría hasta 2 semanas.
- **Mitigación existente:** `AdminMFARequiredMiddleware` re-valida
  `admin_mfa_verified_at < 8h`. Pasado ese umbral redirige a `/slug/mfa/`,
  aunque la cookie Django siga viva. El vector real queda acotado a 8h.
- **Fix sugerido:** en `mfa_verify_submit`, tras éxito,
  `request.session.set_expiry(8 * 3600)`. Alineado con MFA_VALID_SECONDS.
  Alternativa: `SESSION_COOKIE_AGE = 3600` global (afecta panel institucional).
- **Impacto:** ventana de 8h vs 2 semanas si el atacante roba cookie
  post-MFA. Data leak mitigado por otros controles.
- **Añadida:** 2026-11-02

## Deuda D-F5-05 — Login admin nativo sin rate limit ni audit propios

- **Estado:** abierta (mitigada por MFA rate limit)
- **Síntoma:** `/slug/login/` (Django admin nativo) no llama a
  `check_rate_limit` ni registra `user_login_failed` en `EventoAuditoria`.
  Un atacante puede enumerar credenciales sin traza ni freno.
- **Mitigación existente:** si el atacante pasa `/slug/login/`, cae en
  `AdminMFARequiredMiddleware` → `/slug/mfa/`, donde SÍ hay rate limit
  (5/15min) + audit de fallos (nuevo).
- **Fix sugerido:** signal `user_login_failed` en `apps/auditoria/signals.py`
  que llame a `registrar_evento(accion="admin.login.failed", ...)`. Aplicar
  `check_rate_limit` en el login nativo requiere override del `AdminSite.login`
  (costoso) o un middleware delante de `/slug/login/`.
- **Impacto:** enmascarado por MFA. Solo impacta si MFA es comprometido.
- **Añadida:** 2026-11-02

## Deuda D-F5-04 — SESSION_COOKIE_AGE no reducido para admin

- **Estado:** abierta (decisión de producto)
- **Síntoma:** `SESSION_COOKIE_AGE` mantiene el default Django (2 semanas).
  Un atacante con cookie robada tras MFA tendría hasta 2 semanas.
- **Mitigación existente:** `AdminMFARequiredMiddleware` re-valida
  `admin_mfa_verified_at < 8h`. Pasado ese umbral redirige a `/slug/mfa/`,
  aunque la cookie Django siga viva. El vector real queda acotado a 8h.
- **Fix sugerido:** en `mfa_verify_submit`, tras éxito,
  `request.session.set_expiry(8 * 3600)`. Alineado con MFA_VALID_SECONDS.
  Alternativa: `SESSION_COOKIE_AGE = 3600` global (afecta panel institucional).
- **Impacto:** ventana de 8h vs 2 semanas si el atacante roba cookie
  post-MFA. Data leak mitigado por otros controles.
- **Añadida:** 2026-11-02

## Deuda D-F5-05 — Login admin nativo sin rate limit ni audit propios

- **Estado:** abierta (mitigada por MFA rate limit)
- **Síntoma:** `/slug/login/` (Django admin nativo) no llama a
  `check_rate_limit` ni registra `user_login_failed` en `EventoAuditoria`.
  Un atacante puede enumerar credenciales sin traza ni freno.
- **Mitigación existente:** si el atacante pasa `/slug/login/`, cae en
  `AdminMFARequiredMiddleware` → `/slug/mfa/`, donde SÍ hay rate limit
  (5/15min) + audit de fallos (nuevo).
- **Fix sugerido:** signal `user_login_failed` en `apps/auditoria/signals.py`
  que llame a `registrar_evento(accion="admin.login.failed", ...)`. Aplicar
  `check_rate_limit` en el login nativo requiere override del `AdminSite.login`
  (costoso) o un middleware delante de `/slug/login/`.
- **Impacto:** enmascarado por MFA. Solo impacta si MFA es comprometido.
- **Añadida:** 2026-11-02

## Cierre del panel institucional — CRUD operativo

**Estado:** COMPLETO ✅

CRUDs funcionales (crear + editar + inactivar/activar + cross-org 404):

| Módulo | CRUD | FSM | Notas |
|--------|------|-----|-------|
| Pacientes | update | — | create vía episodio |
| Refugios | create/update/inactivar | cambiar_estado | `inactivar` no borra (PROTECT) |
| Hospitales | create/update/inactivar/reactivar | cambiar_estado | ídem |
| Emergencias | create/update | cambiar_estado | ídem |
| Insumos | create/update/toggle | — | catálogo global (admin plataforma) |
| Membresías | create | update (rol/estado) | scoped por `_orgs_admin` |
| Entregas | — | BORRADOR→ENVIADA→RECIBIDA/CANCELADA | FSM con audit |
| Transferencias | — | 6 estados | FSM con audit |
| Derivaciones | — | 5 estados | FSM con audit |
| Triajes | solo lectura | — | creado por flujo médico |
| Stock | solo lectura | — | ajustado vía movimientos/FSM |

**Reglas de coherencia aplicadas:**
- `inactivar` (no `delete()`) en entidades con FKs `PROTECT`.
- Scope por organización en listas y detalles (404 cross-org).
- Permisos por rol (`can_edit`, `can_manage`, `can_create`) respetados en UI + backend.
- Toda escritura pasa por `apps/*/services.py` cuando existe (auditoría incluida).
- Tests: **402** frontend verdes.

**Pendiente (fuera de alcance CRUD):**
- D-F5-01 Leaflet lazy, D-F5-02 djlint, D-F5-03 autodemoción, D-F5-04 session, D-F5-05 login admin.
- E2E Playwright de flujos CRUD (F5 §11.3).

**Añadido:** 2026-11-02
