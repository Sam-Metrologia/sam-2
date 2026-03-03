# core/views/pagos.py
# Módulo C: Pagos con Wompi (PSE / Tarjeta)

import hashlib
import json
import logging
import re
import uuid
from decimal import Decimal
from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from core.models import CustomUser, TransaccionPago

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURACIÓN DE PLANES
# Precios según contrato vigente (sin IVA; el IVA se calcula aparte)
# ============================================================================
IVA = Decimal('0.19')

# ============================================================================
# Catálogo de planes — 4 niveles × 2 períodos (mensual / anual)
#
# Lógica de retención: precio por equipo decrece con el volumen para que
# empresas grandes prefieran un plan superior a pagar excesos a $1.000/equipo.
#
#  Básico     50 eq  → $1.600/eq/mes
#  Estándar  200 eq  → $1.000/eq/mes  (base contractual)
#  Profesional 500eq →   $760/eq/mes
#  Empresarial 1000eq→   $650/eq/mes
#
# Anual = 10 meses pagados (2 meses gratis, −16.7%)
# ============================================================================

_TIER_BASE = [
    # (key_mes, key_año, nombre, equipos, almac_mb, usuarios, precio_mes, precio_año)
    # Todos los planes incluyen 3 usuarios base (técnico, admin, gerente).
    # Usuarios o equipos adicionales se compran como add-ons.
    ('BASICO_MENSUAL',    'BASICO_ANUAL',    'Básico',      50,   2*1024,  3,   Decimal('80000'),   Decimal('800000')),
    ('MENSUAL',           'ANUAL',           'Estándar',   200,   4*1024,  3,   Decimal('200000'),  Decimal('2000000')),
    ('PRO_MENSUAL',       'PRO_ANUAL',       'Profesional',500,  10*1024,  3,   Decimal('380000'),  Decimal('3800000')),
    ('ENTERPRISE_MENSUAL','ENTERPRISE_ANUAL','Empresarial',1000, 20*1024,  3,   Decimal('650000'),  Decimal('6500000')),
]

# ============================================================================
# Add-ons modulares — disponibles en cualquier plan
# Los precios están alineados con el contrato (Cláusula 3) con ajuste por rol.
# ============================================================================
ADDONS = {
    # ── Usuarios por rol ────────────────────────────────────────────────────
    'usuario_tecnico': {
        'nombre': 'Técnico adicional',
        'descripcion': 'Registra equipos, calibraciones, comprobaciones y mantenimientos. Sin acceso administrativo.',
        'precio_base': Decimal('20000'),
        'unidad': '/usuario/mes',
        'icono': '👷',
        'rol': 'tecnico',
    },
    'usuario_admin': {
        'nombre': 'Administrador adicional',
        'descripcion': 'Gestión completa de equipos, usuarios y configuración de la empresa.',
        'precio_base': Decimal('28000'),
        'unidad': '/usuario/mes',
        'icono': '🔧',
        'rol': 'admin',
    },
    'usuario_gerente': {
        'nombre': 'Gerente adicional',
        'descripcion': 'Acceso total: dashboard gerencial, reportes avanzados, panel de decisiones y métricas.',
        'precio_base': Decimal('35000'),
        'unidad': '/usuario/mes',
        'icono': '👔',
        'rol': 'gerente',
    },
    # ── Recursos ────────────────────────────────────────────────────────────
    'equipos_50': {
        'nombre': '+50 Equipos',
        'descripcion': 'Bloque de 50 equipos adicionales sobre el límite del plan. Sin límite de bloques.',
        'precio_base': Decimal('45000'),
        'unidad': '/bloque/mes',
        'icono': '⚙️',
        'rol': None,
    },
    'storage_5gb': {
        'nombre': '+5 GB Almacenamiento',
        'descripcion': 'Espacio extra para documentos, certificados y archivos adjuntos.',
        'precio_base': Decimal('20000'),
        'unidad': '/5 GB/mes',
        'icono': '💾',
        'rol': None,
    },
}

