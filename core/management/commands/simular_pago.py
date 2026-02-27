# core/management/commands/simular_pago.py
# Simula un pago aprobado de Wompi para probar la activación de planes y add-ons.
# USO:
#   python manage.py simular_pago --empresa 1 --plan MENSUAL
#   python manage.py simular_pago --empresa 1 --addon --tecnicos 2 --bloques-equipos 1

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from core.models import Empresa, TransaccionPago
from core.views.pagos import PLANES, ADDONS
import uuid


class Command(BaseCommand):
    help = 'Simula un pago aprobado de Wompi para probar la activación sin pasarela real.'

    def add_arguments(self, parser):
        parser.add_argument('--empresa', type=int, required=True, help='ID de la empresa')
        parser.add_argument('--plan', type=str, help='Clave del plan (ej: MENSUAL, ANUAL, BASICO_MENSUAL, PRO_ANUAL)')
        parser.add_argument('--addon', action='store_true', help='Simular compra de add-ons')
        parser.add_argument('--tecnicos', type=int, default=0)
        parser.add_argument('--admins', type=int, default=0)
        parser.add_argument('--gerentes', type=int, default=0)
        parser.add_argument('--bloques-equipos', type=int, default=0, dest='bloques_equipos')
        parser.add_argument('--bloques-storage', type=int, default=0, dest='bloques_storage')

    def handle(self, *args, **options):
        try:
            empresa = Empresa.objects.get(pk=options['empresa'])
        except Empresa.DoesNotExist:
            raise CommandError(f"No existe empresa con ID {options['empresa']}")

        self.stdout.write('=' * 65)
        self.stdout.write(f'SIMULACIÓN DE PAGO — Empresa: {empresa.nombre} (ID: {empresa.id})')
        self.stdout.write('=' * 65)

        # Estado antes
        self.stdout.write('\n[ANTES]')
        self.stdout.write(f'  Equipos:       {empresa.limite_equipos_empresa}')
        self.stdout.write(f'  Almacenamiento: {empresa.limite_almacenamiento_mb} MB')
        self.stdout.write(f'  Usuarios:      {empresa.limite_usuarios_empresa}')
        self.stdout.write(f'  Estado:        {empresa.get_estado_suscripcion_display()}')

        referencia = f"TEST-{empresa.id}-{uuid.uuid4().hex[:8].upper()}"

        if options['addon']:
            # ── Simular add-on ──────────────────────────────────────────────
            datos_addon = {
                'tecnicos': options['tecnicos'],
                'admins': options['admins'],
                'gerentes': options['gerentes'],
                'bloques_equipos': options['bloques_equipos'],
                'bloques_storage': options['bloques_storage'],
            }
            total = sum(datos_addon.values())
            if total == 0:
                raise CommandError('Debes especificar al menos un add-on (--tecnicos, --bloques-equipos, etc.)')

            self.stdout.write(f'\n[ADDON] {datos_addon}')

            transaccion = TransaccionPago.objects.create(
                empresa=empresa,
                referencia_pago=referencia,
                estado='pendiente',
                monto=0,
                moneda='COP',
                plan_seleccionado='ADDON',
                datos_addon=datos_addon,
                ip_cliente='127.0.0.1',
            )

            empresa.activar_addons(datos_addon)
            transaccion.estado = 'aprobado'
            transaccion.save(update_fields=['estado'])

            self.stdout.write(self.style.SUCCESS('\n[OK] Add-ons activados.'))

        else:
            # ── Simular plan completo ───────────────────────────────────────
            plan_key = (options.get('plan') or '').upper()
            if not plan_key:
                self.stdout.write('\nPlanes disponibles:')
                for k, p in PLANES.items():
                    self.stdout.write(f'  {k:25} → {p["nombre"]:30} ${p["precio_total"]:>10,} COP')
                raise CommandError('Especifica --plan con una de las claves anteriores.')

            if plan_key not in PLANES:
                raise CommandError(f'Plan "{plan_key}" no existe. Usa uno de: {list(PLANES.keys())}')

            plan = PLANES[plan_key]
            self.stdout.write(f'\n[PLAN] {plan["nombre"]} — ${plan["precio_total"]:,} COP')

            transaccion = TransaccionPago.objects.create(
                empresa=empresa,
                referencia_pago=referencia,
                estado='pendiente',
                monto=plan['precio_total'],
                moneda='COP',
                plan_seleccionado=plan_key,
                ip_cliente='127.0.0.1',
            )

            empresa.activar_plan_pagado(
                limite_equipos=plan['equipos'],
                limite_almacenamiento_mb=plan['almacenamiento_mb'],
                duracion_meses=plan['duracion_meses'],
            )
            transaccion.estado = 'aprobado'
            transaccion.save(update_fields=['estado'])

            self.stdout.write(self.style.SUCCESS('\n[OK] Plan activado.'))

        # Estado después
        empresa.refresh_from_db()
        self.stdout.write('\n[DESPUÉS]')
        self.stdout.write(f'  Equipos:       {empresa.limite_equipos_empresa}')
        self.stdout.write(f'  Almacenamiento: {empresa.limite_almacenamiento_mb} MB')
        self.stdout.write(f'  Usuarios:      {empresa.limite_usuarios_empresa}')
        self.stdout.write(f'  Estado:        {empresa.get_estado_suscripcion_display()}')
        self.stdout.write(f'  Referencia:    {referencia}')
        self.stdout.write('=' * 65)
