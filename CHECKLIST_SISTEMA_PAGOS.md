# ✅ CHECKLIST MAESTRO - SISTEMA DE PAGOS Y SUSCRIPCIONES SAM METROLOGÍA

**Última actualización:** 3 de Octubre de 2025
**Basado en:** Contrato de Licencia SaaS - Versión 1: 2025/10/01

---

## 📋 ÍNDICE DE FASES

- [FASE 0: Preparación y Decisiones](#fase-0-preparación-y-decisiones)
- [FASE 1: Términos y Condiciones](#fase-1-términos-y-condiciones-obligatorio)
- [FASE 2: Sistema de Paquetes Adicionales](#fase-2-sistema-de-paquetes-adicionales-escalabilidad)
- [FASE 3: Monitoreo de Uso y Límites](#fase-3-monitoreo-de-uso-y-límites)
- [FASE 4: Notificaciones Automáticas](#fase-4-notificaciones-automáticas)
- [FASE 5: Panel de Suscripción del Cliente](#fase-5-panel-de-suscripción-del-cliente)
- [FASE 6: Pasarela de Pagos](#fase-6-pasarela-de-pagos-mercadopago-o-stripe)
- [FASE 7: Facturación Electrónica DIAN](#fase-7-facturación-electrónica-dian)
- [FASE 8: Automatización y Cron Jobs](#fase-8-automatización-y-cron-jobs)
- [FASE 9: Testing y Lanzamiento](#fase-9-testing-y-lanzamiento)

---

## FASE 0: Preparación y Decisiones
**Tiempo estimado:** 1-2 días
**Responsable:** Equipo de gerencia

### Decisiones Críticas a Tomar

- [ ] **0.1** Decidir pasarela de pagos
  - [ ] MercadoPago (recomendado para Colombia)
  - [ ] Stripe
  - [ ] PayU
  - [ ] Otro: ___________

- [ ] **0.2** Decidir sistema de facturación electrónica
  - [ ] API externa (Alegra, Siigo) - Recomendado
  - [ ] Implementación propia con certificado DIAN
  - [ ] Manual (no recomendado)

- [ ] **0.3** Verificar requisitos técnicos
  - [ ] Certificado SSL activo en producción (https://)
  - [ ] Email corporativo configurado para envíos masivos
  - [ ] Acceso a servidor para configurar cron jobs
  - [ ] Backup de base de datos antes de empezar

- [ ] **0.4** Preparar documentación legal
  - [ ] Contrato PDF firmado digitalmente
  - [ ] Logo de la empresa en alta resolución
  - [ ] Información bancaria para recibir pagos

---

## FASE 1: Términos y Condiciones (OBLIGATORIO)
**Tiempo estimado:** 3-5 días
**Prioridad:** 🔴 ALTA - Empezar AHORA mientras se decide sobre pagos
**Cláusula del contrato:** 11.1, 13.1

### 1.1 Modelo de Base de Datos

- [ ] **1.1.1** Crear modelo `TerminosYCondiciones`
  ```python
  - version (CharField) ej: "1.0"
  - fecha_vigencia (DateField) ej: 2025-10-01
  - titulo (CharField)
  - contenido_html (TextField) - Contenido formateado
  - archivo_pdf (FileField) - PDF del contrato
  - activo (BooleanField) - Solo una versión activa a la vez
  - created_at (DateTimeField)
  ```

- [ ] **1.1.2** Crear modelo `AceptacionTerminos`
  ```python
  - usuario (ForeignKey CustomUser)
  - terminos (ForeignKey TerminosYCondiciones)
  - empresa (ForeignKey Empresa)
  - fecha_aceptacion (DateTimeField)
  - ip_address (GenericIPAddressField)
  - user_agent (TextField)
  - aceptado (BooleanField)
  ```

- [ ] **1.1.3** Crear y aplicar migración
  ```bash
  python manage.py makemigrations
  python manage.py migrate
  ```

### 1.2 Vista de Términos y Condiciones

- [ ] **1.2.1** Crear template `terminos_condiciones.html`
  - [ ] Mostrar PDF del contrato (iframe o visor)
  - [ ] Checkbox "He leído y acepto los términos"
  - [ ] Botón "Aceptar y Continuar"
  - [ ] Botón "Rechazar y Cerrar Sesión"
  - [ ] Diseño responsivo (móvil/desktop)

- [ ] **1.2.2** Crear vista `aceptar_terminos`
  - [ ] Verificar si usuario ya aceptó versión actual
  - [ ] Capturar IP del usuario
  - [ ] Capturar User-Agent del navegador
  - [ ] Guardar timestamp de aceptación
  - [ ] Redirigir al dashboard después de aceptar

- [ ] **1.2.3** Crear URL `/terminos-condiciones/`

### 1.3 Middleware de Verificación

- [ ] **1.3.1** Crear `TerminosMiddleware`
  - [ ] Verificar en cada request si usuario está autenticado
  - [ ] Verificar si aceptó términos actuales
  - [ ] Excepciones: /terminos-condiciones/, /logout/, /static/, /media/
  - [ ] Redirigir a página de términos si no aceptó

- [ ] **1.3.2** Agregar middleware a `settings.py`
  ```python
  MIDDLEWARE = [
      ...
      'core.middleware.TerminosMiddleware',
  ]
  ```

### 1.4 Comando de Administración

- [ ] **1.4.1** Crear comando `cargar_terminos_iniciales`
  ```bash
  python manage.py cargar_terminos_iniciales
  ```
  - [ ] Sube el PDF del contrato
  - [ ] Crea versión 1.0 de términos
  - [ ] Marca como activo

### 1.5 Testing de Términos

- [ ] **1.5.1** Probar flujo completo
  - [ ] Usuario nuevo → Debe ver términos
  - [ ] Usuario acepta → Puede acceder al sistema
  - [ ] Usuario rechaza → Se cierra sesión
  - [ ] Usuario que ya aceptó → No se le vuelve a pedir

- [ ] **1.5.2** Verificar registro en base de datos
  - [ ] IP guardada correctamente
  - [ ] Timestamp correcto
  - [ ] Relación usuario-términos correcta

---

## FASE 2: Sistema de Paquetes Adicionales (ESCALABILIDAD)
**Tiempo estimado:** 1 semana
**Prioridad:** 🟡 MEDIA-ALTA
**Cláusula del contrato:** 3.4, 3.5

### 2.1 Modelo de Paquetes Adicionales

- [ ] **2.1.1** Crear modelo `PaqueteAdicional`
  ```python
  - tipo (CharField) choices: ['USUARIOS', 'EQUIPOS', 'ALMACENAMIENTO']
  - cantidad (IntegerField) ej: 2 usuarios, 50 equipos, 2GB
  - precio_mensual (DecimalField) ej: 50000, 100000, 50000
  - descripcion (TextField)
  - activo (BooleanField)
  ```

- [ ] **2.1.2** Crear modelo `PaqueteContratado`
  ```python
  - empresa (ForeignKey Empresa)
  - paquete (ForeignKey PaqueteAdicional)
  - cantidad_paquetes (IntegerField) - Cuántos paquetes contrató
  - fecha_inicio (DateField)
  - fecha_fin (DateField, null=True) - Si cancela
  - activo (BooleanField)
  - created_at (DateTimeField)
  ```

- [ ] **2.1.3** Crear modelo `ExcesoLimite` (Historial)
  ```python
  - empresa (ForeignKey Empresa)
  - tipo_limite (CharField) choices: ['USUARIOS', 'EQUIPOS', 'ALMACENAMIENTO']
  - limite_actual (IntegerField)
  - cantidad_usada (IntegerField)
  - cantidad_exceso (IntegerField)
  - fecha_deteccion (DateTimeField)
  - dias_consecutivos (IntegerField) - Contador para regla de 7 días
  - estado (CharField) choices: ['DETECTADO', 'NOTIFICADO', 'FACTURADO', 'RESUELTO']
  - notificacion_enviada (BooleanField)
  - paquete_sugerido (ForeignKey PaqueteAdicional, null=True)
  ```

- [ ] **2.1.4** Crear y aplicar migraciones

### 2.2 Métodos del Modelo Empresa

- [ ] **2.2.1** Método `get_limite_usuarios_total()`
  ```python
  # Límite base (3) + paquetes contratados
  # Retornar número total de usuarios permitidos
  ```

- [ ] **2.2.2** Método `get_limite_equipos_total()`
  ```python
  # Límite base (50) + paquetes contratados de equipos
  # Retornar número total de equipos permitidos
  ```

- [ ] **2.2.3** Método `get_limite_almacenamiento_total_mb()`
  ```python
  # Límite base (2GB) + paquetes contratados de almacenamiento
  # Retornar MB totales permitidos
  ```

- [ ] **2.2.4** Método `get_usuarios_activos_count()`
  ```python
  # Contar usuarios activos de la empresa
  ```

- [ ] **2.2.5** Método `get_equipos_count()`
  ```python
  # Contar equipos registrados (ya existe pero verificar)
  ```

- [ ] **2.2.6** Método `get_almacenamiento_usado_mb()`
  ```python
  # Calcular almacenamiento usado en MB (ya existe pero optimizar)
  ```

- [ ] **2.2.7** Método `verificar_excesos()`
  ```python
  # Verificar si hay excesos en usuarios, equipos o almacenamiento
  # Retornar dict con excesos detectados
  ```

### 2.3 Sistema de Detección de Excesos

- [ ] **2.3.1** Crear servicio `ExcesoService`
  - [ ] `detectar_excesos(empresa)` - Detecta excesos actuales
  - [ ] `registrar_exceso(empresa, tipo, cantidad)` - Registra en BD
  - [ ] `verificar_dias_consecutivos(empresa, tipo)` - Contador de 7 días
  - [ ] `sugerir_paquete(empresa, tipo, exceso)` - Calcula paquete necesario
  - [ ] `marcar_para_facturacion(empresa, exceso)` - Marca para cobrar

- [ ] **2.3.2** Integrar verificación en puntos clave
  - [ ] Al crear nuevo usuario → Verificar límite usuarios
  - [ ] Al crear nuevo equipo → Verificar límite equipos
  - [ ] Al subir archivo → Verificar límite almacenamiento
  - [ ] Mostrar advertencia si está cerca del límite (80%)

### 2.4 Comandos de Administración

- [ ] **2.4.1** Comando `cargar_paquetes_adicionales`
  ```bash
  python manage.py cargar_paquetes_adicionales
  ```
  - [ ] Crea paquete: 2 Usuarios × $50.000
  - [ ] Crea paquete: 50 Equipos × $100.000
  - [ ] Crea paquete: 2GB Almacenamiento × $50.000

- [ ] **2.4.2** Comando `verificar_excesos_todas_empresas`
  ```bash
  python manage.py verificar_excesos_todas_empresas
  ```
  - [ ] Recorre todas las empresas activas
  - [ ] Detecta excesos de usuarios, equipos, almacenamiento
  - [ ] Registra en tabla ExcesoLimite
  - [ ] Incrementa contador de días consecutivos
  - [ ] Si llega a 7 días → Marca para facturación

### 2.5 Testing de Paquetes

- [ ] **2.5.1** Probar límites base
  - [ ] Empresa nueva: 3 usuarios, 50 equipos, 2GB
  - [ ] Intentar crear usuario #4 → Debe bloquear o advertir

- [ ] **2.5.2** Probar paquetes adicionales
  - [ ] Contratar paquete de 2 usuarios
  - [ ] Verificar nuevo límite: 5 usuarios
  - [ ] Permitir crear usuarios 4 y 5

- [ ] **2.5.3** Probar detección de excesos
  - [ ] Crear exceso temporal (6 días)
  - [ ] Verificar que NO se factura
  - [ ] Mantener exceso 7 días
  - [ ] Verificar que SÍ se marca para facturación

---

## FASE 3: Monitoreo de Uso y Límites
**Tiempo estimado:** 3-4 días
**Prioridad:** 🟡 MEDIA-ALTA
**Cláusula del contrato:** 3.5

### 3.1 Dashboard de Uso para Empresa

- [ ] **3.1.1** Crear widget "Uso de Recursos"
  - [ ] Barra de progreso: Usuarios (3/5)
  - [ ] Barra de progreso: Equipos (45/50)
  - [ ] Barra de progreso: Almacenamiento (1.5GB/2GB)
  - [ ] Indicador de color: Verde (<80%), Amarillo (80-99%), Rojo (100%+)

- [ ] **3.1.2** Agregar al dashboard principal
  - [ ] Ubicación destacada (sidebar o header)
  - [ ] Actualización en tiempo real

### 3.2 Alertas Visuales

- [ ] **3.2.1** Notificación al 80% de límite
  - [ ] Banner amarillo: "Estás usando el 80% de tus equipos"
  - [ ] Botón "Ampliar Plan"

- [ ] **3.2.2** Notificación al 100% de límite
  - [ ] Banner rojo: "Has alcanzado el límite de equipos"
  - [ ] Bloquear creación de nuevos equipos
  - [ ] Botón "Contratar Paquete Adicional"

### 3.3 Modal de Sugerencia de Paquete

- [ ] **3.3.1** Modal cuando se intenta exceder límite
  ```
  "Has alcanzado el límite de 50 equipos"
  "Te recomendamos contratar el paquete de 50 equipos adicionales"
  "Precio: $100.000/mes"
  [Contratar Paquete] [Cancelar]
  ```

---

## FASE 4: Notificaciones Automáticas
**Tiempo estimado:** 3 días
**Prioridad:** 🟢 MEDIA
**Cláusula del contrato:** 3.5

### 4.1 Templates de Email

- [ ] **4.1.1** Email: "Estás cerca del límite" (80%)
  - [ ] Asunto: "SAM Metrología - Uso de recursos al 80%"
  - [ ] Contenido: Detalle de uso actual, paquetes sugeridos
  - [ ] CTA: "Ver Paquetes Adicionales"

- [ ] **4.1.2** Email: "Has excedido el límite"
  - [ ] Asunto: "SAM Metrología - Límite de recursos alcanzado"
  - [ ] Contenido: Explicar que si se mantiene 7 días se facturará
  - [ ] CTA: "Contratar Paquete Ahora"

- [ ] **4.1.3** Email: "Se agregará cargo adicional"
  - [ ] Asunto: "SAM Metrología - Cargo adicional en próxima factura"
  - [ ] Contenido: Detalle del exceso y monto adicional
  - [ ] Detalle de facturación

### 4.2 Sistema de Envío

- [ ] **4.2.1** Servicio `NotificacionService`
  - [ ] `enviar_alerta_80_porciento(empresa, tipo_recurso)`
  - [ ] `enviar_alerta_exceso(empresa, tipo_recurso, dias)`
  - [ ] `enviar_confirmacion_facturacion(empresa, exceso, monto)`

- [ ] **4.2.2** Configurar Celery (opcional pero recomendado)
  - [ ] Instalar Celery + Redis
  - [ ] Configurar tareas asíncronas
  - [ ] Enviar emails en background

---

## FASE 5: Panel de Suscripción del Cliente
**Tiempo estimado:** 1 semana
**Prioridad:** 🟡 MEDIA-ALTA
**Cláusula del contrato:** 3.1, 3.3, 8.1

### 5.1 Página "Mi Suscripción"

- [ ] **5.1.1** Crear template `mi_suscripcion.html`
  - [ ] Sección: Plan Actual
    - [ ] Tipo de plan (Mensual / Anual)
    - [ ] Fecha de inicio
    - [ ] Fecha de próximo pago
    - [ ] Estado (Activo, Trial, Expirado)

  - [ ] Sección: Recursos Incluidos
    - [ ] Usuarios: 3 (Base) + 2 (Adicional) = 5 total
    - [ ] Equipos: 50 (Base) + 50 (Adicional) = 100 total
    - [ ] Almacenamiento: 2GB (Base) + 2GB (Adicional) = 4GB total

  - [ ] Sección: Paquetes Adicionales Contratados
    - [ ] Tabla con paquetes activos
    - [ ] Botón "Cancelar Paquete"

  - [ ] Sección: Disponibles para Contratar
    - [ ] Tarjetas de paquetes no contratados
    - [ ] Precio, descripción, botón "Contratar"

- [ ] **5.1.2** Crear vista `mi_suscripcion`
  - [ ] Cargar datos de empresa del usuario
  - [ ] Calcular límites totales
  - [ ] Obtener paquetes disponibles
  - [ ] Renderizar template

- [ ] **5.1.3** Crear URL `/mi-suscripcion/`

### 5.2 Contratar Paquete Adicional

- [ ] **5.2.1** Vista `contratar_paquete_adicional`
  - [ ] Recibir ID del paquete a contratar
  - [ ] Validar que empresa puede contratar
  - [ ] Redirigir a checkout de pago

- [ ] **5.2.2** Vista `cancelar_paquete_adicional`
  - [ ] Recibir ID del paquete contratado
  - [ ] Confirmar cancelación
  - [ ] Marcar paquete como inactivo (fecha_fin = hoy)
  - [ ] Notificar que se aplicará en próximo ciclo

### 5.3 Historial de Pagos

- [ ] **5.3.1** Crear modelo `Pago`
  ```python
  - empresa (ForeignKey Empresa)
  - fecha_pago (DateTimeField)
  - monto (DecimalField)
  - concepto (TextField)
  - metodo_pago (CharField) choices: ['MERCADOPAGO', 'PSE', 'TARJETA', 'TRANSFERENCIA']
  - estado (CharField) choices: ['PENDIENTE', 'APROBADO', 'RECHAZADO']
  - referencia_externa (CharField) - ID de MercadoPago/Stripe
  - factura_url (URLField, null=True)
  ```

- [ ] **5.3.2** Sección en "Mi Suscripción"
  - [ ] Tabla con historial de pagos
  - [ ] Columnas: Fecha, Concepto, Monto, Estado
  - [ ] Botón "Descargar Factura" (si tiene)

---

## FASE 6: Pasarela de Pagos (MercadoPago o Stripe)
**Tiempo estimado:** 2-3 semanas
**Prioridad:** 🔴 ALTA (después de decidir proveedor)
**Cláusula del contrato:** 9.2

### 6.1 Configuración Inicial

- [ ] **6.1.1** Crear cuenta en pasarela elegida
  - [ ] MercadoPago Business
  - [ ] O Stripe Connect
  - [ ] Verificar identidad y cuenta bancaria

- [ ] **6.1.2** Obtener credenciales
  - [ ] Access Token / API Key (producción)
  - [ ] Access Token / API Key (sandbox/pruebas)
  - [ ] Guardar en variables de entorno

- [ ] **6.1.3** Instalar SDK
  ```bash
  pip install mercadopago  # O pip install stripe
  pip freeze > requirements.txt
  ```

- [ ] **6.1.4** Configurar en `settings.py`
  ```python
  MERCADOPAGO_ACCESS_TOKEN = os.environ.get('MERCADOPAGO_ACCESS_TOKEN')
  MERCADOPAGO_PUBLIC_KEY = os.environ.get('MERCADOPAGO_PUBLIC_KEY')
  ```

### 6.2 Página de Selección de Plan

- [ ] **6.2.1** Crear template `seleccionar_plan.html`
  - [ ] Tarjeta Plan Mensual
    - [ ] Título: "Plan Mensual"
    - [ ] Precio: $180.000 COP/mes
    - [ ] Incluye: 3 usuarios, 50 equipos, 2GB
    - [ ] Botón: "Seleccionar Mensual"

  - [ ] Tarjeta Plan Anual (destacada)
    - [ ] Título: "Plan Anual (2 meses gratis)"
    - [ ] Precio: $1.800.000 COP/año
    - [ ] Precio equivalente: $150.000/mes
    - [ ] Badge: "Ahorra $360.000"
    - [ ] Incluye: 3 usuarios, 50 equipos, 2GB
    - [ ] Botón: "Seleccionar Anual"

- [ ] **6.2.2** Vista `seleccionar_plan`
  - [ ] Verificar que empresa está en trial o expirada
  - [ ] Renderizar opciones de planes

### 6.3 Checkout (Página de Pago)

- [ ] **6.3.1** Crear template `checkout.html`
  - [ ] Resumen del pedido
    - [ ] Plan seleccionado
    - [ ] Subtotal: $180.000 (o $1.800.000)
    - [ ] IVA 19%: $34.200 (o $342.000)
    - [ ] Total: $214.200 (o $2.142.000)

  - [ ] Datos de facturación
    - [ ] NIT/CC (pre-llenado de empresa)
    - [ ] Razón Social (pre-llenado)
    - [ ] Email de facturación
    - [ ] Dirección

  - [ ] Botón "Proceder al Pago"

- [ ] **6.3.2** Vista `checkout`
  ```python
  - Recibir tipo de plan (mensual/anual)
  - Calcular monto + IVA
  - Renderizar formulario
  ```

### 6.4 Integración con Pasarela

- [ ] **6.4.1** Vista `crear_preferencia_pago`
  ```python
  # Si MercadoPago:
  - Crear preferencia de pago
  - Configurar URLs de retorno (success, failure, pending)
  - Configurar notification_url (webhook)
  - Redirigir a init_point de MercadoPago

  # Si Stripe:
  - Crear Checkout Session
  - Configurar success_url y cancel_url
  - Redirigir a Stripe Checkout
  ```

- [ ] **6.4.2** URLs de retorno
  - [ ] `/pago/exito/` - Pago aprobado
  - [ ] `/pago/pendiente/` - Pago pendiente (PSE)
  - [ ] `/pago/fallo/` - Pago rechazado

- [ ] **6.4.3** Vista `pago_exito`
  - [ ] Mostrar mensaje de confirmación
  - [ ] "Tu pago está siendo procesado"
  - [ ] "Recibirás confirmación por email"
  - [ ] Botón "Ir al Dashboard"

- [ ] **6.4.4** Vista `pago_fallo`
  - [ ] Mostrar mensaje de error
  - [ ] Botón "Reintentar Pago"

### 6.5 Webhooks (Confirmación Asíncrona)

- [ ] **6.5.1** Vista `webhook_mercadopago` (o `webhook_stripe`)
  ```python
  @csrf_exempt
  def webhook_mercadopago(request):
      # Verificar firma/autenticidad del webhook
      # Obtener datos del pago
      # Verificar estado del pago
      # Si aprobado:
      #   - Actualizar estado_suscripcion de Empresa
      #   - Crear registro en modelo Pago
      #   - Actualizar fecha_ultimo_pago
      #   - Calcular fecha_proximo_pago
      #   - Generar factura electrónica
      #   - Enviar email de confirmación
      # Retornar status 200
  ```

- [ ] **6.5.2** Configurar URL pública para webhook
  - [ ] `/webhooks/mercadopago/` (o `/webhooks/stripe/`)
  - [ ] Asegurar que es accesible desde internet
  - [ ] Registrar URL en dashboard de pasarela

- [ ] **6.5.3** Seguridad del webhook
  - [ ] Verificar firma/secret
  - [ ] Validar IP de origen
  - [ ] Prevenir ataques de replay

### 6.6 Testing de Pagos

- [ ] **6.6.1** Modo Sandbox/Test
  - [ ] Realizar pago de prueba con tarjeta test
  - [ ] Verificar que webhook se ejecuta
  - [ ] Verificar que empresa se activa

- [ ] **6.6.2** Casos de prueba
  - [ ] Pago aprobado → Empresa activa
  - [ ] Pago rechazado → Empresa sigue inactiva
  - [ ] Pago pendiente (PSE) → Esperar confirmación

---

## FASE 7: Facturación Electrónica DIAN
**Tiempo estimado:** 2-3 semanas (con API externa) o 4-6 semanas (propia)
**Prioridad:** 🟡 MEDIA (puede ser después de pagos)
**Cláusula del contrato:** 3.6, 9.3

### 7.1 Decisión de Implementación

- [ ] **7.1.1** Si se elige API externa (Alegra, Siigo, Facturama)
  - [ ] Crear cuenta en el proveedor elegido
  - [ ] Verificar con RUT, Cámara de Comercio
  - [ ] Obtener API Key
  - [ ] Revisar documentación de API

- [ ] **7.1.2** Si se elige implementación propia
  - [ ] Obtener certificado digital ante DIAN
  - [ ] Configurar resolución de facturación
  - [ ] Implementar firma digital
  - [ ] ⚠️ NO RECOMENDADO - Muy complejo

### 7.2 Integración con API de Facturación

- [ ] **7.2.1** Instalar SDK
  ```bash
  pip install alegra-python  # O el SDK correspondiente
  ```

- [ ] **7.2.2** Crear servicio `FacturacionService`
  ```python
  class FacturacionService:
      def crear_factura(empresa, pago):
          # Crear factura en API externa
          # Retornar URL del PDF

      def enviar_factura_email(empresa, factura_url):
          # Enviar PDF por email

      def consultar_factura(factura_id):
          # Consultar estado de factura
  ```

- [ ] **7.2.3** Integrar en webhook de pago
  ```python
  # Después de confirmar pago:
  factura = FacturacionService.crear_factura(empresa, pago)
  pago.factura_url = factura.pdf_url
  pago.save()
  FacturacionService.enviar_factura_email(empresa, factura.pdf_url)
  ```

### 7.3 Template de Factura

- [ ] **7.3.1** Datos requeridos en factura
  - [ ] Número de factura consecutivo
  - [ ] Fecha de expedición
  - [ ] NIT y datos de SAS METROLOGIA S.A.S
  - [ ] NIT y datos de cliente
  - [ ] Detalle de items:
    - [ ] "SAM Metrología - Suscripción Mensual" (o Anual)
    - [ ] Paquetes adicionales (si aplica)
  - [ ] Subtotal
  - [ ] IVA 19%
  - [ ] Total
  - [ ] Forma de pago: "Pago Online - MercadoPago"
  - [ ] CUFE (Código Único de Facturación Electrónica)
  - [ ] QR Code

### 7.4 Testing de Facturación

- [ ] **7.4.1** Generar factura de prueba
  - [ ] Verificar que se crea correctamente
  - [ ] Verificar que PDF se genera
  - [ ] Verificar que email se envía

- [ ] **7.4.2** Validar con DIAN (si es propia)
  - [ ] Factura se registra en DIAN
  - [ ] No hay errores de validación

---

## FASE 8: Automatización y Cron Jobs
**Tiempo estimado:** 1 semana
**Prioridad:** 🟢 MEDIA
**Cláusula del contrato:** 8.2, 9.4

### 8.1 Comandos Programados

- [ ] **8.1.1** Comando `verificar_vencimientos_suscripciones`
  ```bash
  python manage.py verificar_vencimientos_suscripciones
  ```
  - [ ] Buscar empresas con fecha_proximo_pago = hoy
  - [ ] Enviar email recordatorio de pago
  - [ ] Si pasan 5 días sin pago → Suspender acceso
  - [ ] Si pasan 30 días → Cambiar estado a 'Expirado'

- [ ] **8.1.2** Comando `verificar_excesos_recursos`
  ```bash
  python manage.py verificar_excesos_recursos
  ```
  - [ ] Ya creado en FASE 2.4.2
  - [ ] Ejecutar diariamente

- [ ] **8.1.3** Comando `enviar_recordatorios_pago`
  ```bash
  python manage.py enviar_recordatorios_pago
  ```
  - [ ] 7 días antes de vencimiento: Email recordatorio
  - [ ] 3 días antes: Email recordatorio urgente
  - [ ] Día de vencimiento: Email "Paga hoy"

### 8.2 Configurar Cron Jobs (Linux/Render)

- [ ] **8.2.1** Crear archivo `crontab.txt`
  ```cron
  # Verificar excesos de recursos - Diario a las 3:00 AM
  0 3 * * * cd /app && python manage.py verificar_excesos_recursos

  # Verificar vencimientos - Diario a las 6:00 AM
  0 6 * * * cd /app && python manage.py verificar_vencimientos_suscripciones

  # Enviar recordatorios - Diario a las 9:00 AM
  0 9 * * * cd /app && python manage.py enviar_recordatorios_pago
  ```

- [ ] **8.2.2** Instalar crontab en servidor
  ```bash
  crontab crontab.txt
  crontab -l  # Verificar que se instaló
  ```

### 8.3 Alternativa con Celery Beat (Recomendado)

- [ ] **8.3.1** Instalar Celery + Redis
  ```bash
  pip install celery redis django-celery-beat
  ```

- [ ] **8.3.2** Configurar tareas periódicas
  ```python
  # proyecto_c/celery.py
  from celery.schedules import crontab

  app.conf.beat_schedule = {
      'verificar-excesos-diario': {
          'task': 'core.tasks.verificar_excesos_recursos',
          'schedule': crontab(hour=3, minute=0),
      },
      'verificar-vencimientos': {
          'task': 'core.tasks.verificar_vencimientos',
          'schedule': crontab(hour=6, minute=0),
      },
  }
  ```

---

## FASE 9: Testing y Lanzamiento
**Tiempo estimado:** 1-2 semanas
**Prioridad:** 🔴 CRÍTICA antes de producción

### 9.1 Testing Funcional

- [ ] **9.1.1** Flujo completo de nuevo cliente
  - [ ] Registro → Acepta términos → Trial 30 días
  - [ ] Día 30 → Recibe notificación de vencimiento
  - [ ] Selecciona plan → Checkout → Pago
  - [ ] Webhook confirma → Factura generada → Email enviado
  - [ ] Empresa activada → Puede usar sistema

- [ ] **9.1.2** Flujo de paquetes adicionales
  - [ ] Empresa llega a 48 equipos → Alerta 80%
  - [ ] Intenta crear equipo 51 → Bloqueado
  - [ ] Contrata paquete +50 equipos
  - [ ] Puede crear equipo 51

- [ ] **9.1.3** Flujo de renovación
  - [ ] Suscripción mensual vence → Notificación
  - [ ] Cliente no paga en 5 días → Acceso suspendido
  - [ ] Cliente paga → Acceso restaurado

### 9.2 Testing de Seguridad

- [ ] **9.2.1** Verificar protecciones
  - [ ] Usuario no puede ver suscripción de otra empresa
  - [ ] Webhook verifica firma de MercadoPago/Stripe
  - [ ] CSRF token en formularios de pago
  - [ ] HTTPS obligatorio en checkout

- [ ] **9.2.2** Pruebas de penetración básicas
  - [ ] Intentar manipular precios en checkout
  - [ ] Intentar acceder a pago sin autenticación
  - [ ] Intentar enviar webhook falso

### 9.3 Testing de Performance

- [ ] **9.3.1** Carga de emails masivos
  - [ ] Simular envío de 100 notificaciones
  - [ ] Verificar que no colapsa servidor

- [ ] **9.3.2** Webhooks concurrentes
  - [ ] Simular 10 webhooks simultáneos
  - [ ] Verificar que no hay race conditions

### 9.4 Documentación

- [ ] **9.4.1** Manual de usuario
  - [ ] Cómo aceptar términos
  - [ ] Cómo seleccionar plan
  - [ ] Cómo pagar
  - [ ] Cómo ver mi suscripción
  - [ ] Cómo contratar paquetes adicionales

- [ ] **9.4.2** Manual de administrador
  - [ ] Cómo verificar pagos en MercadoPago
  - [ ] Cómo resolver problemas de webhook
  - [ ] Cómo activar empresa manualmente
  - [ ] Cómo generar factura manual

- [ ] **9.4.3** Runbook de incidentes
  - [ ] Webhook no se ejecuta → Qué hacer
  - [ ] Factura no se genera → Qué hacer
  - [ ] Cliente no puede pagar → Qué hacer

### 9.5 Deployment a Producción

- [ ] **9.5.1** Backup completo de BD
  ```bash
  python manage.py dumpdata > backup_pre_pagos.json
  ```

- [ ] **9.5.2** Variables de entorno en producción
  - [ ] MERCADOPAGO_ACCESS_TOKEN (producción)
  - [ ] ALEGRA_API_KEY (o el que sea)
  - [ ] Verificar que están configuradas

- [ ] **9.5.3** Deploy gradual
  - [ ] Fase 1: Solo términos (bajo riesgo)
  - [ ] Fase 2: Paquetes adicionales (sin cobro aún)
  - [ ] Fase 3: Pagos en modo test
  - [ ] Fase 4: Pagos en producción

- [ ] **9.5.4** Monitoreo post-lanzamiento
  - [ ] Primeros 3 días: Revisar logs cada 4 horas
  - [ ] Primera semana: Revisar webhooks diarios
  - [ ] Primer mes: Revisar facturación semanal

---

## 📊 RESUMEN DE TIEMPOS

| Fase | Descripción | Tiempo Estimado | Dependencias |
|------|-------------|-----------------|--------------|
| 0 | Preparación y Decisiones | 1-2 días | - |
| 1 | Términos y Condiciones | 3-5 días | Fase 0 |
| 2 | Paquetes Adicionales | 1 semana | Fase 1 |
| 3 | Monitoreo de Uso | 3-4 días | Fase 2 |
| 4 | Notificaciones | 3 días | Fase 2, 3 |
| 5 | Panel de Suscripción | 1 semana | Fase 2 |
| 6 | Pasarela de Pagos | 2-3 semanas | Fase 0, 5 |
| 7 | Facturación DIAN | 2-3 semanas | Fase 6 |
| 8 | Automatización | 1 semana | Fase 2-7 |
| 9 | Testing y Lanzamiento | 1-2 semanas | Todas |

**TIEMPO TOTAL: 8-12 semanas (2-3 meses)**

---

## 🎯 RUTA CRÍTICA RECOMENDADA

### **MES 1: Fundamentos**
- Semana 1: Fase 0 + Fase 1 (Términos)
- Semana 2: Fase 2 (Paquetes Adicionales)
- Semana 3: Fase 3 + Fase 4 (Monitoreo + Notificaciones)
- Semana 4: Fase 5 (Panel de Suscripción)

### **MES 2: Pagos y Facturación**
- Semana 5-6: Fase 6 (Pasarela de Pagos)
- Semana 7-8: Fase 7 (Facturación)

### **MES 3: Automatización y Lanzamiento**
- Semana 9: Fase 8 (Automatización)
- Semana 10-11: Fase 9 (Testing)
- Semana 12: Lanzamiento y Monitoreo

---

## ✅ CRITERIOS DE ACEPTACIÓN

### Cada fase se considera completa cuando:

1. **Términos:** 100% de usuarios nuevos deben aceptar antes de acceder
2. **Paquetes:** Sistema detecta excesos y sugiere paquetes correctos
3. **Monitoreo:** Dashboard muestra uso en tiempo real
4. **Notificaciones:** Emails se envían correctamente en escenarios clave
5. **Panel:** Cliente puede ver y gestionar su suscripción
6. **Pagos:** Webhook procesa pagos en <30 segundos
7. **Facturación:** Factura se genera automáticamente tras pago
8. **Automatización:** Cron jobs ejecutan sin errores
9. **Testing:** 0 bugs críticos, <5 bugs menores

---

## 📝 NOTAS IMPORTANTES

- Este checklist debe revisarse SEMANALMENTE
- Marcar items completados con la fecha
- Documentar cualquier desviación del plan
- Actualizar estimaciones según progreso real
- Celebrar cada fase completada 🎉

---

**Última actualización:** 2025-10-03
**Próxima revisión:** ___________
**Responsable del proyecto:** ___________
