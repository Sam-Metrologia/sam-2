# core/management/commands/cobrar_renovaciones.py
# Cobra renovaciones automáticas y envía recordatorios de vencimiento.
# Diseñado para ejecutarse diariamente a las 7:00 AM (Colombia) vía GitHub Actions.

import logging
import uuid
from datetime import date
from decimal import Decimal

import requests

from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

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
  .badge{display:inline-block;padding:8px 18px;border-radius:20px;font-weight:700;font-size:15px;margin-bottom:20px;}
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


def _get_wompi_base_url():
    sandbox = getattr(settings, 'WOMPI_SANDBOX', True)
    return 'https://sandbox.wompi.co/v1' if sandbox else 'https://production.wompi.co/v1'


def _get_correos_empresa(empresa):
    correos = []
    if empresa.correos_facturacion:
        for c in empresa.correos_facturacion.split(','):
            c = c.strip()
            if c:
                correos.append(c)
    if not correos and empresa.email:
        correos.append(empresa.email)
    return correos


def _send_html_email(asunto, texto_plano, html, destinatarios):
    from django.core.mail import EmailMultiAlternatives
    try:
        msg = EmailMultiAlternatives(asunto, texto_plano, SAM_FROM_LABEL, destinatarios)
        msg.attach_alternative(html, 'text/html')
        msg.send()
        return True
    except Exception as e:
        logger.error(f"Error enviando email '{asunto}' a {destinatarios}: {e}")
        return False


def _url_pago(empresa):
    """Construye URL de la página de planes para la empresa."""
    app_url = getattr(settings, 'APP_URL', 'https://app.sammetrologia.com')
    return f"{app_url}/core/planes/"


def _enviar_aviso_vencimiento(empresa):
    """Envía aviso único: el plan vence en 7 días."""
    destinatarios = _get_correos_empresa(empresa)
    if not destinatarios:
        logger.warning(f"Sin correos para aviso vencimiento: {empresa.nombre}")
        return

    link = _url_pago(empresa)
    asunto = "Tu plan SAM vence en 7 días"
    html = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">{_EMAIL_STYLE}</head>
<body><div class="wrap"><div class="card">
  <div class="hdr"><h1>SAM METROLOGÍA</h1><p>Control Digital e Inteligencia Metrológica</p></div>
  <div class="body">
    <span class="badge" style="background:#fef3c7;color:#92400e;">Tu plan vence en 7 días</span>
    <p>Hola, <strong>{empresa.nombre}</strong>:</p>
    <p>Tu plan de SAM vence en <strong>7 días</strong>. Para evitar interrupciones, renuévalo ahora.</p>
    <p>Si pagaste con tarjeta y activaste la renovación automática, <strong>no necesitas hacer nada</strong>;
       el cobro se realizará automáticamente al vencer.</p>
    <a href="{link}" class="btn">Renovar mi plan →</a>
    <p>Atentamente,</p>
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
        f"Hola {empresa.nombre},\n\n"
        f"Tu plan de SAM vence en 7 días.\n"
        f"Renuévalo aquí: {link}\n\n"
        f"SAM Metrología — comercial@sammetrologia.com"
    )
    _send_html_email(asunto, texto, html, destinatarios)
    logger.info(f"Aviso vencimiento (7 días) enviado a {empresa.nombre} → {destinatarios}")


def _enviar_recordatorio_pago(empresa, ultima_tx):
    """Envía recordatorio urgente: el plan venció hoy (sin token de tarjeta)."""
    destinatarios = _get_correos_empresa(empresa)
    if not destinatarios:
        return

    link = _url_pago(empresa)
    asunto = "Tu plan SAM venció hoy — renueva aquí"
    html = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">{_EMAIL_STYLE}</head>
