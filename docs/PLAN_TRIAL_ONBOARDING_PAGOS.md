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
- [ ] A1. Crear formulario RegistroTrialForm (`core/forms/registro.py`)
- [ ] A2. Crear vista solicitar_trial (`core/views/registro.py`)
- [ ] A3. Crear template solicitar_trial.html
- [ ] A4. Crear template trial_exitoso.html
- [ ] A5. Agregar URLs en core/urls.py
- [ ] A6. Agregar boton "Solicitar Trial" en login.html
- [ ] A7. Configurar CAPTCHA (reCAPTCHA)
- [ ] A8. Tests de registro (15-18 tests)
- [ ] A9. Verificar 1,023+ tests pasan

### MODULO B: Onboarding Guiado
- [ ] B1. Crear modelo OnboardingProgress en models.py
- [ ] B2. Crear migracion y migrar
- [ ] B3. Crear signal auto-crear progreso al crear usuario trial
- [ ] B4. Integrar Shepherd.js (tour guiado)
- [ ] B5. Crear widget checklist en dashboard (partial template)
- [ ] B6. Crear vista API progreso onboarding (`core/views/onboarding.py`)
- [ ] B7. Marcar pasos en vistas existentes (4 vistas)
- [ ] B8. Incluir checklist en template dashboard.html
- [ ] B9. Tests de onboarding (12-15 tests)
- [ ] B10. Verificar 1,038+ tests pasan

### MODULO C: Pagos (PSE / Tarjeta)
- [ ] C1. Elegir pasarela y crear cuenta (Wompi/ePayco)
- [ ] C2. Crear modelo TransaccionPago en models.py
- [ ] C3. Crear migracion y migrar
- [ ] C4. Crear pagina de planes (`core/views/pagos.py` + template)
- [ ] C5. Crear endpoint inicio de pago
- [ ] C6. Crear webhook de confirmacion
- [ ] C7. Crear pagina de resultado de pago
- [ ] C8. Agregar banner vencimiento trial en dashboard
- [ ] C9. Configurar settings (claves pasarela)
- [ ] C10. Tests de pagos (18-22 tests)
- [ ] C11. Verificar 1,056+ tests pasan

### DEPLOY FINAL
- [ ] D1. Correr suite completo de tests
- [ ] D2. Actualizar este documento (marcar todo como completado)
- [ ] D3. Commit final y push a main
- [ ] D4. Desplegar en Render

**Progreso general: 0/33 tareas completadas**

---

## Estructura de Carpetas (donde va cada archivo nuevo)

```
sam-2/
  core/
    views/
      registro.py          # NUEVO - Vista publica de auto-registro (Modulo A)
      onboarding.py        # NUEVO - API de progreso onboarding (Modulo B)
      pagos.py             # NUEVO - Vistas de planes, pago, webhook (Modulo C)
    forms/
      registro.py          # NUEVO - Formulario de registro trial (Modulo A)
    models.py              # MODIFICAR - Agregar OnboardingProgress + TransaccionPago
    urls.py                # MODIFICAR - Agregar rutas nuevas

  templates/
    registration/
      solicitar_trial.html # NUEVO - Pagina publica de registro (Modulo A)
      trial_exitoso.html   # NUEVO - Confirmacion de registro (Modulo A)
    core/
      partials/
        onboarding_checklist.html  # NUEVO - Widget checklist en dashboard (Modulo B)
      planes.html          # NUEVO - Pagina de precios y planes (Modulo C)
      pago_resultado.html  # NUEVO - Resultado del pago (Modulo C)

  core/static/core/
    js/
      onboarding.js        # NUEVO - Configuracion Shepherd.js tours (Modulo B)
    css/
      onboarding.css       # NUEVO - Estilos del onboarding (Modulo B)

  tests/
    test_views/
      test_registro.py     # NUEVO - Tests de auto-registro (Modulo A)
      test_onboarding.py   # NUEVO - Tests de onboarding (Modulo B)
      test_pagos.py        # NUEVO - Tests de pagos y webhook (Modulo C)

  .github/workflows/
    weekly-dependency-audit.yml  # YA CREADO - Auditoria semanal de dependencias

  docs/
    PLAN_TRIAL_ONBOARDING_PAGOS.md  # ESTE DOCUMENTO
    DEPENDENCY_MANAGEMENT.md         # YA CREADO - Mantenimiento de dependencias
```

