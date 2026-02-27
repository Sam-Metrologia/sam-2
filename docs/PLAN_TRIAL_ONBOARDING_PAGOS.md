# Plan de Implementacion: Trial Autoservicio + Onboarding + Pagos

## Resumen Ejecutivo

Tres modulos independientes para automatizar el ciclo de vida del cliente:
- **Modulo A**: El cliente se registra solo y crea su trial
- **Modulo B**: La plataforma lo guia paso a paso
- **Modulo C**: Al vencer el trial, paga por PSE/tarjeta

Orden de implementacion: A -> B -> C (cada uno funciona independiente)

---

## Checklist de Avance

### MODULO A: Auto-registro de Trial
- [x] A1. Crear formulario RegistroTrialForm (`core/forms/registro.py`)
- [x] A2. Crear vista solicitar_trial (`core/views/registro.py`)
- [x] A3. Crear template solicitar_trial.html
- [x] A4. Crear template trial_exitoso.html
- [x] A5. Agregar URLs en core/urls.py
- [x] A6. Agregar boton "Solicitar Trial" en login.html
- [ ] A7. Configurar CAPTCHA (reCAPTCHA) - Flag existe pero no implementado
- [x] A8. Tests de registro (39 tests)
- [x] A9. Verificar tests pasan

### MODULO B: Onboarding Guiado
- [x] B1. Crear modelo OnboardingProgress en models.py
- [x] B2. Crear migracion y migrar
- [x] B3. Crear signal auto-crear progreso al crear usuario trial
- [x] B4. Integrar Shepherd.js (tour guiado multi-pagina 21 pasos)
- [x] B5. Crear widget checklist en dashboard (partial template)
- [x] B6. Crear vista API progreso onboarding (`core/views/onboarding.py`)
- [x] B7. Marcar pasos en vistas existentes (4 vistas)
- [x] B8. Incluir checklist en template dashboard.html
- [x] B9. Tests de onboarding (41 tests)
- [x] B10. Verificar tests pasan
- [x] B11. Context processor para carga global de Shepherd.js
- [x] B12. Tour multi-pagina con persistencia localStorage
- [x] B13. Permisos de prestamos para usuarios trial
- [x] B14. Boton WhatsApp soporte en base.html
- [x] B15. Banner trial expirado en dashboard

### MODULO C: Pagos (PSE / Tarjeta con Wompi)
- [x] C1. Elegir pasarela: Wompi (Bancolombia)
- [x] C2. Crear modelo TransaccionPago en models.py
- [x] C3. Crear migracion y migrar
- [x] C4. Crear pagina de planes (`core/views/pagos.py` + `templates/core/planes.html`)
- [x] C5. Crear endpoint inicio de pago (`iniciar_pago`, `iniciar_addon_pago`)
- [x] C6. Crear webhook de confirmacion Wompi con validacion de firma
- [x] C7. Crear pagina de resultado de pago (`pago_resultado.html`)
- [x] C8. Agregar banner vencimiento trial en dashboard
- [x] C9. Configurar settings (WOMPI_PUBLIC_KEY, WOMPI_SANDBOX, WOMPI_EVENTS_SECRET, WOMPI_INTEGRITY_SECRET)
- [x] C10. Tests de pagos (test_pagos.py)
- [x] C11. Emails de confirmacion post-pago (plan + addon)
- [x] C12. Comando simular_pago para pruebas sin pasarela real
- [x] C13. Precios todo-incluido (IVA incluido en precio mostrado)
- [x] C14. Calculadora de addons en pagina de planes
- [x] C15. Modal "Configurar Usuarios" en primer login post-compra
  - Escenario A: editar usuarios existentes post-compra de plan
  - Escenario B: crear usuarios nuevos post-compra de addons
  - Flags: configurar_usuarios_plan_pendiente + slots_usuarios_pendientes
  - Migracion 0067
- [ ] C16. Arreglar test fallido: test_sin_wompi_key_muestra_error
- [ ] C17. reCAPTCHA en formulario de registro trial (A7 pendiente)