<body><div class="wrap"><div class="card">
  <div class="hdr"><h1>SAM METROLOGÍA</h1><p>Control Digital e Inteligencia Metrológica</p></div>
  <div class="body">
    <span class="badge" style="background:#fee2e2;color:#991b1b;">Tu plan venció hoy</span>
    <p>Hola, <strong>{empresa.nombre}</strong>:</p>
    <p>Tu plan de SAM venció hoy. Para recuperar el acceso completo, renuévalo ahora.</p>
    <a href="{link}" class="btn">Renovar mi plan →</a>
    <p>¿Tienes preguntas? Escríbenos por WhatsApp: <a href="https://wa.me/573247990534">+57 324 799 0534</a></p>
    <p>Atentamente,</p>
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
        f"Hola {empresa.nombre},\n\n"
        f"Tu plan de SAM venció hoy.\n"
        f"Renuévalo aquí: {link}\n\n"
        f"SAM Metrología — comercial@sammetrologia.com"
    )
    _send_html_email(asunto, texto, html, destinatarios)
    logger.info(f"Recordatorio pago (vencido hoy) enviado a {empresa.nombre} → {destinatarios}")


def _enviar_email_cobro_fallido(empresa):
    """Notifica que el cobro automático falló y pide renovar manualmente."""
    destinatarios = _get_correos_empresa(empresa)
    if not destinatarios:
        return

    link = _url_pago(empresa)
    asunto = "No pudimos renovar tu plan SAM automáticamente"
    html = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">{_EMAIL_STYLE}</head>
<body><div class="wrap"><div class="card">
  <div class="hdr"><h1>SAM METROLOGÍA</h1><p>Control Digital e Inteligencia Metrológica</p></div>
  <div class="body">
    <span class="badge" style="background:#fee2e2;color:#991b1b;">Cobro automático fallido</span>
    <p>Hola, <strong>{empresa.nombre}</strong>:</p>
    <p>Intentamos renovar tu plan automáticamente pero el cobro no pudo procesarse
       (tarjeta rechazada, fondos insuficientes u otro error).</p>
    <p>Por favor renueva tu plan manualmente para continuar sin interrupciones:</p>
    <a href="{link}" class="btn">Renovar mi plan →</a>
    <p>Si necesitas ayuda, escríbenos: <a href="https://wa.me/573247990534">WhatsApp +57 324 799 0534</a></p>
    <p>Atentamente,</p>
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
        f"Hola {empresa.nombre},\n\n"
        f"El cobro automático de tu plan SAM falló.\n"
        f"Renueva manualmente en: {link}\n\n"
        f"SAM Metrología — comercial@sammetrologia.com"
    )
    _send_html_email(asunto, texto, html, destinatarios)
    logger.warning(f"Email cobro fallido enviado a {empresa.nombre} → {destinatarios}")


def _calcular_monto_renovacion(empresa, ultima_tx):
    """
    Calcula el monto de renovación = plan base + add-ons recurrentes.
    Retorna (monto_total, addons_dict).
    """
    from core.views.pagos import PLANES, ADDONS
    from decimal import Decimal

    plan_key = ultima_tx.plan_seleccionado
    monto = PLANES[plan_key]['precio_total'] if plan_key and plan_key in PLANES else ultima_tx.monto

    addons = empresa.addons_recurrentes or {}
    monto += Decimal(str(addons.get('tecnicos', 0) or 0)) * ADDONS['usuario_tecnico']['precio_total']
    monto += Decimal(str(addons.get('admins', 0) or 0)) * ADDONS['usuario_admin']['precio_total']
    monto += Decimal(str(addons.get('gerentes', 0) or 0)) * ADDONS['usuario_gerente']['precio_total']
    monto += Decimal(str(addons.get('bloques_equipos', 0) or 0)) * ADDONS['equipos_50']['precio_total']
    monto += Decimal(str(addons.get('bloques_storage', 0) or 0)) * ADDONS['storage_5gb']['precio_total']

    return monto, addons


