# core/views/pagos.py
# Módulo C: Pagos con Wompi (PSE / Tarjeta)

import hashlib
import json
import logging
import re
import uuid
from decimal import Decimal
from urllib.parse import quote

import requests as _requests

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMultiAlternatives
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from core.models import CustomUser, TransaccionPago, LinkPago

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

# ── Plan de prueba temporal $5.000 — ELIMINAR DESPUÉS DEL TEST ──────────────
PLANES['PLAN_TEST'] = {
    'nombre': 'Plan Prueba $5.000',
    'tier': 'Test',
    'precio_base': Decimal('4202'),
    'iva': Decimal('798'),
    'precio_total': Decimal('5000'),
    'equipos': 50,           # igual que Básico real → verificable en dashboard
    'almacenamiento_mb': 2048,  # 2 GB
    'usuarios': 3,
    'duracion_meses': 1,
    'descripcion': 'Prueba técnica de webhook Wompi',
    'ahorro': None,
    'ahorro_total': None,
    'es_anual': False,
    'key_alternativo': None,
}

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

    # Determinar rango del plan actual para bloquear planes inferiores
    # Básico=1, Estándar=2, Profesional=3, Empresarial=4
    _tier_rank = {}
    for rango, (key_mes, key_año) in enumerate(TIERS_ORDENADOS, start=1):
        _tier_rank[key_mes] = rango
        _tier_rank[key_año] = rango

    plan_actual_rango = 0
    if estado_plan == 'Activo':
        from core.models import TransaccionPago as _TX
        ultima_tx = (
            _TX.objects
            .filter(empresa=empresa, estado='aprobado')
            .exclude(plan_seleccionado='ADDON')
            .order_by('-fecha_creacion')
            .first()
        )
        if ultima_tx:
            plan_actual_rango = _tier_rank.get(ultima_tx.plan_seleccionado, 0)

    # Construir lista de tiers para el template: [{mensual: {...}, anual: {...}, rango: N}, ...]
    tiers_lista = []
    for rango, (key_mes, key_año) in enumerate(TIERS_ORDENADOS, start=1):
        tiers_lista.append({
            'mensual': {'key': key_mes, **PLANES[key_mes]},
            'anual':   {'key': key_año, **PLANES[key_año]},
            'rango':   rango,
        })

    context = {
        'planes': PLANES,
        'tiers': tiers_lista,
        'addons': ADDONS,
        'empresa': empresa,
        'estado_plan': estado_plan,
        'dias_restantes': dias_restantes,
        'plan_actual_rango': plan_actual_rango,
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

    # Validar que el perfil de empresa tenga los datos mínimos para facturar
    if not empresa.nit:
        messages.error(
            request,
            'Tu empresa no tiene NIT registrado. Contacta a soporte para actualizar tu perfil.'
        )
        return redirect('core:planes')

    if not empresa.correos_facturacion:
        messages.warning(
            request,
            'Necesitas registrar al menos un correo de facturación antes de proceder al pago. '
            'Lo usaremos para enviarte la factura electrónica.'
        )
        return redirect('core:editar_perfil_empresa')

    # Activar renovación automática si el cliente marcó el checkbox
    if request.POST.get('renovacion_automatica'):
        if not empresa.renovacion_automatica:
            empresa.renovacion_automatica = True
            empresa.save(update_fields=['renovacion_automatica'])
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


SAM_FROM_EMAIL = 'comercial@sammetrologia.com'
SAM_FROM_LABEL = f'SAM Metrología <{SAM_FROM_EMAIL}>'

_EMAIL_STYLE = """
<style>
  body{font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;color:#333;margin:0;padding:0;background:#f4f4f4;}
  .wrap{max-width:600px;margin:30px auto;}
  .card{border:1px solid #e1e1e1;border-radius:10px;overflow:hidden;box-shadow:0 4px 10px rgba(0,0,0,.07);}
  .hdr{background:#003366;color:#fff;padding:28px 35px;text-align:center;}
  .hdr h1{margin:0;font-size:22px;letter-spacing:1px;}
  .hdr p{margin:5px 0 0;opacity:.85;font-size:13px;}
  .body{padding:35px;background:#fff;}
  .badge{display:inline-block;background:#d1fae5;color:#065f46;font-weight:700;
         padding:8px 18px;border-radius:20px;font-size:15px;margin-bottom:20px;}
  table.det{width:100%;border-collapse:collapse;margin:20px 0;}
  table.det td{padding:10px 14px;font-size:14px;border-bottom:1px solid #f0f0f0;}
  table.det td:first-child{color:#555;font-weight:600;width:45%;}
  .btn{display:inline-block;background:#003366;color:#fff!important;padding:12px 28px;
       border-radius:6px;text-decoration:none;font-weight:600;margin:20px 0;}
  .sig-name{color:#003366;font-weight:700;font-size:15px;margin-top:22px;}
  .sig-info{font-size:13px;color:#666;line-height:1.7;}
  .ftr{background:#1a1a1a;padding:22px 35px;text-align:center;color:#888;font-size:12px;}
  .ftr strong{color:#aaa;}
  a{color:#0056b3;}
</style>"""


def _send_html_email(asunto, texto_plano, html, destinatarios, from_label=None):
    """Envía email con versión HTML y texto plano como fallback."""
    remitente = from_label or SAM_FROM_LABEL
    try:
        msg = EmailMultiAlternatives(asunto, texto_plano, remitente, destinatarios)
        msg.attach_alternative(html, 'text/html')
        msg.send()
        return True
    except Exception as e:
        logger.error(f"Error enviando email '{asunto}' a {destinatarios}: {e}")
        return False


def _enviar_email_confirmacion_plan(transaccion, plan):
    """Envía confirmación de activación de plan al cliente y aviso a SAM."""
    empresa = transaccion.empresa
    sam_admin = getattr(settings, 'ADMIN_EMAIL', SAM_FROM_EMAIL)
    destinatarios = _get_correos_empresa(empresa)

    duracion = f"{plan['duracion_meses']} mes" if plan['duracion_meses'] == 1 else f"{plan['duracion_meses']} meses"
    almac_gb = round(plan['almacenamiento_mb'] / 1024, 1)
    monto_fmt = f"${transaccion.monto:,.0f} COP"
    metodo = transaccion.metodo_pago or 'N/A'

    # ── Email al cliente (HTML) ───────────────────────────────────────────
    asunto_cliente = f"✅ Tu {plan['nombre']} en SAM está activo"
    html_cliente = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">{_EMAIL_STYLE}</head>
<body><div class="wrap"><div class="card">
  <div class="hdr">
    <h1>SAM METROLOGÍA</h1>
    <p>Control Digital e Inteligencia Metrológica</p>
  </div>
  <div class="body">
    <span class="badge">✅ Pago Aprobado</span>
    <p>Cordial saludo, estimado(a) <strong>{empresa.nombre}</strong>:</p>
    <p>¡Excelente! Tu pago fue procesado exitosamente y tu plan ya está activo en la plataforma.</p>
    <table class="det">
      <tr><td>Plan</td><td><strong>{plan['nombre']}</strong></td></tr>
      <tr><td>Equipos incluidos</td><td>Hasta {plan['equipos']} equipos</td></tr>
      <tr><td>Almacenamiento</td><td>{almac_gb} GB</td></tr>
      <tr><td>Duración</td><td>{duracion}</td></tr>
      <tr><td>Valor pagado</td><td><strong>{monto_fmt}</strong> (IVA incluido)</td></tr>
      <tr><td>Método de pago</td><td>{metodo}</td></tr>
      <tr><td>Referencia</td><td style="font-family:monospace;font-size:13px">{transaccion.referencia_pago}</td></tr>
    </table>
    <a href="https://app.sammetrologia.com" class="btn">Ingresar a la plataforma →</a>
    <p>Si tienes alguna duda o requerimiento no dudes en contactarnos.</p>
    <p>Atentamente,</p>
    <div class="sig-name">Equipo Comercial SAM Metrología</div>
    <div class="sig-info">
      SAM Metrología S.A.S<br>
      <a href="https://sammetrologia.com">sammetrologia.com</a><br>
      WhatsApp: +57 324 799 0534 &nbsp;|&nbsp; comercial@sammetrologia.com
    </div>
  </div>
  <div class="ftr"><strong>SAM Metrología | Gestión Metrológica 4.0</strong><br>
    Colombia — Soluciones Avanzadas en Medición</div>
</div></div></body></html>"""

    texto_cliente = (
        f"Hola {empresa.nombre},\n\n"
        f"Tu pago fue aprobado. Resumen:\n\n"
        f"  Plan:           {plan['nombre']}\n"
        f"  Equipos:        hasta {plan['equipos']}\n"
        f"  Almacenamiento: {almac_gb} GB\n"
        f"  Duración:       {duracion}\n"
        f"  Valor pagado:   {monto_fmt} (IVA incluido)\n"
        f"  Referencia:     {transaccion.referencia_pago}\n\n"
        f"Ingresa en: https://app.sammetrologia.com\n\n"
        f"SAM Metrología S.A.S — comercial@sammetrologia.com"
    )

    if destinatarios:
        ok = _send_html_email(asunto_cliente, texto_cliente, html_cliente, destinatarios)
        if ok:
            logger.info(f"Email confirmación plan enviado a {destinatarios} | Ref: {transaccion.referencia_pago}")

    # ── Aviso interno a SAM (HTML) ────────────────────────────────────────
    asunto_sam = f"💰 Nuevo pago recibido — {empresa.nombre}"
    html_sam = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">{_EMAIL_STYLE}</head>
<body><div class="wrap"><div class="card">
  <div class="hdr"><h1>SAM METROLOGÍA</h1><p>Notificación interna de pago</p></div>
  <div class="body">
    <span class="badge" style="background:#dbeafe;color:#1e40af;">💰 Pago Recibido</span>
    <p>Se procesó un nuevo pago exitosamente:</p>
    <table class="det">
      <tr><td>Empresa</td><td><strong>{empresa.nombre}</strong> (ID: {empresa.id})</td></tr>
      <tr><td>NIT</td><td>{empresa.nit}</td></tr>
      <tr><td>Plan</td><td>{plan['nombre']}</td></tr>
      <tr><td>Monto</td><td><strong>{monto_fmt}</strong></td></tr>
      <tr><td>Método</td><td>{metodo}</td></tr>
      <tr><td>Referencia</td><td style="font-family:monospace;font-size:13px">{transaccion.referencia_pago}</td></tr>
    </table>
  </div>
  <div class="ftr"><strong>SAM Metrología | Notificación Interna</strong></div>
</div></div></body></html>"""

    texto_sam = (
        f"Pago aprobado:\n  Empresa: {empresa.nombre} (ID: {empresa.id})\n"
        f"  NIT: {empresa.nit}\n  Plan: {plan['nombre']}\n"
        f"  Monto: {monto_fmt}\n  Ref: {transaccion.referencia_pago}"
    )
    _send_html_email(asunto_sam, texto_sam, html_sam, [sam_admin])


def _enviar_email_confirmacion_addon(transaccion):
    """Envía confirmación de add-ons activados al cliente y aviso a SAM."""
    empresa = transaccion.empresa
    sam_admin = getattr(settings, 'ADMIN_EMAIL', SAM_FROM_EMAIL)
    datos = transaccion.datos_addon or {}
    monto_fmt = f"${transaccion.monto:,.0f} COP"

    items_txt = []
    items_html = []
    if datos.get('tecnicos'):
        items_txt.append(f"  +{datos['tecnicos']} usuario(s) Técnico")
        items_html.append(f"<tr><td>Técnicos adicionales</td><td>+{datos['tecnicos']} usuario(s)</td></tr>")
    if datos.get('admins'):
        items_txt.append(f"  +{datos['admins']} usuario(s) Administrador")
        items_html.append(f"<tr><td>Administradores adicionales</td><td>+{datos['admins']} usuario(s)</td></tr>")
    if datos.get('gerentes'):
        items_txt.append(f"  +{datos['gerentes']} usuario(s) Gerente")
        items_html.append(f"<tr><td>Gerentes adicionales</td><td>+{datos['gerentes']} usuario(s)</td></tr>")
    if datos.get('bloques_equipos'):
        items_txt.append(f"  +{datos['bloques_equipos'] * 50} equipos ({datos['bloques_equipos']} bloque(s))")
        items_html.append(f"<tr><td>Equipos adicionales</td><td>+{datos['bloques_equipos'] * 50} ({datos['bloques_equipos']} bloque(s))</td></tr>")
    if datos.get('bloques_storage'):
        items_txt.append(f"  +{datos['bloques_storage'] * 5} GB almacenamiento")
        items_html.append(f"<tr><td>Almacenamiento adicional</td><td>+{datos['bloques_storage'] * 5} GB</td></tr>")

    detalle_txt = '\n'.join(items_txt) if items_txt else '  (sin detalle)'
    detalle_html = '\n'.join(items_html) if items_html else '<tr><td colspan="2">Sin detalle</td></tr>'

    # ── Email al cliente (HTML) ───────────────────────────────────────────
    destinatarios = _get_correos_empresa(empresa)
    asunto_cliente = "✅ Tus add-ons en SAM están activos"
    html_cliente = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">{_EMAIL_STYLE}</head>
<body><div class="wrap"><div class="card">
  <div class="hdr"><h1>SAM METROLOGÍA</h1><p>Control Digital e Inteligencia Metrológica</p></div>
  <div class="body">
    <span class="badge">✅ Add-ons Activados</span>
    <p>Cordial saludo, estimado(a) <strong>{empresa.nombre}</strong>:</p>
    <p>Tu pago fue aprobado. Los siguientes add-ons ya están disponibles en tu cuenta:</p>
    <table class="det">
      {detalle_html}
      <tr><td>Valor pagado</td><td><strong>{monto_fmt}</strong> (IVA incluido)</td></tr>
      <tr><td>Referencia</td><td style="font-family:monospace;font-size:13px">{transaccion.referencia_pago}</td></tr>
    </table>
    <a href="https://app.sammetrologia.com" class="btn">Ver mi cuenta →</a>
    <p>Atentamente,</p>
    <div class="sig-name">Equipo Comercial SAM Metrología</div>
    <div class="sig-info">
      SAM Metrología S.A.S<br>
      <a href="https://sammetrologia.com">sammetrologia.com</a><br>
      WhatsApp: +57 324 799 0534 &nbsp;|&nbsp; comercial@sammetrologia.com
    </div>
  </div>
  <div class="ftr"><strong>SAM Metrología | Gestión Metrológica 4.0</strong><br>
    Colombia — Soluciones Avanzadas en Medición</div>
</div></div></body></html>"""

    texto_cliente = (
        f"Hola {empresa.nombre},\nAdd-ons activos:\n{detalle_txt}\n\n"
        f"  Valor: {monto_fmt}  |  Ref: {transaccion.referencia_pago}\n"
        f"Ingresa en: https://app.sammetrologia.com"
    )

    if destinatarios:
        ok = _send_html_email(asunto_cliente, texto_cliente, html_cliente, destinatarios)
        if ok:
            logger.info(f"Email confirmación addon enviado a {destinatarios} | Ref: {transaccion.referencia_pago}")

    # ── Aviso interno a SAM (HTML) ────────────────────────────────────────
    asunto_sam = f"💰 Add-ons comprados — {empresa.nombre}"
    html_sam = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">{_EMAIL_STYLE}</head>
<body><div class="wrap"><div class="card">
  <div class="hdr"><h1>SAM METROLOGÍA</h1><p>Notificación interna de add-ons</p></div>
  <div class="body">
    <span class="badge" style="background:#dbeafe;color:#1e40af;">💰 Add-ons Comprados</span>
    <table class="det">
      <tr><td>Empresa</td><td><strong>{empresa.nombre}</strong> (ID: {empresa.id})</td></tr>
      <tr><td>Monto</td><td><strong>{monto_fmt}</strong></td></tr>
      <tr><td>Referencia</td><td style="font-family:monospace;font-size:13px">{transaccion.referencia_pago}</td></tr>
      {detalle_html}
    </table>
  </div>
  <div class="ftr"><strong>SAM Metrología | Notificación Interna</strong></div>
</div></div></body></html>"""

    texto_sam = (
        f"Add-ons: {empresa.nombre} (ID: {empresa.id})\n"
        f"Monto: {monto_fmt} | Ref: {transaccion.referencia_pago}\n{detalle_txt}"
    )
    _send_html_email(asunto_sam, texto_sam, html_sam, [sam_admin])


# ============================================================================
# Renovación Automática — Payment Source
# ============================================================================

def _guardar_payment_source(empresa, card_token, customer_email,
                            acceptance_token='', personal_auth_token=''):
    """
    Crea un payment_source en Wompi y guarda el ID en la empresa.
    Devuelve el payment_source_id (str) si tuvo éxito, None si falló.
    """
    private_key = getattr(settings, 'WOMPI_PRIVATE_KEY', '')
    if not private_key:
        logger.warning("WOMPI_PRIVATE_KEY no configurado; no se puede crear payment_source.")
        return None
    payload = {
        'type': 'CARD',
        'token': card_token,
        'customer_email': customer_email,
    }
    if acceptance_token:
        payload['acceptance_token'] = acceptance_token
    if personal_auth_token:
        payload['accept_personal_auth'] = personal_auth_token
    try:
        r = _requests.post(
            f"{_get_wompi_base_url()}/payment_sources",
            json=payload,
            headers={'Authorization': f'Bearer {private_key}'},
            timeout=10,
        )
        if r.status_code in (200, 201):
            ps_id = r.json().get('data', {}).get('id')
            if ps_id:
                empresa.wompi_payment_source_id = str(ps_id)
                empresa.renovacion_automatica = True
                empresa.save(update_fields=['wompi_payment_source_id', 'renovacion_automatica'])
                try:
                    from core.signals import invalidate_dashboard_cache
                    invalidate_dashboard_cache(empresa.id)
                except Exception:
                    pass
                logger.info(f"Payment source guardado para {empresa.nombre}: {ps_id}")
                return str(ps_id)
        logger.warning(
            f"Wompi /payment_sources devolvió {r.status_code} para "
            f"{empresa.nombre}: {r.text[:200]}"
        )
        return None
    except Exception as e:
        logger.error(f"Error creando payment_source en Wompi: {e}")
        return None


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

    # Parsear payload primero — JSON inválido siempre retorna 400
    try:
        payload = json.loads(payload_bytes)
    except json.JSONDecodeError:
        logger.warning("Webhook Wompi: payload JSON inválido")
        return HttpResponse(status=400)

    events_secret = getattr(settings, 'WOMPI_EVENTS_SECRET', '')

    # Rechazar si el secret no está configurado — nunca procesar sin firma verificada
    if not events_secret:
        logger.critical(
            "WOMPI_EVENTS_SECRET no configurado. "
            "Rechazando webhook para evitar activaciones fraudulentas."
        )
        return HttpResponse(status=500)

    # Validar firma — siempre requerida
    signature = payload.get('signature', {})
    checksum_recibido = signature.get('checksum', '')
    signature_props = signature.get('properties', [])

    if not _validar_firma_webhook(
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
                # Filtrar la clave interna _link_pago_token antes de activar
                datos_addon_limpios = {
                    k: v for k, v in transaccion.datos_addon.items()
                    if not k.startswith('_')
                }
                try:
                    if datos_addon_limpios:
                        transaccion.empresa.activar_addons(datos_addon_limpios)
                    logger.info(
                        f"Add-ons activados para empresa {transaccion.empresa.nombre}: "
                        f"{datos_addon_limpios} | Ref: {referencia}"
                    )
                    _enviar_email_confirmacion_addon(transaccion)
                except Exception as e:
                    logger.error(
                        f"Error activando add-ons para empresa {transaccion.empresa.nombre}: {e}"
                    )
                # Marcar LinkPago como pagado si aplica
                link_token = transaccion.datos_addon.get('_link_pago_token')
                if link_token:
                    try:
                        lp = LinkPago.objects.get(token=link_token)
                        lp.estado = 'pagado'
                        lp.save(update_fields=['estado'])
                        # Acumular add-ons pagados sobre los existentes
                        if datos_addon_limpios:
                            recurrentes = dict(transaccion.empresa.addons_recurrentes or {})
                            for k, v in datos_addon_limpios.items():
                                recurrentes[k] = recurrentes.get(k, 0) + int(v or 0)
                            transaccion.empresa.addons_recurrentes = recurrentes
                            transaccion.empresa.save(update_fields=['addons_recurrentes'])
                    except LinkPago.DoesNotExist:
                        pass
                else:
                    # Pago directo (sin link) — acumular en addons_recurrentes
                    # para que la renovación automática los incluya el próximo ciclo
                    if datos_addon_limpios:
                        recurrentes = dict(transaccion.empresa.addons_recurrentes or {})
                        for k, v in datos_addon_limpios.items():
                            recurrentes[k] = recurrentes.get(k, 0) + int(v or 0)
                        transaccion.empresa.addons_recurrentes = recurrentes
                        transaccion.empresa.save(update_fields=['addons_recurrentes'])
                        logger.info(
                            f"addons_recurrentes actualizado para {transaccion.empresa.nombre}: "
                            f"{recurrentes}"
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

                # Si viene de un LinkPago, aplicar add-ons y marcarlo como pagado
                link_token = (transaccion.datos_addon or {}).get('_link_pago_token')
                if link_token:
                    try:
                        link_obj = LinkPago.objects.get(token=link_token)
                        addons_link = {k: v for k, v in (link_obj.addons or {}).items()}
                        if addons_link:
                            transaccion.empresa.activar_addons(addons_link)
                            # Acumular add-ons del link sobre los existentes
                            recurrentes = dict(transaccion.empresa.addons_recurrentes or {})
                            for k, v in addons_link.items():
                                recurrentes[k] = recurrentes.get(k, 0) + int(v or 0)
                            transaccion.empresa.addons_recurrentes = recurrentes
                            transaccion.empresa.save(update_fields=['addons_recurrentes'])
                        link_obj.estado = 'pagado'
                        link_obj.save(update_fields=['estado'])
                        logger.info(f"LinkPago {link_token[:8]} marcado como pagado para {transaccion.empresa.nombre}")
                    except LinkPago.DoesNotExist:
                        logger.warning(f"LinkPago no encontrado: {link_token[:8]}")
    else:
        logger.info(
            f"Transacción {referencia} → estado: {nuevo_estado} "
            f"(Wompi: {estado_wompi})"
        )

    return HttpResponse(status=200)


# ============================================================================
# VISTA TEMPORAL DE PRUEBA — ELIMINAR DESPUÉS DEL TEST DE WEBHOOK
# Acceso: /core/test-pago/ (cualquier usuario con empresa)
# ============================================================================
@login_required
def test_pago_view(request):
    """Página temporal para probar el flujo Wompi con $5.000 COP."""
    from django.http import HttpResponse
    from django.middleware.csrf import get_token

    empresa = request.user.empresa
    if not empresa:
        return HttpResponse(
            "<h3>Este usuario no tiene empresa. Inicia sesión con una cuenta de empresa.</h3>"
        )

    csrf = get_token(request)
    html = f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><title>Test Pago Wompi $5.000</title>
<style>body{{font-family:sans-serif;max-width:500px;margin:60px auto;padding:20px;}}
.btn{{background:#2563eb;color:#fff;border:none;padding:14px 28px;font-size:16px;
border-radius:8px;cursor:pointer;width:100%;}}
.btn:hover{{background:#1d4ed8;}}
.info{{background:#fef9c3;border:1px solid #fde047;padding:12px;border-radius:6px;margin-bottom:20px;}}
</style></head>
<body>
<h2>&#129514; Prueba de Pago Wompi</h2>
<div class="info">
  <strong>Plan:</strong> PLAN_TEST<br>
  <strong>Monto:</strong> $5.000 COP (IVA incluido)<br>
  <strong>Empresa:</strong> {empresa.nombre}<br>
  <strong>Usuario:</strong> {request.user.username}
</div>
<form method="post" action="/core/pagos/iniciar/">
  <input type="hidden" name="csrfmiddlewaretoken" value="{csrf}">
  <input type="hidden" name="plan" value="PLAN_TEST">
  <button type="submit" class="btn">&#128179; Ir al checkout Wompi ($5.000)</button>
</form>
<br>
<a href="/core/planes/" style="color:#6b7280;">&larr; Volver a planes reales</a>
</body></html>"""
    return HttpResponse(html)


# ============================================================================
# Add-ons Recurrentes — Validación y Link de Pago
# ============================================================================

def _calcular_monto_link(plan_key, addons_dict):
    """Calcula el monto total (IVA incluido) de un plan + add-ons."""
    monto = Decimal('0')
    if plan_key and plan_key in PLANES:
        monto += PLANES[plan_key]['precio_total']
    monto += Decimal(str(addons_dict.get('tecnicos', 0) or 0)) * ADDONS['usuario_tecnico']['precio_total']
    monto += Decimal(str(addons_dict.get('admins', 0) or 0)) * ADDONS['usuario_admin']['precio_total']
    monto += Decimal(str(addons_dict.get('gerentes', 0) or 0)) * ADDONS['usuario_gerente']['precio_total']
    monto += Decimal(str(addons_dict.get('bloques_equipos', 0) or 0)) * ADDONS['equipos_50']['precio_total']
    monto += Decimal(str(addons_dict.get('bloques_storage', 0) or 0)) * ADDONS['storage_5gb']['precio_total']
    return monto


def _validar_reduccion_addons(empresa, plan_key, nuevos_addons):
    """
    Verifica que reducir add-ons no deje la empresa por debajo de su uso actual.
    Retorna lista de mensajes de error (vacía = todo ok).
    """
    errores = []

    # ── Límite de equipos ──────────────────────────────────────────────────
    equipos_base = PLANES[plan_key]['equipos'] if plan_key and plan_key in PLANES else (
        empresa.limite_equipos_empresa
        - (empresa.addons_recurrentes.get('bloques_equipos', 0) * 50)
    )
    nuevo_limite_eq = equipos_base + int(nuevos_addons.get('bloques_equipos', 0)) * 50
    equipos_activos = empresa.equipos.exclude(estado__in=['De Baja', 'Inactivo']).count()
    if equipos_activos > nuevo_limite_eq:
        errores.append(
            f"Tienes {equipos_activos} equipos activos. El nuevo límite sería {nuevo_limite_eq}. "
            f"Debes tener máximo {nuevo_limite_eq} equipos activos para reducir."
        )

    # ── Límite de almacenamiento ───────────────────────────────────────────
    if plan_key and plan_key in PLANES:
        storage_base_mb = PLANES[plan_key]['almacenamiento_mb']
    else:
        storage_base_mb = (
            empresa.limite_almacenamiento_mb
            - (empresa.addons_recurrentes.get('bloques_storage', 0) * 5 * 1024)
        )
    nuevo_limite_mb = storage_base_mb + int(nuevos_addons.get('bloques_storage', 0)) * 5 * 1024
    try:
        storage_usado_mb = empresa.get_total_storage_used_mb()
    except Exception:
        storage_usado_mb = 0
    if storage_usado_mb > nuevo_limite_mb:
        usado_gb = round(storage_usado_mb / 1024, 1)
        nuevo_gb = round(nuevo_limite_mb / 1024, 1)
        errores.append(
            f"Estás usando {usado_gb} GB de almacenamiento. El nuevo límite sería {nuevo_gb} GB. "
            f"Libera archivos antes de reducir el almacenamiento."
        )

    # ── Usuarios activos (si se reducen) ──────────────────────────────────
    addons_ant = empresa.addons_recurrentes or {}
    usuarios_extra_ant = (
        int(addons_ant.get('tecnicos', 0)) +
        int(addons_ant.get('admins', 0)) +
        int(addons_ant.get('gerentes', 0))
    )
    usuarios_extra_nuevo = (
        int(nuevos_addons.get('tecnicos', 0)) +
        int(nuevos_addons.get('admins', 0)) +
        int(nuevos_addons.get('gerentes', 0))
    )
    if usuarios_extra_nuevo < usuarios_extra_ant:
        # Solo advertencia — los usuarios se inactivan al vencer, no inmediatamente
        errores.append(
            '__advertencia_usuarios__'  # señal especial: mostrar aviso, no bloquear
        )

    return errores


def _enviar_link_pago_contabilidad(link):
    """Envía el link de pago a los correos de facturación de la empresa."""
    from django.conf import settings as _settings
    destinatarios = _get_correos_empresa(link.empresa)
    if not destinatarios:
        logger.warning(f"Sin correos de facturación para enviar link de pago: {link.empresa.nombre}")
        return

    app_url = getattr(_settings, 'APP_URL', 'https://app.sammetrologia.com')
    link_url = f"{app_url}/core/pagar/{link.token}/"

    plan_nombre = PLANES[link.plan_seleccionado]['nombre'] if link.plan_seleccionado and link.plan_seleccionado in PLANES else None
    addons = link.addons or {}
    monto_fmt = f"${link.monto_total:,.0f} COP"

    filas_html = ''
    filas_txt = ''
    if plan_nombre:
        filas_html += f"<tr><td>Plan</td><td><strong>{plan_nombre}</strong></td></tr>"
        filas_txt += f"  Plan: {plan_nombre}\n"
    if addons.get('tecnicos'):
        filas_html += f"<tr><td>Técnicos adicionales</td><td>+{addons['tecnicos']}</td></tr>"
        filas_txt += f"  Técnicos adicionales: +{addons['tecnicos']}\n"
    if addons.get('admins'):
        filas_html += f"<tr><td>Admins adicionales</td><td>+{addons['admins']}</td></tr>"
        filas_txt += f"  Admins adicionales: +{addons['admins']}\n"
    if addons.get('gerentes'):
        filas_html += f"<tr><td>Gerentes adicionales</td><td>+{addons['gerentes']}</td></tr>"
        filas_txt += f"  Gerentes adicionales: +{addons['gerentes']}\n"
    if addons.get('bloques_equipos'):
        filas_html += f"<tr><td>Equipos adicionales</td><td>+{addons['bloques_equipos'] * 50} ({addons['bloques_equipos']} bloque(s))</td></tr>"
        filas_txt += f"  Equipos adicionales: +{addons['bloques_equipos'] * 50}\n"
    if addons.get('bloques_storage'):
        filas_html += f"<tr><td>Almacenamiento adicional</td><td>+{addons['bloques_storage'] * 5} GB</td></tr>"
        filas_txt += f"  Almacenamiento adicional: +{addons['bloques_storage'] * 5} GB\n"

    expira = link.fecha_expiracion.strftime('%d/%m/%Y')
    asunto = f"Pago pendiente SAM — {monto_fmt}"
    html = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">{_EMAIL_STYLE}</head>
<body><div class="wrap"><div class="card">
  <div class="hdr"><h1>SAM METROLOGÍA</h1><p>Link de pago para {link.empresa.nombre}</p></div>
  <div class="body">
    <span class="badge" style="background:#dbeafe;color:#1e40af;">Pago pendiente</span>
    <p>Hay un pago pendiente para la cuenta <strong>{link.empresa.nombre}</strong>:</p>
    <table class="det">
      {filas_html}
      <tr><td>Total (IVA incluido)</td><td><strong>{monto_fmt}</strong></td></tr>
      <tr><td>Link válido hasta</td><td>{expira}</td></tr>
    </table>
    <a href="{link_url}" class="btn">Pagar ahora — {monto_fmt} →</a>
    <p style="font-size:12px;color:#888;">No necesitas iniciar sesión para pagar. El link expira el {expira}.</p>
    <div class="sig-name">Equipo Comercial SAM Metrología</div>
    <div class="sig-info">
      SAM Metrología S.A.S<br>
      <a href="https://sammetrologia.com">sammetrologia.com</a><br>
      WhatsApp: +57 324 799 0534 &nbsp;|&nbsp; comercial@sammetrologia.com
    </div>
  </div>
  <div class="ftr"><strong>SAM Metrología | Gestión Metrológica 4.0</strong></div>
</div></div></body></html>"""

    texto = (
        f"Pago pendiente para {link.empresa.nombre}:\n\n"
        f"{filas_txt}"
        f"  Total: {monto_fmt}\n\n"
        f"Pagar en: {link_url}\n"
        f"(Link válido hasta el {expira})\n\n"
        f"SAM Metrología — comercial@sammetrologia.com"
    )
    ok = _send_html_email(asunto, texto, html, destinatarios)
    if ok:
        logger.info(f"Link de pago enviado a {destinatarios} para {link.empresa.nombre} — {link.token[:8]}")
        link.correo_notificado = True
        link.save(update_fields=['correo_notificado'])


@login_required
@require_POST
def generar_link_pago(request):
    """
    Admin/Gerente configura plan + add-ons y genera un link de pago único.
    Envía el link por email a correos_facturacion y lo devuelve en JSON.
    """
    empresa = request.user.empresa
    if not empresa:
        return JsonResponse({'ok': False, 'errores': ['Sin empresa asociada.']})
    if not (request.user.is_administrador() or request.user.is_gerente()):
        return JsonResponse({'ok': False, 'errores': ['Sin permisos.']}, status=403)

    def _int(key):
        try:
            return max(0, int(request.POST.get(key, 0) or 0))
        except (ValueError, TypeError):
            return 0

    plan_key = request.POST.get('plan', '').upper() or None
    if plan_key and plan_key not in PLANES:
        plan_key = None

    nuevos_addons = {
        'tecnicos':        _int('tecnicos'),
        'admins':          _int('admins'),
        'gerentes':        _int('gerentes'),
        'bloques_equipos': _int('bloques_equipos'),
        'bloques_storage': _int('bloques_storage'),
    }

    # Validar reducción de límites
    errores_raw = _validar_reduccion_addons(empresa, plan_key, nuevos_addons)
    tiene_advertencia_usuarios = '__advertencia_usuarios__' in errores_raw
    errores = [e for e in errores_raw if e != '__advertencia_usuarios__']
    if errores:
        return JsonResponse({'ok': False, 'errores': errores})

    monto_total = _calcular_monto_link(plan_key, nuevos_addons)
    if monto_total <= 0:
        return JsonResponse({'ok': False, 'errores': ['Selecciona al menos un plan o add-on.']})

    from django.utils import timezone
    from datetime import timedelta

    token = uuid.uuid4().hex
    link = LinkPago.objects.create(
        empresa=empresa,
        token=token,
        plan_seleccionado=plan_key,
        addons=nuevos_addons,
        monto_total=monto_total,
        fecha_expiracion=timezone.now() + timedelta(days=7),
        creado_por=request.user,
    )
    # addons_recurrentes se actualiza SOLO cuando el pago sea confirmado (en el webhook)

    # Enviar email a contabilidad
    try:
        _enviar_link_pago_contabilidad(link)
    except Exception as e:
        logger.error(f"Error enviando link de pago por email: {e}")

    app_url = getattr(settings, 'APP_URL', 'https://app.sammetrologia.com')
    link_url = f"{app_url}/core/pagar/{token}/"

    return JsonResponse({
        'ok': True,
        'link': link_url,
        'token': token,
        'monto': str(monto_total),
        'advertencia_usuarios': tiene_advertencia_usuarios,
    })


def pagar_link(request, token):
    """
    Página pública de pago. No requiere login.
    Contabilidad entra aquí desde el email y paga directamente con Wompi.
    """
    try:
        link = LinkPago.objects.select_related('empresa').get(token=token)
    except LinkPago.DoesNotExist:
        return render(request, 'core/pagar_link.html', {'error': 'Link no encontrado o inválido.'})

    if not link.esta_vigente():
        return render(request, 'core/pagar_link.html', {
            'error': 'Este link ya fue usado o expiró.',
            'empresa': link.empresa,
        })

    if request.method == 'POST':
        # Crear transacción y redirigir a Wompi
        public_key = getattr(settings, 'WOMPI_PUBLIC_KEY', '')
        integrity_secret = getattr(settings, 'WOMPI_INTEGRITY_SECRET', '')
        if not public_key:
            return render(request, 'core/pagar_link.html', {
                'error': 'Pasarela de pagos no disponible. Contacta soporte.',
                'link': link,
            })

        referencia = f"SAM-LINK-{link.empresa.id}-{uuid.uuid4().hex[:10].upper()}"
        monto_centavos = int(link.monto_total * 100)

        transaccion = TransaccionPago.objects.create(
            empresa=link.empresa,
            referencia_pago=referencia,
            estado='pendiente',
            monto=link.monto_total,
            moneda='COP',
            plan_seleccionado=link.plan_seleccionado or 'ADDON',
            datos_addon={
                **(link.addons or {}),
                '_link_pago_token': link.token,
            },
            ip_cliente=_get_ip(request),
        )
        link.transaccion = transaccion
        link.save(update_fields=['transaccion'])

        redirect_url = quote(
            request.build_absolute_uri(f"/core/pagar/{token}/confirmado/"),
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

    # GET — mostrar resumen de pago
    plan_nombre = PLANES[link.plan_seleccionado]['nombre'] if link.plan_seleccionado and link.plan_seleccionado in PLANES else None
    addons = link.addons or {}
    items = []
    if plan_nombre:
        items.append({'nombre': plan_nombre, 'monto': PLANES[link.plan_seleccionado]['precio_total']})
    if addons.get('tecnicos'):
        items.append({'nombre': f"+{addons['tecnicos']} Técnico(s) adicional(es)", 'monto': addons['tecnicos'] * ADDONS['usuario_tecnico']['precio_total']})
    if addons.get('admins'):
        items.append({'nombre': f"+{addons['admins']} Admin(s) adicional(es)", 'monto': addons['admins'] * ADDONS['usuario_admin']['precio_total']})
    if addons.get('gerentes'):
        items.append({'nombre': f"+{addons['gerentes']} Gerente(s) adicional(es)", 'monto': addons['gerentes'] * ADDONS['usuario_gerente']['precio_total']})
    if addons.get('bloques_equipos'):
        items.append({'nombre': f"+{addons['bloques_equipos'] * 50} equipos ({addons['bloques_equipos']} bloque(s))", 'monto': addons['bloques_equipos'] * ADDONS['equipos_50']['precio_total']})
    if addons.get('bloques_storage'):
        items.append({'nombre': f"+{addons['bloques_storage'] * 5} GB almacenamiento", 'monto': addons['bloques_storage'] * ADDONS['storage_5gb']['precio_total']})

    return render(request, 'core/pagar_link.html', {
        'link': link,
        'items': items,
        'empresa': link.empresa,
    })


def pagar_link_confirmado(request, token):
    """Página de confirmación después de que Wompi redirige de vuelta."""
    try:
        link = LinkPago.objects.select_related('empresa', 'transaccion').get(token=token)
    except LinkPago.DoesNotExist:
        return render(request, 'core/pagar_link.html', {'error': 'Link no encontrado.'})
    return render(request, 'core/pagar_link.html', {
        'link': link,
        'confirmacion': True,
        'empresa': link.empresa,
    })


# ============================================================================
# Toggle Renovación Automática
# ============================================================================

@login_required
@require_POST
def toggle_renovacion_automatica(request):
    """Activa o desactiva la renovación automática para la empresa del usuario."""
    empresa = request.user.empresa
    if not empresa:
        return HttpResponseForbidden()
    if not (request.user.is_administrador() or request.user.is_gerente()):
        return HttpResponseForbidden()
    # Usa el estado explícito enviado por el form para evitar inconsistencias con caché
    activar = request.POST.get('activar')
    if activar is not None:
        empresa.renovacion_automatica = (activar == '1')
    else:
        empresa.renovacion_automatica = not empresa.renovacion_automatica
    empresa.save(update_fields=['renovacion_automatica'])
    try:
        from core.signals import invalidate_dashboard_cache
        invalidate_dashboard_cache(empresa.id)
    except Exception:
        pass
    estado = 'activa' if empresa.renovacion_automatica else 'inactiva'
    messages.success(request, f"Renovación automática {estado}.")
    return redirect(request.POST.get('next', 'core:planes'))


# ============================================================================
# Guardar Tarjeta para Autopago
# ============================================================================

@login_required
def guardar_tarjeta_autopago(request):
    """
    Permite al administrador/gerente guardar una tarjeta para cobros automáticos.

    GET:  Obtiene los acceptance_tokens de Wompi y renderiza el formulario.
    POST: Recibe el card_token (ya tokenizado en el frontend vía JS + public_key)
          y crea un payment_source en Wompi con la clave privada.
    """
    empresa = request.user.empresa
    if not empresa:
        return HttpResponseForbidden()
    if not (request.user.is_administrador() or request.user.is_gerente()):
        return HttpResponseForbidden()

    public_key = getattr(settings, 'WOMPI_PUBLIC_KEY', '')
    wompi_base = _get_wompi_base_url()

    if request.method == 'POST':
        card_token = request.POST.get('card_token', '').strip()
        acceptance_token = request.POST.get('acceptance_token', '').strip()
        personal_auth_token = request.POST.get('personal_auth_token', '').strip()

        if not card_token:
            messages.error(request, "No se recibió el token de tarjeta. Verifica los datos e intenta de nuevo.")
            return redirect('core:guardar_tarjeta_autopago')

        correos = _get_correos_empresa(empresa)
        correo = correos[0] if correos else empresa.email or ''

        ps_id = _guardar_payment_source(
            empresa, card_token, correo,
            acceptance_token=acceptance_token,
            personal_auth_token=personal_auth_token,
        )
        if ps_id:
            messages.success(
                request,
                "Tarjeta guardada correctamente. Tu plan se renovará automáticamente al vencer."
            )
            return redirect('core:planes')
        else:
            messages.error(
                request,
                "No se pudo guardar la tarjeta. Verifica los datos o usa una tarjeta diferente."
            )
            return redirect('core:guardar_tarjeta_autopago')

    # GET — obtener acceptance_tokens de Wompi
    acceptance_token = personal_auth_token = terms_permalink = personal_permalink = ''
    try:
        r = _requests.get(
            f"{wompi_base}/merchants/{public_key}",
            timeout=10,
        )
        if r.status_code == 200:
            data = r.json().get('data', {})
            presigned = data.get('presigned_acceptance', {})
            presigned_personal = data.get('presigned_personal_data_auth', {})
            acceptance_token = presigned.get('acceptance_token', '')
            personal_auth_token = presigned_personal.get('acceptance_token', '')
            terms_permalink = presigned.get('permalink', '')
            personal_permalink = presigned_personal.get('permalink', '')
        else:
            logger.warning(f"Wompi /merchants devolvió {r.status_code}")
    except Exception as e:
        logger.error(f"Error obteniendo acceptance tokens de Wompi: {e}")
        messages.warning(request, "No se pudo conectar con el sistema de pagos. Intenta más tarde.")
        return redirect('core:planes')

    return render(request, 'core/guardar_tarjeta.html', {
        'empresa': empresa,
        'public_key': public_key,
        'wompi_sandbox': getattr(settings, 'WOMPI_SANDBOX', True),
        'wompi_base_url': wompi_base,
        'acceptance_token': acceptance_token,
        'personal_auth_token': personal_auth_token,
        'terms_permalink': terms_permalink,
        'personal_permalink': personal_permalink,
    })