for _addon in ADDONS.values():
    _addon['iva'] = (_addon['precio_base'] * IVA).quantize(Decimal('1'))
    _addon['precio_total'] = _addon['precio_base'] + _addon['iva']

PLANES = {}
for _km, _ka, _nom, _eq, _mb, _usr, _pm, _pa in _TIER_BASE:
    _ahorro_anual = (_pm * 12) - _pa  # lo que se ahorra vs 12 meses
    PLANES[_km] = {
        'nombre': f'Plan {_nom} Mensual',
        'tier': _nom,
        'precio_base': _pm,
        'equipos': _eq,
        'almacenamiento_mb': _mb,
        'usuarios': _usr,
        'duracion_meses': 1,
        'descripcion': f'Acceso mensual — hasta {_eq} equipos',
        'ahorro': None,
        'es_anual': False,
        'key_alternativo': _ka,
    }
    PLANES[_ka] = {
        'nombre': f'Plan {_nom} Anual',
        'tier': _nom,
        'precio_base': _pa,
        'equipos': _eq,
        'almacenamiento_mb': _mb,
        'usuarios': _usr,
        'duracion_meses': 12,
        'descripcion': f'Acceso anual — 2 meses gratis',
        'ahorro': _ahorro_anual,
        'es_anual': True,
        'key_alternativo': _km,
    }

for _plan in PLANES.values():
    _plan['iva'] = (_plan['precio_base'] * IVA).quantize(Decimal('1'))
    _plan['precio_total'] = _plan['precio_base'] + _plan['iva']
    # Ahorro expresado en precio total (IVA incluido) para mostrar en template
    _plan['ahorro_total'] = ((_plan['ahorro'] * (1 + IVA)).quantize(Decimal('1'))) if _plan.get('ahorro') else None

# Lista ordenada de tiers para el template (mensual primero de cada par)
TIERS_ORDENADOS = [
    ('BASICO_MENSUAL',    'BASICO_ANUAL'),
    ('MENSUAL',           'ANUAL'),
    ('PRO_MENSUAL',       'PRO_ANUAL'),
    ('ENTERPRISE_MENSUAL','ENTERPRISE_ANUAL'),
]


def _get_wompi_base_url():
    sandbox = getattr(settings, 'WOMPI_SANDBOX', True)
    return 'https://sandbox.wompi.co/v1' if sandbox else 'https://production.wompi.co/v1'


def _get_wompi_checkout_url():
    sandbox = getattr(settings, 'WOMPI_SANDBOX', True)
    return 'https://checkout.wompi.co/p/'


def _get_ip(request):
    """Extrae la IP real del cliente, considerando proxies."""
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _calcular_firma_integridad(referencia, monto_centavos, moneda, integrity_secret):
    """
    Genera la firma de integridad requerida por Wompi para el checkout.
    Fórmula: SHA-256(reference + amount_in_cents + currency + integrity_secret)
    """
    cadena = f"{referencia}{monto_centavos}{moneda}{integrity_secret}"
    return hashlib.sha256(cadena.encode('utf-8')).hexdigest()


def _validar_firma_webhook(payload_bytes, signature_props, checksum_recibido, events_secret):
    """
    Valida la firma del webhook de Wompi.
    Fórmula: SHA-256(prop1_value + prop2_value + ... + timestamp + events_secret)
    El timestamp es el campo raíz 'timestamp' del payload (entero Unix).
    Retorna True si la firma es válida.
    """
    try:
        payload = json.loads(payload_bytes)

        # Wompi envía las props como "transaction.id" (relativas a payload['data'])
        data_context = payload.get('data', payload)
        valores = []
        for prop in signature_props:
            partes = prop.split('.')
            valor = data_context
            for parte in partes:
                valor = valor.get(parte, '') if isinstance(valor, dict) else ''
            valores.append(str(valor))

        timestamp = payload.get('timestamp', '')
        cadena = ''.join(valores) + str(timestamp) + events_secret
        checksum_calculado = hashlib.sha256(cadena.encode('utf-8')).hexdigest()

        logger.info(
            f"Webhook Wompi firma — props: {signature_props} | "
            f"timestamp: {timestamp} | calculado: {checksum_calculado} | recibido: {checksum_recibido}"
        )
        return checksum_calculado == checksum_recibido
    except Exception as e:
        logger.error(f"Error validando firma webhook Wompi: {e}")
        return False