---

## MODULO A: Auto-registro de Trial

### Objetivo
El cliente llega a la pagina de login, da clic en "Solicitar Trial Gratuito",
llena un formulario y queda con su empresa creada y activa en menos de 2 minutos.

### Paso a paso de implementacion

#### Paso 1: Crear formulario de registro
**Archivo:** `core/forms/registro.py`

Campos del formulario:
- Nombre de la empresa (requerido)
- NIT (requerido, validar unicidad)
- Email corporativo (requerido, validar unicidad)
- Telefono (requerido)
- Nombre completo del administrador (requerido)
- Username (requerido, validar unicidad)
- Password + confirmacion (requerido, validar seguridad Django)

Validaciones:
- NIT no duplicado en BD
- Email no duplicado en BD
- Username no duplicado en BD
- Password cumple validadores de Django
- CAPTCHA (reCAPTCHA v3 o hCaptcha)

#### Paso 2: Crear vista de registro
**Archivo:** `core/views/registro.py`

Logica:
1. Recibir formulario (POST)
2. Validar CAPTCHA
3. Crear Empresa con configuracion trial:
   - es_periodo_prueba = True
   - duracion_prueba_dias = 30
   - fecha_inicio_plan = hoy
   - limite_equipos_empresa = 50
   - limite_almacenamiento_mb = 500
   - estado_suscripcion = 'Activo'
4. Crear CustomUser con rol ADMINISTRADOR asignado a la empresa
5. Enviar email de bienvenida (opcional fase 1)
6. Redirigir a pagina de exito con enlace al login

Decoradores: NINGUNO (vista publica, sin @login_required)

#### Paso 3: Crear templates
**Archivos:**
- `templates/registration/solicitar_trial.html` - Formulario de registro
- `templates/registration/trial_exitoso.html` - Pagina de confirmacion

El template de registro debe:
- Extender de `base_login.html` (misma estetica que login)
- Mostrar formulario con crispy forms
- Incluir script de reCAPTCHA
- Mostrar resumen del trial (30 dias, 50 equipos, gratis)

#### Paso 4: Configurar URLs
**Archivo:** `core/urls.py`

Agregar:
```python
path('solicitar-trial/', views.solicitar_trial, name='solicitar_trial'),
path('trial-exitoso/', views.trial_exitoso, name='trial_exitoso'),
```

#### Paso 5: Agregar enlace en login
**Archivo:** `templates/registration/login.html`

Agregar boton/enlace: "No tienes cuenta? Solicita tu trial gratuito de 30 dias"

#### Paso 6: Proteccion anti-abuso
- Instalar django-recaptcha: `pip install django-recaptcha`
- Configurar claves en settings.py (RECAPTCHA_PUBLIC_KEY, RECAPTCHA_PRIVATE_KEY)
- Rate limiting: maximo 5 registros por IP por hora (usar middleware existente)

#### Paso 7: Tests
**Archivo:** `tests/test_views/test_registro.py`

Tests necesarios (~15-18):
- GET muestra formulario correctamente
- POST con datos validos crea empresa + usuario
- POST con NIT duplicado muestra error
- POST con email duplicado muestra error
- POST con username duplicado muestra error
- POST con password debil muestra error
- Empresa creada tiene configuracion trial correcta
- Usuario creado tiene rol ADMINISTRADOR
- Usuario creado esta asignado a la empresa
- Redireccion a pagina de exito
- CAPTCHA invalido rechaza registro
- Rate limiting bloquea multiples intentos
- Vista es publica (no requiere login)
- Usuario autenticado es redirigido al dashboard

### Requisitos previos
- [ ] Cuenta de Google reCAPTCHA (gratis): https://www.google.com/recaptcha/admin
- [ ] Configurar EMAIL_HOST en settings.py (si no esta configurado)