def _cobrar_automatico(empresa, ultima_tx):
    """
    Realiza el cobro automático usando el payment_source_id guardado en Wompi.
    Incluye plan base + add-ons recurrentes en el monto.
    Retorna True si Wompi aceptó la transacción, False en caso contrario.
    El webhook de Wompi activará el plan al recibir APPROVED.
    """
    private_key = getattr(settings, 'WOMPI_PRIVATE_KEY', '')
    if not private_key:
        logger.error("WOMPI_PRIVATE_KEY no configurado; no se puede cobrar automáticamente.")
        return False

    from core.models import TransaccionPago

    monto_total, addons_recurrentes = _calcular_monto_renovacion(empresa, ultima_tx)
    referencia = f"SAM-AUTO-{empresa.id}-{uuid.uuid4().hex[:10].upper()}"
    monto_centavos = int(monto_total * 100)
    correos = _get_correos_empresa(empresa)
    correo = correos[0] if correos else empresa.email or ''

    payload = {
        'amount_in_cents': monto_centavos,
        'currency': 'COP',
        'customer_email': correo,
        'payment_method': {
            'type': 'CARD',
            'installments': 1,
        },
        'payment_source_id': int(empresa.wompi_payment_source_id),
        'reference': referencia,
    }

    # Crear registro de transacción pendiente antes de cobrar
    transaccion = TransaccionPago.objects.create(
        empresa=empresa,
        referencia_pago=referencia,
        estado='pendiente',
        monto=monto_total,
        moneda='COP',
        plan_seleccionado=ultima_tx.plan_seleccionado,
        datos_addon=addons_recurrentes if addons_recurrentes else None,
        ip_cliente='auto',
    )

    try:
        r = requests.post(
            f"{_get_wompi_base_url()}/transactions",
            json=payload,
            headers={'Authorization': f'Bearer {private_key}'},
            timeout=15,
        )
        data = r.json()
        estado_wompi = data.get('data', {}).get('status', '')

        if r.status_code in (200, 201) and estado_wompi in ('APPROVED', 'PENDING'):
            logger.info(
                f"Cobro automático enviado a Wompi para {empresa.nombre}: "
                f"{referencia} | estado={estado_wompi}"
            )
            return True
        else:
            logger.warning(
                f"Cobro automático rechazado para {empresa.nombre}: "
                f"HTTP {r.status_code} | {data}"
            )
            transaccion.estado = 'rechazado'
            transaccion.save(update_fields=['estado'])
            _enviar_email_cobro_fallido(empresa)
            return False

    except Exception as e:
        logger.error(f"Error en cobro automático para {empresa.nombre}: {e}")
        transaccion.estado = 'error'
        transaccion.save(update_fields=['estado'])
        _enviar_email_cobro_fallido(empresa)
        return False


class Command(BaseCommand):
    help = 'Cobra renovaciones automáticas y envía recordatorios de vencimiento'

    def handle(self, *args, **options):
        from core.models import Empresa, TransaccionPago

        empresas_activas = Empresa.objects.filter(
            estado_suscripcion='Activo',
            is_deleted=False,
            renovacion_automatica=True,
        )

        cobros_ok = cobros_fallo = recordatorios = avisos = 0

        for empresa in empresas_activas:
            try:
                dias = empresa.get_dias_restantes_plan()
            except Exception as e:
                logger.error(f"Error obteniendo días restantes para {empresa.nombre}: {e}")
                continue

            if dias == float('inf'):
                continue  # acceso manual o sin límite de fecha

            # Aviso único 7 días antes
            if dias == 7:
                _enviar_aviso_vencimiento(empresa)
                avisos += 1

            # Acción en el día del vencimiento
            elif dias == 0:
                ultima_tx = (
                    TransaccionPago.objects
                    .filter(empresa=empresa, estado='aprobado')
                    .exclude(plan_seleccionado='ADDON')
                    .order_by('-fecha_creacion')
                    .first()
                )

                if not ultima_tx:
                    logger.warning(
                        f"No hay transacción aprobada para cobrar renovación de {empresa.nombre}"
                    )
                    continue

                if empresa.wompi_payment_source_id:
                    ok = _cobrar_automatico(empresa, ultima_tx)
                    if ok:
                        cobros_ok += 1
                    else:
                        cobros_fallo += 1
                else:
                    _enviar_recordatorio_pago(empresa, ultima_tx)
                    recordatorios += 1

        resumen = (
            f"Cobros OK: {cobros_ok} | Fallidos: {cobros_fallo} | "
            f"Recordatorios: {recordatorios} | Avisos 7d: {avisos}"
        )
        self.stdout.write(resumen)
        logger.info(f"cobrar_renovaciones completado — {resumen}")