# ============================================================================
# C4 — Página de Planes
# ============================================================================

@login_required
def planes(request):
    """
    Muestra la página de planes y precios.
    Accesible para cualquier usuario autenticado; es el punto de entrada al pago.
    """
    empresa = request.user.empresa
    estado_plan = empresa.get_estado_suscripcion_display()
    dias_restantes = empresa.get_dias_restantes_plan()
    # Si dias_restantes es inf (plan sin límite) lo normalizamos a None para el template
    if dias_restantes == float('inf'):
        dias_restantes = None

    # Construir lista de tiers para el template: [{mensual: {...}, anual: {...}}, ...]
    tiers_lista = []
    for key_mes, key_año in TIERS_ORDENADOS:
        tiers_lista.append({
            'mensual': {'key': key_mes, **PLANES[key_mes]},
            'anual': {'key': key_año, **PLANES[key_año]},
        })

    context = {
        'planes': PLANES,
        'tiers': tiers_lista,
        'addons': ADDONS,
        'empresa': empresa,
        'estado_plan': estado_plan,
        'dias_restantes': dias_restantes,
        'wompi_public_key': getattr(settings, 'WOMPI_PUBLIC_KEY', ''),
        'wompi_sandbox': getattr(settings, 'WOMPI_SANDBOX', True),
    }
    return render(request, 'core/planes.html', context)


# ============================================================================
# C5 — Inicio de Pago
# ============================================================================

@login_required
@require_POST
def iniciar_pago(request):
    """
    Crea una TransaccionPago con estado 'pendiente' y redirige al checkout de Wompi.
    El campo 'redirect-url' devuelve al usuario a pago_resultado después del pago.
    """
    plan_key = request.POST.get('plan', '').upper()

    if plan_key not in PLANES:
        messages.error(request, 'Plan seleccionado no válido.')
        return redirect('core:planes')

    plan = PLANES[plan_key]
    empresa = request.user.empresa
    integrity_secret = getattr(settings, 'WOMPI_INTEGRITY_SECRET', '')
    public_key = getattr(settings, 'WOMPI_PUBLIC_KEY', '')

    if not public_key:
        logger.error("WOMPI_PUBLIC_KEY no configurado. No se puede iniciar pago.")
        return redirect('core:pago_no_disponible')

    # Referencia única para esta transacción
    referencia = f"SAM-{empresa.id}-{uuid.uuid4().hex[:12].upper()}"
    monto_total = plan['precio_total']
    monto_centavos = int(monto_total * 100)

    # Crear transacción pendiente
    transaccion = TransaccionPago.objects.create(
        empresa=empresa,
        referencia_pago=referencia,
        estado='pendiente',
        monto=monto_total,
        moneda='COP',
        plan_seleccionado=plan_key,
        ip_cliente=_get_ip(request),
    )

    logger.info(
        f"Transacción iniciada: {referencia} | Empresa: {empresa.nombre} | "
        f"Plan: {plan_key} | Monto: {monto_total} COP"
    )

    # Construir URL de retorno al resultado (URL-encoded para que Wompi la preserve)
    redirect_url = quote(
        request.build_absolute_uri(f"/core/pagos/resultado/?ref={referencia}"),
        safe=''
    )

    # Calcular firma de integridad para Wompi
    firma = _calcular_firma_integridad(referencia, monto_centavos, 'COP', integrity_secret)

    # Construir URL de checkout de Wompi con parámetros
    checkout_url = (
        f"{_get_wompi_checkout_url()}"
        f"?public-key={public_key}"
        f"&currency=COP"
        f"&amount-in-cents={monto_centavos}"
        f"&reference={referencia}"
        f"&redirect-url={redirect_url}"
        f"&signature:integrity={firma}"
    )

    return redirect(checkout_url)


