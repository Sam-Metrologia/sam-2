# core/management/commands/create_realistic_test_data.py
# Comando para generar datos de prueba realistas para testing

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from core.models import (
    Empresa, Equipo, Calibracion, Mantenimiento, Comprobacion,
    Procedimiento, Proveedor
)
import random
from datetime import datetime, timedelta
import logging

User = get_user_model()
logger = logging.getLogger('core')

class Command(BaseCommand):
    help = 'Crea datos de prueba realistas: 5 empresas con 50 equipos cada una'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Limpiar datos existentes antes de crear nuevos'
        )
        parser.add_argument(
            '--empresas',
            type=int,
            default=5,
            help='Número de empresas a crear (default: 5)'
        )
        parser.add_argument(
            '--equipos-por-empresa',
            type=int,
            default=50,
            help='Equipos por empresa (default: 50)'
        )

    def handle(self, *args, **options):
        clear_existing = options['clear_existing']
        num_empresas = options['empresas']
        equipos_por_empresa = options['equipos_por_empresa']

        self.stdout.write(self.style.SUCCESS(f'[INICIO] Creando {num_empresas} empresas con {equipos_por_empresa} equipos cada una'))

        if clear_existing:
            self.clear_existing_data()

        # Crear datos de prueba
        for i in range(num_empresas):
            empresa = self.create_empresa(i + 1)
            self.create_empresa_data(empresa, equipos_por_empresa, i + 1)

        self.stdout.write(
            self.style.SUCCESS(f'[COMPLETADO] Datos de prueba creados exitosamente')
        )

    def clear_existing_data(self):
        """Limpia datos existentes manteniendo superusuarios."""
        self.stdout.write(self.style.WARNING('[LIMPIEZA] Eliminando datos existentes...'))

        # Eliminar empresas (cascada eliminará todo lo relacionado)
        Empresa.objects.all().delete()

        # Eliminar usuarios no superusuarios
        User.objects.filter(is_superuser=False).delete()

        self.stdout.write('[LIMPIEZA] Datos eliminados')

    def create_empresa(self, num):
        """Crea una empresa con datos realistas."""
        empresas_data = [
            {
                'nombre': 'Certicapital',
                'nit': '900123456-1',
                'direccion': 'Calle 72 #15-45, Bogotá',
                'telefono': '+57 1 3456789',
                'email': 'info@certicapital.co',
                'limite_equipos_empresa': 100,
                'limite_almacenamiento_mb': 5000,
                'duracion_suscripcion_meses': 12
            },
            {
                'nombre': 'MetroTech Solutions',
                'nit': '800234567-2',
                'direccion': 'Carrera 50 #25-30, Medellín',
                'telefono': '+57 4 2345678',
                'email': 'ventas@metrotech.co',
                'limite_equipos_empresa': 75,
                'limite_almacenamiento_mb': 3000,
                'duracion_suscripcion_meses': 24
            },
            {
                'nombre': 'Instrumentos Precisión Ltda',
                'nit': '900345678-3',
                'direccion': 'Avenida 19 #120-50, Cali',
                'telefono': '+57 2 3456789',
                'email': 'laboratorio@precision.co',
                'limite_equipos_empresa': 60,
                'limite_almacenamiento_mb': 2500,
                'duracion_suscripcion_meses': 18
            },
            {
                'nombre': 'Laboratorios Calidad SAS',
                'nit': '800456789-4',
                'direccion': 'Calle 45 #28-15, Bucaramanga',
                'telefono': '+57 7 4567890',
                'email': 'control@calidad.co',
                'limite_equipos_empresa': 80,
                'limite_almacenamiento_mb': 4000,
                'duracion_suscripcion_meses': 36
            },
            {
                'nombre': 'Control Metrológico Andino',
                'nit': '900567890-5',
                'direccion': 'Carrera 68 #80-32, Barranquilla',
                'telefono': '+57 5 5678901',
                'email': 'sistemas@andino.co',
                'limite_equipos_empresa': 90,
                'limite_almacenamiento_mb': 3500,
                'duracion_suscripcion_meses': 12
            }
        ]

        # Usar datos predefinidos o generar nuevos si hay más empresas
        if num <= len(empresas_data):
            data = empresas_data[num - 1]
        else:
            data = {
                'nombre': f'Empresa Metrológica {num}',
                'nit': f'90{num:07d}-{num}',
                'direccion': f'Dirección {num}, Ciudad {num}',
                'telefono': f'+57 {num} {num*1000000:07d}',
                'email': f'empresa{num}@test.co',
                'limite_equipos_empresa': 50,
                'limite_almacenamiento_mb': 2000,
                'duracion_suscripcion_meses': 12
            }

        # Campos adicionales estándar
        data.update({
            'fecha_inicio_plan': timezone.now().date() - timedelta(days=random.randint(30, 365)),
            'estado_suscripcion': 'activa',
            'acceso_manual_activo': True
        })

        empresa = Empresa.objects.create(**data)
        self.stdout.write(f'[EMPRESA] {empresa.nombre}')
        return empresa

    def create_empresa_data(self, empresa, num_equipos, empresa_num):
        """Crea todos los datos relacionados con una empresa."""
        # Crear usuario administrador para la empresa
        username = f'admin_{empresa.nombre.lower().replace(" ", "_").replace(".", "")}'[:30]
        user = User.objects.create_user(
            username=username,
            email=empresa.email,
            password='admin123',
            first_name='Admin',
            last_name=empresa.nombre.split()[0],
            empresa=empresa,
            is_staff=False,
            can_access_dashboard_decisiones=True
        )
        self.stdout.write(f'   [USUARIO] {user.username} (contraseña: admin123)')

        # Crear proveedores
        proveedores = self.create_proveedores(empresa)

        # Crear procedimientos
        procedimientos = self.create_procedimientos(empresa)

        # Crear equipos
        equipos = self.create_equipos(empresa, num_equipos, empresa_num)

        # Crear calibraciones, mantenimientos y comprobaciones
        self.create_calibraciones(equipos, procedimientos)
        self.create_mantenimientos(equipos)
        self.create_comprobaciones(equipos)

    def create_proveedores(self, empresa):
        """Crea proveedores para la empresa."""
        proveedores_data = [
            {
                'nombre_empresa': 'FLUKE Corporation',
                'tipo_servicio': 'Calibración',
                'nombre_contacto': 'John Smith',
                'numero_contacto': '+1 425-347-6100',
                'correo_electronico': 'info@fluke.com',
                'pagina_web': 'https://www.fluke.com',
                'alcance': 'Instrumentos de medición eléctrica',
                'servicio_prestado': 'Calibración de multímetros y equipos eléctricos'
            },
            {
                'nombre_empresa': 'Agilent Technologies',
                'tipo_servicio': 'Calibración',
                'nombre_contacto': 'Maria Garcia',
                'numero_contacto': '+1 707-577-2663',
                'correo_electronico': 'info@agilent.com',
                'pagina_web': 'https://www.agilent.com',
                'alcance': 'Equipos de alta frecuencia',
                'servicio_prestado': 'Calibración de osciloscopios y analizadores'
            },
            {
                'nombre_empresa': 'Tektronix Inc',
                'tipo_servicio': 'Mantenimiento',
                'nombre_contacto': 'Carlos Rodriguez',
                'numero_contacto': '+1 503-627-7111',
                'correo_electronico': 'support@tek.com',
                'pagina_web': 'https://www.tek.com',
                'alcance': 'Equipos electrónicos',
                'servicio_prestado': 'Mantenimiento preventivo y correctivo'
            },
            {
                'nombre_empresa': 'Keysight Technologies',
                'tipo_servicio': 'Calibración',
                'nombre_contacto': 'Ana Lopez',
                'numero_contacto': '+1 800-829-4444',
                'correo_electronico': 'contact@keysight.com',
                'pagina_web': 'https://www.keysight.com',
                'alcance': 'Instrumentos de precisión',
                'servicio_prestado': 'Calibración de equipos de medición RF'
            }
        ]

        proveedores = []
        for data in proveedores_data:
            data['empresa'] = empresa
            proveedor = Proveedor.objects.create(**data)
            proveedores.append(proveedor)

        self.stdout.write(f'   [PROVEEDORES] {len(proveedores)} proveedores')
        return proveedores

    def create_procedimientos(self, empresa):
        """Crea procedimientos de calibración."""
        procedimientos_data = [
            {'codigo': 'PC-001', 'descripcion': 'Calibración de Multímetros Digitales'},
            {'codigo': 'PC-002', 'descripcion': 'Calibración de Termómetros Digitales'},
            {'codigo': 'PC-003', 'descripcion': 'Calibración de Osciloscopios'},
            {'codigo': 'PC-004', 'descripcion': 'Calibración de Fuentes de Voltaje'},
            {'codigo': 'PC-005', 'descripcion': 'Calibración de Balanzas Electrónicas'},
            {'codigo': 'PC-006', 'descripcion': 'Calibración de Manómetros Digitales'},
            {'codigo': 'PC-007', 'descripcion': 'Calibración de Cronómetros de Precisión'},
            {'codigo': 'PC-008', 'descripcion': 'Calibración de Medidores de Presión'},
            {'codigo': 'PC-009', 'descripcion': 'Calibración de Generadores de Función'},
            {'codigo': 'PC-010', 'descripcion': 'Calibración de Analizadores de Espectro'}
        ]

        procedimientos = []
        for data in procedimientos_data:
            data['empresa'] = empresa
            procedimiento = Procedimiento.objects.create(**data)
            procedimientos.append(procedimiento)

        self.stdout.write(f'   [PROCEDIMIENTOS] {len(procedimientos)} procedimientos')
        return procedimientos

    def create_equipos(self, empresa, num_equipos, empresa_num):
        """Crea equipos para la empresa."""
        tipos_equipos = [
            ('Multímetro Digital', 'FLUKE', ['287', '289', '179', '175', '87V', '77IV', '115']),
            ('Osciloscopio Digital', 'Tektronix', ['TDS2024C', 'MSO3014', 'DPO4054B', 'MSO2024B']),
            ('Fuente de Voltaje', 'Agilent', ['E3631A', 'E3632A', 'E3633A', 'E3634A']),
            ('Termómetro Digital', 'OMEGA', ['HH374', 'HH378', 'HH506RA', 'HH802A']),
            ('Balanza Electrónica', 'Ohaus', ['CP323', 'CP423', 'CP523', 'CP623']),
            ('Manómetro Digital', 'FLUKE', ['718Ex', '719Pro', '700G', '726']),
            ('Cronómetro Digital', 'OMEGA', ['HH502', 'HH506', 'HH512', 'HH520']),
            ('Medidor de Presión', 'Keysight', ['34470A', '34461A', 'U1273A', '34465A']),
            ('Generador de Funciones', 'Tektronix', ['AFG3022C', 'AFG3102C', 'AFG3252']),
            ('Analizador de Espectro', 'Keysight', ['N9020A', 'E4407B', 'N9010A']),
            ('Calibrador Multifunción', 'FLUKE', ['5522A', '5502A', '5720A']),
            ('Frecuencímetro', 'Agilent', ['53131A', '53132A', '53181A'])
        ]

        ubicaciones = [
            'Laboratorio Principal', 'Laboratorio Secundario', 'Área de Calibración',
            'Sala de Mediciones', 'Laboratorio de Temperatura', 'Laboratorio de Presión',
            'Área de Mantenimiento', 'Almacén Técnico', 'Oficina de Metrología'
        ]

        equipos = []
        for i in range(num_equipos):
            tipo, marca, modelos = random.choice(tipos_equipos)
            modelo = random.choice(modelos)

            # Generar fechas realistas
            fecha_adquisicion = timezone.now() - timedelta(days=random.randint(30, 1825))

            # Programar fechas futuras próximas (algunas ya vencidas para testing)
            dias_hasta_calibracion = random.randint(-30, 365)  # Algunas vencidas
            dias_hasta_mantenimiento = random.randint(-15, 180)
            dias_hasta_comprobacion = random.randint(-10, 90)

            equipo = Equipo.objects.create(
                empresa=empresa,
                codigo_interno=f'{empresa_num:02d}-{i+1:03d}',
                nombre=f'{tipo} {marca} {modelo}',
                tipo_equipo=tipo,
                marca=marca,
                modelo=modelo,
                numero_serie=f'SN{empresa_num:02d}{i+1:06d}',
                fecha_adquisicion=fecha_adquisicion,
                estado=random.choices(
                    ['Activo', 'En Mantenimiento', 'En Calibración', 'En Comprobación'],
                    weights=[85, 5, 5, 5]
                )[0],
                ubicacion=random.choice(ubicaciones),
                descripcion=f'{tipo} de alta precisión marca {marca}, modelo {modelo}. Utilizado para mediciones críticas en el laboratorio de metrología.',
                observaciones=random.choice([
                    'Equipo en condiciones óptimas de funcionamiento.',
                    'Requiere calibración periódica cada 12 meses.',
                    'Mantenimiento preventivo cada 6 meses.',
                    'Equipo crítico para el proceso de medición.',
                    'Verificar condiciones ambientales de operación.'
                ]),
                responsable=random.choice([
                    'Técnico Metrología', 'Ing. Calibración', 'Jefe Laboratorio',
                    'Especialista Medición', 'Coordinador Técnico'
                ]),
                rango_medida=random.choice([
                    '0-100V DC', '0-1000V AC', '0-10A DC', '1Hz-1MHz',
                    '0-100°C', '0-10 Bar', '0-50kg', '10-1000MHz'
                ]),
                resolucion=random.choice([
                    '0.1V', '0.01A', '0.1°C', '1Hz', '0.1g', '0.01Bar', '1mV'
                ]),
                error_maximo_permisible=random.choice([
                    '±0.1%', '±0.5%', '±1%', '±0.05%', '±2%', '±0.2%'
                ]),
                proxima_calibracion=timezone.now() + timedelta(days=dias_hasta_calibracion) if dias_hasta_calibracion > 0 else None,
                proximo_mantenimiento=timezone.now() + timedelta(days=dias_hasta_mantenimiento) if dias_hasta_mantenimiento > 0 else None,
                proxima_comprobacion=timezone.now() + timedelta(days=dias_hasta_comprobacion) if dias_hasta_comprobacion > 0 else None,
            )
            equipos.append(equipo)

        self.stdout.write(f'   [EQUIPOS] {len(equipos)} equipos')
        return equipos

    def create_calibraciones(self, equipos, procedimientos):
        """Crea calibraciones para los equipos."""
        total_calibraciones = 0

        for equipo in equipos:
            # Entre 2 y 5 calibraciones por equipo (historial)
            num_calibraciones = random.randint(2, 5)

            for i in range(num_calibraciones):
                dias_atras = random.randint(30 + (i * 120), 365 + (i * 120))
                fecha_calibracion = timezone.now() - timedelta(days=dias_atras)

                calibracion = Calibracion.objects.create(
                    equipo=equipo,
                    fecha_calibracion=fecha_calibracion,
                    procedimiento=random.choice(procedimientos),
                    resultado=random.choices(
                        ['Conforme', 'No Conforme', 'Conforme con observaciones'],
                        weights=[80, 5, 15]
                    )[0],
                    observaciones=random.choice([
                        'Calibración exitosa, equipo dentro de especificaciones técnicas.',
                        'Ajustes menores realizados durante el proceso de calibración.',
                        'Equipo calibrado conforme a procedimientos estándar ISO 17025.',
                        'Se realizaron verificaciones adicionales por precisión requerida.',
                        'Calibración completada sin inconvenientes. Equipo apto para uso.',
                        'Verificación de incertidumbre de medición dentro de límites.',
                        'Certificado de calibración emitido conforme a normas.',
                        'Equipo requiere nuevo ajuste en próxima calibración.',
                        'Trazabilidad metrológica verificada y confirmada.',
                        'Condiciones ambientales controladas durante calibración.'
                    ])
                )
                total_calibraciones += 1

        self.stdout.write(f'   [CALIBRACIONES] {total_calibraciones} calibraciones')

    def create_mantenimientos(self, equipos):
        """Crea mantenimientos para los equipos."""
        total_mantenimientos = 0

        for equipo in equipos:
            # Entre 1 y 4 mantenimientos por equipo
            num_mantenimientos = random.randint(1, 4)

            for i in range(num_mantenimientos):
                dias_atras = random.randint(15 + (i * 90), 300 + (i * 90))
                fecha_mantenimiento = timezone.now() - timedelta(days=dias_atras)

                mantenimiento = Mantenimiento.objects.create(
                    equipo=equipo,
                    fecha_mantenimiento=fecha_mantenimiento,
                    tipo_mantenimiento=random.choices(
                        ['Preventivo', 'Correctivo', 'Predictivo'],
                        weights=[70, 20, 10]
                    )[0],
                    descripcion=random.choice([
                        'Limpieza general del equipo y verificación de funcionamiento básico.',
                        'Cambio de componentes desgastados y verificación de especificaciones.',
                        'Lubricación de partes móviles y ajuste de mecanismos internos.',
                        'Verificación de conexiones eléctricas y estado de cables.',
                        'Actualización de firmware del equipo a versión más reciente.',
                        'Calibración de parámetros internos y verificación de rangos.',
                        'Inspección visual completa y funcional de todos los controles.',
                        'Reemplazo de filtros y componentes de protección.',
                        'Verificación de seguridad eléctrica y aislamiento.',
                        'Limpieza de contactos y verificación de resistencias internas.'
                    ]),
                    observaciones=random.choice([
                        'Mantenimiento completado satisfactoriamente según cronograma.',
                        'Equipo en excelentes condiciones después del mantenimiento.',
                        'Se detectaron desgastes mínimos, no requieren intervención.',
                        'Mantenimiento preventivo realizado conforme a manual técnico.',
                        'Todas las verificaciones resultaron dentro de parámetros normales.',
                        'Equipo listo para continuar operación normal.',
                        'Se recomienda próximo mantenimiento en 6 meses.',
                        'Documentación técnica actualizada en registros.'
                    ])
                )
                total_mantenimientos += 1

        self.stdout.write(f'   [MANTENIMIENTOS] {total_mantenimientos} mantenimientos')

    def create_comprobaciones(self, equipos):
        """Crea comprobaciones para los equipos."""
        total_comprobaciones = 0

        for equipo in equipos:
            # Entre 1 y 3 comprobaciones por equipo
            num_comprobaciones = random.randint(1, 3)

            for i in range(num_comprobaciones):
                dias_atras = random.randint(10 + (i * 60), 180 + (i * 60))
                fecha_comprobacion = timezone.now() - timedelta(days=dias_atras)

                comprobacion = Comprobacion.objects.create(
                    equipo=equipo,
                    fecha_comprobacion=fecha_comprobacion,
                    resultado=random.choices(
                        ['Satisfactorio', 'No Satisfactorio', 'Satisfactorio con observaciones'],
                        weights=[85, 5, 10]
                    )[0],
                    observaciones=random.choice([
                        'Comprobación intermedia exitosa, equipo funcionando correctamente.',
                        'Verificación de funcionamiento y precisión satisfactoria.',
                        'Comprobación de deriva y estabilidad dentro de límites.',
                        'Control de calidad intermedio aprobado sin observaciones.',
                        'Verificación técnica completada conforme a procedimientos.',
                        'Equipo mantiene características metrológicas adecuadas.',
                        'Comprobación de repetibilidad y reproducibilidad exitosa.',
                        'Estado general del equipo satisfactorio para uso continuo.',
                        'Verificación de rangos de medición dentro de especificaciones.',
                        'Comprobación de funcionamiento en condiciones normales de uso.'
                    ])
                )
                total_comprobaciones += 1

        self.stdout.write(f'   [COMPROBACIONES] {total_comprobaciones} comprobaciones')
        self.stdout.write('')