### DEPLOY FINAL
- [x] D1. Desplegar en Render (activo en produccion)
- [x] D2. Wompi sandbox configurado y probado
- [x] D3. Contrato v1.1 cargado en BD
- [ ] D4. Correr suite completo de tests (1 fallo preexistente: test_sin_wompi_key)
- [ ] D5. Actualizar este documento al 100% al cerrar todos los pendientes

**Progreso general: 31/36 tareas completadas (86%)**
- Modulo A: 8/9 (89%) - falta reCAPTCHA
- Modulo B: 13/13 (100%)
- Modulo C: 15/17 (88%) - 1 test fallido, reCAPTCHA pendiente
- Deploy: 3/5

---

## Estructura de Archivos Implementados

```
sam-2/
  core/
    views/
      registro.py          # Auto-registro trial + asignar_permisos_por_rol
      onboarding.py        # API progreso onboarding
      pagos.py             # Planes, pago, addon, webhook Wompi, resultado
      admin.py             # + configurar_usuarios_setup (post-compra)
    models.py
      # Empresa: configurar_usuarios_plan_pendiente, slots_usuarios_pendientes
      # tiene_setup_usuarios_pendiente (property)
      # activar_plan_pagado() → activa flag configuracion
      # activar_addons()     → acumula slots por rol
      # OnboardingProgress, TransaccionPago
    urls.py
      # /solicitar-trial/, /trial-exitoso/
      # /onboarding/progreso/, /onboarding/completar-tour/
      # /planes/, /pagos/iniciar/, /pagos/iniciar-addon/
      # /pagos/resultado/, /pagos/webhook/, /pagos/no-disponible/
      # /usuarios/configurar-setup/
    migrations/
      0067_empresa_setup_usuarios_pendiente.py

  templates/core/
    planes.html              # Pagina de precios + calculadora addons
    pago_resultado.html      # Resultado exitoso/fallido
    partials/
      onboarding_checklist.html  # Widget checklist trial
      modal_setup_usuarios.html  # Modal post-compra (nuevo)
    dashboard.html
      # Banner trial vencimiento
      # Checklist onboarding
      # Modal setup usuarios (auto-abre si hay pendiente)

  core/management/commands/
    simular_pago.py    # Simula pago aprobado (plan o addon) para pruebas
    cargar_terminos_v11.py  # Carga/actualiza contrato v1.1 en BD

  tests/test_views/
    test_registro.py   # 39 tests registro trial
    test_onboarding.py # 41 tests onboarding
    test_pagos.py      # Tests pagos Wompi (1 fallo preexistente)
```

---

## Variables de Entorno en Produccion (Render)

```
WOMPI_PUBLIC_KEY          # Clave publica Wompi
WOMPI_PRIVATE_KEY         # Clave privada Wompi
WOMPI_INTEGRITY_SECRET    # Firma de integridad (checkout)
WOMPI_EVENTS_SECRET       # Firma de eventos (webhook)
WOMPI_SANDBOX             # True=sandbox, False=produccion
```

---

## Flujo Completo del Cliente

```
1. Cliente llega a /login/ → clic "Solicitar Trial Gratuito"
2. Llena formulario → empresa + 3 usuarios creados automaticamente
3. Onboarding guiado (Shepherd.js 21 pasos) + checklist en dashboard
4. Trial vence → banner rojo → clic "Ver planes"
5. Elige plan en /planes/ → redirige a Wompi checkout
6. Wompi aprueba → webhook → activar_plan_pagado() → email confirmacion
   └→ configurar_usuarios_plan_pendiente = True
7. Primer login post-compra → modal "Configurar Usuarios" auto-abre
8. Cliente personaliza cuentas → POST /usuarios/configurar-setup/
9. Dashboard limpio, plan activo

Addons:
5b. Clic "Agregar capacidad" → /planes/ seccion addons
6b. Wompi aprueba → activar_addons() → slots_usuarios_pendientes = {tecnicos:N}
7b. Primer login → modal sección B con filas vacias para crear usuarios
8b. Crea usuarios con rol+permisos → slots limpiados
```

---

## Pendientes

| # | Tarea | Prioridad |
|---|-------|-----------|
| 1 | Arreglar test_sin_wompi_key_muestra_error | Media |
| 2 | reCAPTCHA en formulario registro trial | Baja |

---

**Documento creado:** 2026-02-19
**Ultima actualizacion:** 2026-02-27