# ============================================================================
# C5b — Inicio de Pago de Add-ons
# ============================================================================

@login_required
@require_POST
def iniciar_addon_pago(request):
    """
    Crea una TransaccionPago de tipo ADDON y redirige al checkout de Wompi.
    El webhook activa los add-ons automáticamente al recibir APPROVED.
    """
    empresa = request.user.empresa
    public_key = getattr(settings, 'WOMPI_PUBLIC_KEY', '')
    integrity_secret = getattr(settings, 'WOMPI_INTEGRITY_SECRET', '')

    if not public_key:
        logger.error("WOMPI_PUBLIC_KEY no configurado. No se puede iniciar addon.")
        return redirect('core:pago_no_disponible')

    # Leer cantidades del formulario (mínimo 0 en cada campo)
    def _pos_int(key):
        try:
            return max(0, int(request.POST.get(key, 0)))
        except (ValueError, TypeError):
            return 0

    tecnicos        = _pos_int('tecnicos')
    admins          = _pos_int('admins')
    gerentes        = _pos_int('gerentes')
    bloques_equipos = _pos_int('bloques_equipos')
    bloques_storage = _pos_int('bloques_storage')

    subtotal = (
        tecnicos        * int(ADDONS['usuario_tecnico']['precio_base']) +
        admins          * int(ADDONS['usuario_admin']['precio_base']) +
        gerentes        * int(ADDONS['usuario_gerente']['precio_base']) +
        bloques_equipos * int(ADDONS['equipos_50']['precio_base']) +
        bloques_storage * int(ADDONS['storage_5gb']['precio_base'])
    )

    if subtotal <= 0:
        messages.error(request, 'Selecciona al menos un add-on antes de pagar.')
        return redirect('core:planes')

    total_con_iva = (Decimal(str(subtotal)) * (1 + IVA)).quantize(Decimal('1'))
    monto_centavos = int(total_con_iva * 100)

    datos_addon = {
        'tecnicos': tecnicos,
        'admins': admins,
        'gerentes': gerentes,
        'bloques_equipos': bloques_equipos,
        'bloques_storage': bloques_storage,
    }

    referencia = f"SAM-ADDON-{empresa.id}-{uuid.uuid4().hex[:10].upper()}"

    TransaccionPago.objects.create(
        empresa=empresa,
        referencia_pago=referencia,
        estado='pendiente',
        monto=total_con_iva,
        moneda='COP',
        plan_seleccionado='ADDON',
        datos_addon=datos_addon,
        ip_cliente=_get_ip(request),
    )

    logger.info(
        f"Add-on iniciado: {referencia} | Empresa: {empresa.nombre} | "
        f"Detalle: {datos_addon} | Monto: {total_con_iva} COP"
    )

    redirect_url = quote(
        request.build_absolute_uri(f"/core/pagos/resultado/?ref={referencia}"),
        safe=''
    )
    firma = _calcular_firma_integridad(referencia, monto_centavos, 'COP', integrity_secret)

    checkout_url = (
        f"{_get_wompi_checkout_url()}"
        f"?public-key={public_key}"
        f"&currency=COP"
        f"&amount-in-cents={monto_centavos}"
        f"&reference={referencia}"
        f"&redirect-url={redirect_url}"
        f"&signature:integrity={firma}"
    )

    return redirect(checkout_url)


# ============================================================================
# C6b — Pagos no disponibles (Wompi aún no configurado)
# ============================================================================

@login_required
def pago_no_disponible(request):
    """
    Página temporal mientras se configura la pasarela de pagos.
    Muestra información de contacto para gestionar el plan manualmente.
    """
    return render(request, 'core/pago_no_disponible.html')


# ============================================================================
# C7 — Resultado de Pago
# ============================================================================