### Riesgos y mitigaciones
| Riesgo | Mitigacion |
|---|---|
| Bots crean empresas masivamente | reCAPTCHA + rate limiting |
| NIT/emails falsos | Verificacion email (fase 2) |
| Abuso de trials repetidos | Bloquear NIT/email ya usados |

---

## MODULO B: Onboarding Guiado

### Objetivo
Cuando un usuario de trial entra por primera vez, la plataforma lo guia con
tooltips interactivos y una checklist de tareas en el dashboard.

### Paso a paso de implementacion

#### Paso 1: Crear modelo OnboardingProgress
**Archivo:** `core/models.py` (agregar al final)

```
OnboardingProgress:
  - usuario (FK a CustomUser, unique)
  - tour_completado (BooleanField, default=False)
  - paso_crear_equipo (BooleanField, default=False)
  - paso_registrar_calibracion (BooleanField, default=False)
  - paso_generar_reporte (BooleanField, default=False)
  - paso_agregar_usuario (BooleanField, default=False)
  - fecha_inicio (DateTimeField, auto_now_add)
  - fecha_completado (DateTimeField, nullable)
```

#### Paso 2: Crear migracion
```bash
python manage.py makemigrations core
python manage.py migrate
```

#### Paso 3: Crear signal para auto-crear progreso
**Archivo:** `core/signals.py` (agregar)

Cuando se crea un CustomUser con empresa en trial, auto-crear OnboardingProgress.

#### Paso 4: Integrar Shepherd.js
**Archivo:** `core/static/core/js/onboarding.js`

Configurar tour guiado:
1. "Bienvenido a SAM Metrologia" - señalar dashboard
2. "Aqui ves el resumen de tus equipos" - señalar estadisticas
3. "Crea tu primer equipo aqui" - señalar boton de crear equipo
4. "Aqui programas calibraciones" - señalar menu de actividades
5. "Genera reportes PDF/Excel" - señalar seccion de reportes

Libreria: Shepherd.js (MIT, ~12KB gzip)
Instalacion: descargar o usar CDN

#### Paso 5: Crear widget checklist en dashboard
**Archivo:** `templates/core/partials/onboarding_checklist.html`

Mostrar en el dashboard (solo para usuarios en trial):
- [ ] Crear tu primer equipo
- [ ] Registrar una calibracion
- [ ] Generar un reporte
- [ ] Agregar un usuario a tu empresa
- Barra de progreso (0%, 25%, 50%, 75%, 100%)
- Boton "Repetir tour guiado"

#### Paso 6: Crear vista API para actualizar progreso
**Archivo:** `core/views/onboarding.py`

Endpoints:
- GET `/onboarding/progress/` - Retorna estado actual del onboarding
- POST `/onboarding/complete-step/` - Marca un paso como completado

Estos se llaman automaticamente cuando el usuario completa acciones
(crear equipo, registrar calibracion, etc.) via señales o en las vistas existentes.

#### Paso 7: Modificar vistas existentes para marcar pasos
Agregar al final de:
- `views/equipment.py` → `añadir_equipo()`: marcar paso_crear_equipo
- `views/confirmacion.py` → crear calibracion: marcar paso_registrar_calibracion
- `views/reports.py` → generar reporte: marcar paso_generar_reporte
- `views/admin.py` → `añadir_usuario()`: marcar paso_agregar_usuario

Son 4 lineas de codigo (una por vista).

#### Paso 8: Incluir en template del dashboard
**Archivo:** `templates/core/dashboard.html`

Agregar condicional:
```
{% if onboarding_progress and not onboarding_progress.tour_completado %}
  {% include 'core/partials/onboarding_checklist.html' %}
{% endif %}
```

#### Paso 9: Tests
**Archivo:** `tests/test_views/test_onboarding.py`

