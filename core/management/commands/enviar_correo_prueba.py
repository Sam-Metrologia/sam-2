# core/management/commands/enviar_correo_prueba.py
# Envia los 3 tipos de correo de pago a una direccion de prueba.
# Uso:
#   python manage.py enviar_correo_prueba --email metrologiasam@gmail.com
#   python manage.py enviar_correo_prueba --email metrologiasam@gmail.com --empresa-id 34

import os
from django.core.management.base import BaseCommand

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
  .btn{display:inline-block;background:#003366;color:#fff!important;padding:14px 32px;
       border-radius:6px;text-decoration:none;font-weight:600;margin:20px 0;font-size:15px;}
  .sig-name{color:#003366;font-weight:700;font-size:15px;margin-top:22px;}
  .sig-info{font-size:13px;color:#666;line-height:1.7;}
  .ftr{background:#1a1a1a;padding:22px 35px;text-align:center;color:#888;font-size:12px;}
  .ftr strong{color:#aaa;}
  a{color:#0056b3;}
  .note{background:#f0f9ff;border-left:4px solid #0ea5e9;padding:12px 16px;border-radius:4px;
        font-size:13px;color:#0369a1;margin:16px 0;}
</style>"""


def _html_aviso_7_dias(nombre_empresa, plan, addons_str, monto, fecha_vence, link):
    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><title>Tu plan SAM vence en 7 dias</title>{_EMAIL_STYLE}</head>
<body>
<div class="wrap"><div class="card">
  <div class="hdr"><h1>SAM METROLOGIA</h1><p>Control Digital e Inteligencia Metrologica</p></div>
  <div class="body">
    <span class="badge" style="background:#fef3c7;color:#92400e;">Tu plan vence en 7 dias</span>
    <p>Hola, <strong>{nombre_empresa}</strong>:</p>
    <p>Tu plan de SAM vence el <strong>{fecha_vence}</strong>. Para evitar interrupciones,
    renuevalo antes de esa fecha.</p>
    <table class="det">
      <tr><td>Plan actual</td><td><strong>{plan}</strong></td></tr>
      <tr><td>Add-ons activos</td><td>{addons_str}</td></tr>
      <tr><td>Total a pagar</td><td><strong>{monto}</strong> (IVA incluido)</td></tr>
      <tr><td>Fecha de vencimiento</td><td><strong>{fecha_vence}</strong></td></tr>
    </table>
    <div class="note">
      Si pagaste con tarjeta y tienes renovacion automatica activada,
      <strong>no necesitas hacer nada</strong> — el cobro se realiza automaticamente al vencer.
    </div>
    <p>Si prefieres pagar manualmente, usa este enlace (no requiere usuario ni contrasena):</p>
    <a href="{link}" class="btn">Renovar mi plan &rarr;</a>
    <p style="font-size:12px;color:#999;">Este enlace es valido por 8 dias y puede usarlo
    directamente el area de contabilidad.</p>
    <p>Atentamente,</p>
    <div class="sig-name">Equipo Comercial SAM Metrologia</div>
    <div class="sig-info">
      SAM Metrologia S.A.S<br>
      <a href="https://sammetrologia.com">sammetrologia.com</a><br>
      WhatsApp: +57 324 799 0534 &nbsp;|&nbsp; comercial@sammetrologia.com
    </div>
  </div>
  <div class="ftr">
    <strong>SAM Metrologia | Gestion Metrologica 4.0</strong><br>
    Este correo fue generado automaticamente. Por favor no respondas a este mensaje.
  </div>
</div></div>
</body></html>"""


def _html_vencio_hoy(nombre_empresa, plan, addons_str, monto, link):
    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><title>Tu plan SAM vencio hoy</title>{_EMAIL_STYLE}</head>
<body>
<div class="wrap"><div class="card">
  <div class="hdr"><h1>SAM METROLOGIA</h1><p>Control Digital e Inteligencia Metrologica</p></div>
  <div class="body">
    <span class="badge" style="background:#fee2e2;color:#991b1b;">Tu plan vencio hoy</span>
    <p>Hola, <strong>{nombre_empresa}</strong>:</p>
    <p>Tu plan de SAM <strong>vencio hoy</strong>. Para recuperar el acceso completo,
    renuevalo lo antes posible.</p>
    <table class="det">
      <tr><td>Plan</td><td><strong>{plan}</strong></td></tr>
      <tr><td>Add-ons</td><td>{addons_str}</td></tr>
      <tr><td>Total</td><td><strong>{monto}</strong> (IVA incluido)</td></tr>
    </table>
    <p>Paga de forma rapida y segura con este enlace (no requiere usuario ni contrasena):</p>
    <a href="{link}" class="btn">Pagar ahora &rarr;</a>
    <p style="font-size:12px;color:#999;">Este enlace es valido por 8 dias y puede usarlo
    directamente el area de contabilidad.</p>
    <p>Tienes preguntas? Escribenos por WhatsApp:
    <a href="https://wa.me/573247990534">+57 324 799 0534</a></p>
    <p>Atentamente,</p>
    <div class="sig-name">Equipo Comercial SAM Metrologia</div>
    <div class="sig-info">
      SAM Metrologia S.A.S<br>
      <a href="https://sammetrologia.com">sammetrologia.com</a><br>
      WhatsApp: +57 324 799 0534 &nbsp;|&nbsp; comercial@sammetrologia.com
    </div>
  </div>
  <div class="ftr">
    <strong>SAM Metrologia | Gestion Metrologica 4.0</strong><br>
    Este correo fue generado automaticamente. Por favor no respondas a este mensaje.
  </div>
</div></div>
</body></html>"""


def _html_cobro_fallido(nombre_empresa, plan, addons_str, monto, link):
    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><title>No pudimos renovar tu plan SAM automaticamente</title>{_EMAIL_STYLE}</head>
<body>
<div class="wrap"><div class="card">
  <div class="hdr"><h1>SAM METROLOGIA</h1><p>Control Digital e Inteligencia Metrologica</p></div>
  <div class="body">
    <span class="badge" style="background:#fee2e2;color:#991b1b;">Cobro automatico fallido</span>
    <p>Hola, <strong>{nombre_empresa}</strong>:</p>
    <p>Intentamos renovar tu plan automaticamente pero el cobro no pudo procesarse
    (tarjeta rechazada, fondos insuficientes u otro inconveniente).</p>
    <table class="det">
      <tr><td>Plan</td><td><strong>{plan}</strong></td></tr>
      <tr><td>Add-ons</td><td>{addons_str}</td></tr>
      <tr><td>Total</td><td><strong>{monto}</strong> (IVA incluido)</td></tr>
    </table>
    <p>Por favor renueva manualmente para continuar sin interrupciones
    (no requiere usuario ni contrasena):</p>
    <a href="{link}" class="btn">Renovar mi plan manualmente &rarr;</a>
    <p style="font-size:12px;color:#999;">Este enlace es valido por 8 dias y puede usarlo
    directamente el area de contabilidad.</p>
    <p>Necesitas ayuda?
    <a href="https://wa.me/573247990534">WhatsApp +57 324 799 0534</a></p>
    <p>Atentamente,</p>
    <div class="sig-name">Equipo Comercial SAM Metrologia</div>
    <div class="sig-info">
      SAM Metrologia S.A.S<br>
      <a href="https://sammetrologia.com">sammetrologia.com</a><br>
      WhatsApp: +57 324 799 0534 &nbsp;|&nbsp; comercial@sammetrologia.com
    </div>
  </div>
  <div class="ftr">
    <strong>SAM Metrologia | Gestion Metrologica 4.0</strong><br>
    Este correo fue generado automaticamente. Por favor no respondas a este mensaje.
  </div>
</div></div>
</body></html>"""


def _datos_empresa(empresa_id):
    """Obtiene datos reales de la empresa si se especifica un ID."""
    from core.models import Empresa, TransaccionPago
    from core.views.pagos import PLANES, ADDONS
    from decimal import Decimal
    from django.conf import settings
    import uuid
    from django.utils import timezone
    from datetime import timedelta

    empresa = Empresa.objects.get(id=empresa_id)
    nombre = empresa.nombre

    ultima_tx = (
        TransaccionPago.objects
        .filter(empresa=empresa, estado='aprobado')
        .exclude(plan_seleccionado='ADDON')
        .order_by('-fecha_creacion')
        .first()
    )

    plan_key = ultima_tx.plan_seleccionado if ultima_tx else None
    plan_nombre = PLANES[plan_key]['nombre'] if plan_key and plan_key in PLANES else (plan_key or 'Sin plan base')

    addons = empresa.addons_recurrentes or {}
    partes = []
    if addons.get('tecnicos'):
        partes.append(f"{addons['tecnicos']} usuario(s) tecnico(s)")
    if addons.get('admins'):
        partes.append(f"{addons['admins']} usuario(s) admin(s)")
    if addons.get('gerentes'):
        partes.append(f"{addons['gerentes']} gerente(s)")
    if addons.get('bloques_equipos'):
        partes.append(f"{addons['bloques_equipos']} bloque(s) de 50 equipos")
    if addons.get('bloques_storage'):
        partes.append(f"{addons['bloques_storage']} bloque(s) de 5 GB storage")
    addons_str = ' · '.join(partes) if partes else 'Sin add-ons'

    # Calcular monto
    monto = PLANES[plan_key]['precio_total'] if plan_key and plan_key in PLANES else (ultima_tx.monto if ultima_tx else Decimal('0'))
    monto += Decimal(str(addons.get('tecnicos', 0) or 0)) * ADDONS['usuario_tecnico']['precio_total']
    monto += Decimal(str(addons.get('admins', 0) or 0)) * ADDONS['usuario_admin']['precio_total']
    monto += Decimal(str(addons.get('gerentes', 0) or 0)) * ADDONS['usuario_gerente']['precio_total']
    monto += Decimal(str(addons.get('bloques_equipos', 0) or 0)) * ADDONS['equipos_50']['precio_total']
    monto += Decimal(str(addons.get('bloques_storage', 0) or 0)) * ADDONS['storage_5gb']['precio_total']

    monto_str = f"${monto:,.0f} COP"

    # Fecha de vencimiento
    try:
        dias = empresa.get_dias_restantes_plan()
        if dias == float('inf'):
            fecha_vence = 'Sin fecha de vencimiento'
        else:
            from datetime import date, timedelta as td
            fecha_obj = date.today() + td(days=int(dias))
            meses = ['enero','febrero','marzo','abril','mayo','junio',
                     'julio','agosto','septiembre','octubre','noviembre','diciembre']
            fecha_vence = f"{fecha_obj.day} de {meses[fecha_obj.month-1]} de {fecha_obj.year}"
    except Exception:
        fecha_vence = 'Por confirmar'

    # Crear LinkPago real para el demo
    from core.models import LinkPago
    token = uuid.uuid4().hex
    LinkPago.objects.create(
        empresa=empresa,
        token=token,
        plan_seleccionado=plan_key,
        addons=addons if addons else {},
        monto_total=monto if monto > 0 else Decimal('0'),
        fecha_expiracion=timezone.now() + timedelta(days=8),
    )
    app_url = getattr(settings, 'APP_URL', 'https://app.sammetrologia.com')
    link = f"{app_url}/core/pagar/{token}/"

    return nombre, plan_nombre, addons_str, monto_str, fecha_vence, link


def _datos_demo():
    """Datos de ejemplo cuando no se especifica empresa."""
    nombre = "Laboratorio Demo S.A.S"
    plan = "Plan Profesional"
    addons_str = "50 equipos adicionales · 1 usuario tecnico"
    monto = "$1.190.000 COP"
    fecha_vence = "9 de marzo de 2026"
    link = "https://app.sammetrologia.com/core/pagar/abc123demo456/"
    return nombre, plan, addons_str, monto, fecha_vence, link


class Command(BaseCommand):
    help = 'Envia los 3 correos de pago de prueba a una direccion especificada'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            required=True,
            help='Correo destino (ej: metrologiasam@gmail.com)',
        )
        parser.add_argument(
            '--empresa-id',
            type=int,
            default=None,
            help='ID de empresa para usar datos reales (opcional)',
        )

    def handle(self, *args, **options):
        from django.core.mail import EmailMultiAlternatives

        email_destino = options['email']
        empresa_id = options.get('empresa_id')

        self.stdout.write(f"Preparando correos de prueba para: {email_destino}")

        if empresa_id:
            self.stdout.write(f"Usando datos reales de empresa ID={empresa_id}...")
            try:
                nombre, plan, addons_str, monto, fecha_vence, link = _datos_empresa(empresa_id)
                self.stdout.write(f"  Empresa: {nombre}")
                self.stdout.write(f"  Plan: {plan} | Monto: {monto}")
                self.stdout.write(f"  Link generado: {link}")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error cargando empresa {empresa_id}: {e}"))
                self.stdout.write("Usando datos de ejemplo...")
                nombre, plan, addons_str, monto, fecha_vence, link = _datos_demo()
        else:
            self.stdout.write("Usando datos de ejemplo (sin empresa real)...")
            nombre, plan, addons_str, monto, fecha_vence, link = _datos_demo()

        correos = [
            (
                "[DEMO] Tu plan SAM vence en 7 dias",
                _html_aviso_7_dias(nombre, plan, addons_str, monto, fecha_vence, link),
            ),
            (
                "[DEMO] Tu plan SAM vencio hoy - renueva aqui",
                _html_vencio_hoy(nombre, plan, addons_str, monto, link),
            ),
            (
                "[DEMO] No pudimos renovar tu plan SAM automaticamente",
                _html_cobro_fallido(nombre, plan, addons_str, monto, link),
            ),
        ]

        SAM_FROM = 'SAM Metrologia <comercial@sammetrologia.com>'
        enviados = 0

        for asunto, html in correos:
            try:
                msg = EmailMultiAlternatives(
                    subject=asunto,
                    body=asunto,
                    from_email=SAM_FROM,
                    to=[email_destino],
                )
                msg.attach_alternative(html, 'text/html')
                msg.send()
                self.stdout.write(f"  Enviado: {asunto}")
                enviados += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Error: {asunto}\n  -> {e}"))

        if enviados == len(correos):
            self.stdout.write(self.style.SUCCESS(
                f"\n{enviados} correos enviados a {email_destino}"
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f"\n{enviados}/{len(correos)} enviados."
            ))
            if enviados == 0:
                self.stdout.write(
                    "Verifica que EMAIL_HOST_USER y EMAIL_HOST_PASSWORD esten configurados en Render."
                )