@login_required
def pago_resultado(request):
    """
    Página de resultado después de que Wompi redirige de vuelta al sistema.
    Muestra el estado actual de la transacción.
    Nota: el estado definitivo lo actualiza el webhook; esta vista solo informa.
    """
    referencia = request.GET.get('ref', '')
    wompi_id = request.GET.get('id', '')
    transaccion = None

    if referencia:
        try:
            transaccion = TransaccionPago.objects.get(
                referencia_pago=referencia,
                empresa=request.user.empresa
            )
        except TransaccionPago.DoesNotExist:
            pass

    # Fallback: buscar por el ID de Wompi en datos_respuesta (por si ref llegó vacío)
    if not transaccion and wompi_id and request.user.empresa:
        try:
            transaccion = TransaccionPago.objects.get(
                datos_respuesta__id=wompi_id,
                empresa=request.user.empresa
            )
            referencia = transaccion.referencia_pago
        except TransaccionPago.DoesNotExist:
            pass

    context = {
        'transaccion': transaccion,
        'referencia': referencia,
    }
    return render(request, 'core/pago_resultado.html', context)


# ============================================================================
# Helpers de email post-pago
# ============================================================================

def _get_correos_empresa(empresa):
    """Devuelve lista de correos de facturación de la empresa."""
    correos = []
    if empresa.correos_facturacion:
        for c in empresa.correos_facturacion.split(','):
            c = c.strip()
            if c:
                correos.append(c)
    if not correos and empresa.email:
        correos.append(empresa.email)
    return correos


def _enviar_email_confirmacion_plan(transaccion, plan):
    """Envía confirmación de activación de plan al cliente y aviso a SAM."""
    empresa = transaccion.empresa
    from_email = settings.DEFAULT_FROM_EMAIL
    sam_admin = getattr(settings, 'ADMIN_EMAIL', from_email)

    # ── Email al cliente ──────────────────────────────────────────────────
    destinatarios = _get_correos_empresa(empresa)
    duracion = f"{plan['duracion_meses']} mes" if plan['duracion_meses'] == 1 else f"{plan['duracion_meses']} meses"
    almac_gb = plan['almacenamiento_mb'] // 1024

    asunto_cliente = f"✅ Tu {plan['nombre']} en SAM está activo"
    cuerpo_cliente = (
        f"Hola {empresa.nombre},\n\n"
        f"¡Tu pago fue aprobado! Aquí el resumen de tu plan:\n\n"
        f"  Plan:           {plan['nombre']}\n"
        f"  Equipos:        hasta {plan['equipos']}\n"
        f"  Almacenamiento: {almac_gb} GB\n"
        f"  Duración:       {duracion}\n"
        f"  Valor pagado:   ${transaccion.monto:,.0f} COP (IVA incluido)\n"
        f"  Referencia:     {transaccion.referencia_pago}\n\n"
        f"Tu plan ya está activo. Puedes ingresar en https://app.sammetrologia.com\n\n"
        f"Si tienes dudas escríbenos:\n"
        f"  WhatsApp: +57 324 799 0534\n"
        f"  Correo:   direccion@sammetrologia.com\n\n"
        f"SAM Metrologia S.A.S"
    )
    try:
        if destinatarios:
            send_mail(asunto_cliente, cuerpo_cliente, from_email, destinatarios, fail_silently=True)
            logger.info(f"Email confirmación plan enviado a {destinatarios} | Ref: {transaccion.referencia_pago}")
    except Exception as e:
        logger.error(f"Error enviando email confirmación plan: {e}")

    # ── Aviso interno a SAM ───────────────────────────────────────────────
    asunto_sam = f"💰 Nuevo pago recibido — {empresa.nombre}"
    cuerpo_sam = (
        f"Se recibió un pago aprobado:\n\n"
        f"  Empresa:    {empresa.nombre} (ID: {empresa.id})\n"
        f"  NIT:        {empresa.nit}\n"
        f"  Plan:       {plan['nombre']}\n"
        f"  Monto:      ${transaccion.monto:,.0f} COP\n"
        f"  Método:     {transaccion.metodo_pago or 'N/A'}\n"
        f"  Referencia: {transaccion.referencia_pago}\n"
    )
    try:
        send_mail(asunto_sam, cuerpo_sam, from_email, [sam_admin], fail_silently=True)
    except Exception as e:
        logger.error(f"Error enviando aviso de pago a SAM: {e}")