Tests necesarios (~12-15):
- OnboardingProgress se crea al crear usuario trial
- No se crea para usuarios de empresa pagada
- Tour se marca como completado
- Cada paso se marca correctamente
- Checklist aparece en dashboard para trial
- Checklist NO aparece para empresas pagadas
- Checklist desaparece al completar todo
- API retorna progreso correcto
- Crear equipo marca paso automaticamente
- Generar reporte marca paso automaticamente

### Requisitos previos
- [ ] Descargar Shepherd.js (o usar CDN)
- [ ] Identificar IDs/clases CSS de elementos del dashboard para anclar tooltips

### Riesgos y mitigaciones
| Riesgo | Mitigacion |
|---|---|
| Tooltips no se anclan bien | Usar IDs estables en templates |
| Shepherd.js incompatible con Bootstrap | Testear en navegadores principales |
| Checklist molesta a usuarios avanzados | Boton "Omitir" visible |

---

## MODULO C: Pagos (PSE / Tarjeta)

### Objetivo
Cuando el trial de 30 dias vence, el cliente ve una pagina de planes con precios
y puede pagar directamente con PSE o tarjeta de credito.

### Paso a paso de implementacion

#### Paso 1: Elegir e integrar pasarela de pagos

Opciones evaluadas:

| Pasarela | PSE | Tarjeta | Comision | Recomendacion |
|---|---|---|---|---|
| **Wompi** | Si | Si | 2.5% + IVA | Recomendada (Bancolombia, facil) |
| **ePayco** | Si | Si | 2.99% + IVA | Alternativa solida |
| **PayU** | Si | Si | 3.49% + IVA | Madura pero mas compleja |

Accion: Crear cuenta en la pasarela elegida (3-10 dias habiles de aprobacion).

#### Paso 2: Crear modelo TransaccionPago
**Archivo:** `core/models.py` (agregar al final)

```
TransaccionPago:
  - empresa (FK a Empresa)
  - referencia_pago (CharField, unique) - ID de la pasarela
  - estado (CharField: pendiente/aprobado/rechazado/error)
  - monto (DecimalField)
  - moneda (CharField, default='COP')
  - metodo_pago (CharField: PSE/tarjeta/efectivo)
  - plan_seleccionado (CharField: MENSUAL/ANUAL)
  - fecha_creacion (DateTimeField, auto_now_add)
  - fecha_actualizacion (DateTimeField, auto_now)
  - datos_respuesta (JSONField, nullable) - respuesta completa de la pasarela
  - ip_cliente (GenericIPAddressField, nullable)
```

#### Paso 3: Crear migracion
```bash
python manage.py makemigrations core
python manage.py migrate
```

#### Paso 4: Crear pagina de planes
**Archivo:** `core/views/pagos.py` + `templates/core/planes.html`

Mostrar (segun contrato vigente):
| Plan | Precio | Detalle |
|---|---|---|
| Mensual | $200.000 COP/mes + IVA | 3 usuarios, 200 equipos, 4 GB |
| Anual | $2.000.000 COP/ano + IVA | 3 usuarios, 200 equipos, 4 GB |

Boton "Pagar con PSE" y "Pagar con tarjeta" que redirigen a la pasarela.

#### Paso 5: Crear endpoint de inicio de pago
**Archivo:** `core/views/pagos.py`

Logica:
1. Usuario selecciona plan
2. Crear TransaccionPago con estado 'pendiente'
3. Generar URL de pago en la pasarela (API call)
4. Redirigir al usuario a la pasarela

#### Paso 6: Crear webhook de confirmacion
**Archivo:** `core/views/pagos.py`

Endpoint: POST `/pagos/webhook/` (csrf_exempt, validar firma)

Logica:
1. Recibir notificacion de la pasarela
2. Validar firma/checksum (CRITICO - evitar pagos falsos)
3. Buscar TransaccionPago por referencia
4. Si aprobado:
   - Actualizar TransaccionPago.estado = 'aprobado'
   - Llamar empresa.activar_plan_pagado()
   - Actualizar limites segun plan
   - Enviar email de confirmacion
5. Si rechazado: actualizar estado, notificar usuario

#### Paso 7: Crear pagina de resultado
**Archivo:** `templates/core/pago_resultado.html`

Mostrar: "Pago exitoso, tu plan esta activo" o "Pago rechazado, intenta de nuevo"

#### Paso 8: Agregar banner de vencimiento
**Modificar:** `templates/core/dashboard.html`

Cuando el trial esta por vencer (ultimos 5 dias) o ya vencio:
- Banner amarillo: "Tu trial vence en X dias. Elige tu plan"
- Banner rojo (vencido): "Tu trial vencio. Activa tu plan para continuar"
- Enlace a pagina de planes

#### Paso 9: Configurar settings
**Archivo:** `proyecto_c/settings.py`

Agregar variables de entorno:
```python
PAYMENT_GATEWAY_PUBLIC_KEY = os.environ.get('PAYMENT_GATEWAY_PUBLIC_KEY', '')
PAYMENT_GATEWAY_PRIVATE_KEY = os.environ.get('PAYMENT_GATEWAY_PRIVATE_KEY', '')
PAYMENT_GATEWAY_WEBHOOK_SECRET = os.environ.get('PAYMENT_GATEWAY_WEBHOOK_SECRET', '')
PAYMENT_GATEWAY_SANDBOX = os.environ.get('PAYMENT_GATEWAY_SANDBOX', 'True') == 'True'
```

#### Paso 10: Tests
**Archivo:** `tests/test_views/test_pagos.py`

Tests necesarios (~18-22):
- Pagina de planes muestra precios correctos
- Solo usuarios autenticados ven la pagina de planes
- Crear transaccion pendiente correctamente
- Webhook con firma valida procesa pago
- Webhook con firma invalida rechaza (401)
- Webhook duplicado es idempotente (no doble cobro)
- Pago aprobado activa plan de empresa
- Pago aprobado actualiza limites (equipos, almacenamiento)
- Pago rechazado no activa plan
- TransaccionPago registra IP del cliente
- TransaccionPago registra datos de respuesta
- Banner de vencimiento aparece en ultimos 5 dias
- Banner NO aparece para empresas con plan activo
- Empresa con trial vencido ve banner rojo
- Redirect correcto despues de pago exitoso
- Redirect correcto despues de pago fallido

### Requisitos previos
- [ ] Cuenta aprobada en pasarela de pagos (Wompi, ePayco, o PayU)
- [ ] Credenciales sandbox para desarrollo
- [ ] Credenciales produccion para deploy
- [ ] URL publica para webhook (Render la provee)
- [ ] Revisar si el contrato necesita actualizacion para pagos electronicos

### Riesgos y mitigaciones
| Riesgo | Mitigacion |
|---|---|
| Pagos falsos via webhook | Validar firma criptografica de la pasarela |
| Doble cobro | Idempotencia por referencia_pago unica |
| Pasarela caida | Mostrar "intenta mas tarde" + opcion transferencia manual |
| IVA mal calculado | Calcular en backend, no en frontend |

---

## Resumen de esfuerzo total

| Concepto | Modulo A | Modulo B | Modulo C | Total |
|---|---|---|---|---|
| Archivos nuevos | 4 | 4 | 4 | 12 |
| Archivos modificados | 3 | 5 | 3 | 11 |
| Lineas de codigo estimadas | ~340 | ~230 | ~400 | ~970 |
| Tests nuevos | 15-18 | 12-15 | 18-22 | 45-55 |
| Modelos nuevos | 0 | 1 | 1 | 2 |
| Migraciones | 0 | 1 | 1 | 2 |
| Dependencias nuevas | django-recaptcha | shepherd.js (CDN) | SDK pasarela | 3 |

## Impacto en infraestructura (Render $48.50/mes)

| Recurso | Impacto |
|---|---|
| RAM servicio (512MB) | +5MB max - sin problema |
| RAM BD (1GB) | Despreciable - 2 tablas pequenas |
| Disco BD (15GB) | < 1MB adicional |
| Bandwidth | +2-5 MB/mes |
| **Conclusion** | No requiere subir de plan |

---

**Documento creado:** 2026-02-19
**Ultima actualizacion:** 2026-02-19