def _enviar_email_confirmacion_addon(transaccion):
    """Envía confirmación de add-ons activados al cliente y aviso a SAM."""
    empresa = transaccion.empresa
    from_email = settings.DEFAULT_FROM_EMAIL
    sam_admin = getattr(settings, 'ADMIN_EMAIL', from_email)
    datos = transaccion.datos_addon or {}

    lineas = []
    if datos.get('tecnicos'):
        lineas.append(f"  +{datos['tecnicos']} usuario(s) Técnico")
    if datos.get('admins'):
        lineas.append(f"  +{datos['admins']} usuario(s) Administrador")
    if datos.get('gerentes'):
        lineas.append(f"  +{datos['gerentes']} usuario(s) Gerente")
    if datos.get('bloques_equipos'):
        lineas.append(f"  +{datos['bloques_equipos'] * 50} equipos ({datos['bloques_equipos']} bloque(s))")
    if datos.get('bloques_storage'):
        lineas.append(f"  +{datos['bloques_storage'] * 5} GB almacenamiento")

    detalle = '\n'.join(lineas) if lineas else '  (sin detalle)'

    # ── Email al cliente ──────────────────────────────────────────────────
    destinatarios = _get_correos_empresa(empresa)
    asunto_cliente = "✅ Tus add-ons en SAM están activos"
    cuerpo_cliente = (
        f"Hola {empresa.nombre},\n\n"
        f"¡Tu pago fue aprobado! Los siguientes add-ons ya están activos:\n\n"
        f"{detalle}\n\n"
        f"  Valor pagado: ${transaccion.monto:,.0f} COP (IVA incluido)\n"
        f"  Referencia:   {transaccion.referencia_pago}\n\n"
        f"Puedes verificarlos en tu dashboard: https://app.sammetrologia.com\n\n"
        f"SAM Metrologia S.A.S\n"
        f"WhatsApp: +57 324 799 0534"
    )
    try:
        if destinatarios:
            send_mail(asunto_cliente, cuerpo_cliente, from_email, destinatarios, fail_silently=True)
            logger.info(f"Email confirmación addon enviado a {destinatarios} | Ref: {transaccion.referencia_pago}")
    except Exception as e:
        logger.error(f"Error enviando email confirmación addon: {e}")

    # ── Aviso interno a SAM ───────────────────────────────────────────────
    asunto_sam = f"💰 Add-ons comprados — {empresa.nombre}"
    cuerpo_sam = (
        f"Add-ons activados:\n\n"
        f"  Empresa:    {empresa.nombre} (ID: {empresa.id})\n"
        f"  Monto:      ${transaccion.monto:,.0f} COP\n"
        f"  Referencia: {transaccion.referencia_pago}\n"
        f"  Detalle:\n{detalle}\n"
    )
    try:
        send_mail(asunto_sam, cuerpo_sam, from_email, [sam_admin], fail_silently=True)
    except Exception as e:
        logger.error(f"Error enviando aviso addon a SAM: {e}")


# ============================================================================
# C6 — Webhook de Confirmación (Wompi → SAM)
# ============================================================================

@csrf_exempt
def wompi_webhook(request):
    """
    Endpoint que recibe notificaciones de Wompi sobre el estado de las transacciones.

    Seguridad:
    - CSRF exento (Wompi no envía token CSRF).
    - Firma criptográfica validada antes de procesar cualquier acción.
    - Idempotente: si la transacción ya está aprobada, no se procesa de nuevo.
    """
    if request.method != 'POST':
        return HttpResponse(status=405)

    payload_bytes = request.body
    events_secret = getattr(settings, 'WOMPI_EVENTS_SECRET', '')

    # Parsear payload
    try:
        payload = json.loads(payload_bytes)
    except json.JSONDecodeError:
        logger.warning("Webhook Wompi: payload JSON inválido")
        return HttpResponse(status=400)

    # Validar firma
    signature = payload.get('signature', {})
    checksum_recibido = signature.get('checksum', '')
    signature_props = signature.get('properties', [])

    if events_secret and not _validar_firma_webhook(
        payload_bytes, signature_props, checksum_recibido, events_secret
    ):
        logger.warning(
            f"Webhook Wompi: firma inválida. Checksum recibido: {checksum_recibido}"
        )
        return HttpResponse(status=401)

    # Procesar evento
    evento = payload.get('event', '')
    if evento != 'transaction.updated':
        # Solo procesamos actualizaciones de transacción
        return HttpResponse(status=200)

    transaction_data = payload.get('data', {}).get('transaction', {})
    referencia = transaction_data.get('reference', '')
    estado_wompi = transaction_data.get('status', '')
    metodo = transaction_data.get('payment_method_type', '')

    if not referencia:
        logger.warning("Webhook Wompi: evento sin referencia de transacción")
        return HttpResponse(status=400)

    # Buscar transacción local
    try:
        transaccion = TransaccionPago.objects.get(referencia_pago=referencia)
    except TransaccionPago.DoesNotExist:
        logger.warning(f"Webhook Wompi: transacción no encontrada para referencia {referencia}")
        return HttpResponse(status=404)

    # Idempotencia: si ya está aprobada, no reprocesar
    if transaccion.esta_aprobada():
        logger.info(f"Webhook Wompi: transacción {referencia} ya aprobada, ignorando")
        return HttpResponse(status=200)

    # Guardar datos de respuesta para auditoría
    transaccion.datos_respuesta = transaction_data
    if metodo:
        transaccion.metodo_pago = 'tarjeta' if 'CARD' in metodo.upper() else 'PSE'

    # Mapear estado Wompi → estado interno
    estado_map = {
        'APPROVED': 'aprobado',
        'DECLINED': 'rechazado',
        'VOIDED': 'rechazado',
        'ERROR': 'error',
        'PENDING': 'pendiente',
    }
    nuevo_estado = estado_map.get(estado_wompi.upper(), 'error')
    transaccion.estado = nuevo_estado
    transaccion.save(update_fields=['estado', 'datos_respuesta', 'metodo_pago', 'fecha_actualizacion'])

    # Si fue aprobado, activar lo que corresponda en la empresa
    if nuevo_estado == 'aprobado':
        if transaccion.plan_seleccionado == 'ADDON':
            # ── Activar add-ons ────────────────────────────────────────
            if transaccion.datos_addon:
                try:
                    transaccion.empresa.activar_addons(transaccion.datos_addon)
                    logger.info(
                        f"Add-ons activados para empresa {transaccion.empresa.nombre}: "
                        f"{transaccion.datos_addon} | Ref: {referencia}"
                    )
                    _enviar_email_confirmacion_addon(transaccion)
                except Exception as e:
                    logger.error(
                        f"Error activando add-ons para empresa {transaccion.empresa.nombre}: {e}"
                    )
            else:
                logger.warning(f"Transacción addon {referencia} aprobada pero sin datos_addon")
        else:
            # ── Activar plan completo ───────────────────────────────────
            plan = PLANES.get(transaccion.plan_seleccionado)
            if plan:
                try:
                    transaccion.empresa.activar_plan_pagado(
                        limite_equipos=plan['equipos'],
                        limite_almacenamiento_mb=plan['almacenamiento_mb'],
                        duracion_meses=plan['duracion_meses'],
                    )
                    logger.info(
                        f"Plan activado para empresa {transaccion.empresa.nombre}: "
                        f"{transaccion.plan_seleccionado} | Ref: {referencia}"
                    )
                    _enviar_email_confirmacion_plan(transaccion, plan)
                except Exception as e:
                    logger.error(
                        f"Error activando plan para empresa {transaccion.empresa.nombre}: {e}"
                    )
    else:
        logger.info(
            f"Transacción {referencia} → estado: {nuevo_estado} "
            f"(Wompi: {estado_wompi})"
        )

    return HttpResponse(status=200)


    return HttpResponse(status=200)
