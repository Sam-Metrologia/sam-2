"""
Comando para generar datos de prueba realistas para control de calidad.
Genera 5 empresas con 40 equipos cada una con fechas de actividades próximas.

Uso:
    python manage.py generar_datos_prueba

Para regenerar datos (elimina existentes):
    python manage.py generar_datos_prueba --recrear
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import Group
from core.models import Empresa, CustomUser, Equipo, Calibracion, Mantenimiento, Comprobacion
from datetime import datetime, timedelta, date
import random
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Genera datos de prueba realistas para control de calidad'

    def add_arguments(self, parser):
        parser.add_argument(
            '--recrear',
            action='store_true',
            help='Eliminar datos existentes y crear nuevos'
        )

    def handle(self, *args, **options):
        recrear = options['recrear']

        if recrear:
            self.stdout.write('[ADVERTENCIA] Se eliminarán todos los datos existentes')
            confirm = input('¿Continuar? (escriba "SI"): ')
            if confirm != 'SI':
                self.stdout.write('Operación cancelada')
                return

            # Limpiar datos existentes (excepto superusuarios y grupos)
            Equipo.objects.all().delete()
            CustomUser.objects.filter(is_superuser=False).delete()
            Empresa.objects.all().delete()
            self.stdout.write('[LIMPIADO] Datos existentes eliminados')

        self.stdout.write('[INICIO] Generando datos de prueba...')

        # Crear empresas
        empresas_data = [
            {
                'nombre': 'MetroTech Solutions',
                'nit': '900123456-1',
                'direccion': 'Calle 72 #10-34, Bogotá',
                'telefono': '+57-1-3456789',
                'email': 'info@metrotech.com.co'
            },
            {
                'nombre': 'Instrumentos Precisión Ltda',
                'nit': '800987654-3',
                'direccion': 'Carrera 15 #85-20, Medellín',
                'telefono': '+57-4-2345678',
                'email': 'contacto@precision.com.co'
            },
            {
                'nombre': 'Laboratorios Calidad S.A.S',
                'nit': '901234567-8',
                'direccion': 'Avenida 6N #23-50, Cali',
                'telefono': '+57-2-3214567',
                'email': 'info@labcalidad.com.co'
            },
            {
                'nombre': 'Control Metrológico Andino',
                'nit': '800654321-2',
                'direccion': 'Calle 19 #4-62, Bucaramanga',
                'telefono': '+57-7-6547890',
                'email': 'gerencia@metroandino.com.co'
            },
            {
                'nombre': 'Sistemas Medición Industrial',
                'nit': '900876543-0',
                'direccion': 'Zona Industrial Km 5, Barranquilla',
                'telefono': '+57-5-4567123',
                'email': 'ventas@simedind.com.co'
            }
        ]

        empresas_creadas = []
        for emp_data in empresas_data:
            empresa = Empresa.objects.create(**emp_data)
            # Activar período de prueba
            empresa.activar_periodo_prueba(duracion_dias=15)
            empresas_creadas.append(empresa)
            self.stdout.write(f'[EMPRESA] Creada: {empresa.nombre}')

        # Crear usuarios para cada empresa
        for i, empresa in enumerate(empresas_creadas):
            usuario = CustomUser.objects.create_user(
                username=f'usuario{i+1}',
                email=f'usuario{i+1}@{empresa.nombre.lower().replace(" ", "")}.com',
                password='admin123',
                first_name=f'Usuario{i+1}',
                last_name='Prueba',
                empresa=empresa
            )
            self.stdout.write(f'[USUARIO] Creado: {usuario.username} para {empresa.nombre}')

        # Tipos de equipos realistas
        tipos_equipos = [
            'Balanza analítica',
            'Calibrador de presión',
            'Multímetro digital',
            'Termómetro infrarrojo',
            'Manómetro digital',
            'Cronómetro',
            'Dinamómetro',
            'Microscopio',
            'pH-metro',
            'Espectrofotómetro'
        ]

        marcas = [
            'Fluke', 'Keysight', 'Mettler Toledo', 'Sartorius', 'Omega',
            'Testo', 'Druck', 'Yokogawa', 'Hanna Instruments', 'Cole-Parmer'
        ]

        # Generar 40 equipos por empresa
        for empresa in empresas_creadas:
            self.stdout.write(f'[EQUIPOS] Generando para {empresa.nombre}...')

            for i in range(40):
                tipo_equipo = random.choice(tipos_equipos)
                marca = random.choice(marcas)

                # Fechas de adquisición realistas (últimos 5 años)
                fecha_adquisicion = date.today() - timedelta(days=random.randint(30, 1825))

                equipo = Equipo.objects.create(
                    codigo_interno=f'{empresa.nombre[:3].upper()}-{i+1:03d}',
                    nombre=f'{tipo_equipo} {marca} {i+1}',
                    empresa=empresa,
                    tipo_equipo=tipo_equipo,
                    marca=marca,
                    modelo=f'M-{random.randint(1000, 9999)}',
                    numero_serie=f'SN{random.randint(100000, 999999)}',
                    ubicacion=random.choice(['Laboratorio A', 'Laboratorio B', 'Planta Principal', 'Oficina Técnica']),
                    responsable=f'Técnico {random.choice(["Juan", "María", "Carlos", "Ana", "Luis"])}',
                    estado=random.choice(['Activo'] * 8 + ['Inactivo'] * 1 + ['De Baja'] * 1),  # 80% activos
                    fecha_adquisicion=fecha_adquisicion,
                    rango_medida=f'0-{random.randint(100, 1000)} unidades',
                    resolucion=f'0.{random.randint(1, 5)} unidades',
                    error_maximo_permisible=random.uniform(0.1, 2.0),
                    observaciones='Equipo generado para pruebas de calidad',
                    frecuencia_calibracion_meses=random.choice([6, 12, 24]),
                    frecuencia_mantenimiento_meses=random.choice([3, 6, 12]),
                    frecuencia_comprobacion_meses=random.choice([1, 3, 6])
                )

                # Generar actividades con fechas próximas (30 días)
                self.generar_actividades_proximas(equipo)

            self.stdout.write(f'[EQUIPOS] {empresa.nombre}: 40 equipos creados')

        # Estadísticas finales
        total_empresas = Empresa.objects.count()
        total_usuarios = CustomUser.objects.filter(is_superuser=False).count()
        total_equipos = Equipo.objects.count()
        total_calibraciones = Calibracion.objects.count()
        total_mantenimientos = Mantenimiento.objects.count()
        total_comprobaciones = Comprobacion.objects.count()

        self.stdout.write('\n[ESTADÍSTICAS FINALES]')
        self.stdout.write(f'- Empresas creadas: {total_empresas}')
        self.stdout.write(f'- Usuarios creados: {total_usuarios}')
        self.stdout.write(f'- Equipos creados: {total_equipos}')
        self.stdout.write(f'- Calibraciones: {total_calibraciones}')
        self.stdout.write(f'- Mantenimientos: {total_mantenimientos}')
        self.stdout.write(f'- Comprobaciones: {total_comprobaciones}')

        self.stdout.write(
            self.style.SUCCESS('\n[EXITO] Datos de prueba generados exitosamente')
        )
        self.stdout.write('¡Sistema listo para pruebas de calidad!')

    def generar_actividades_proximas(self, equipo):
        """Genera actividades con fechas próximas (0-30 días) para testing."""
        hoy = date.today()

        # Calibración próxima (aleatoria en los próximos 30 días)
        if random.choice([True, False]):  # 50% probabilidad
            dias_hasta_calibracion = random.randint(0, 30)
            fecha_calibracion = hoy + timedelta(days=dias_hasta_calibracion)

            calibracion = Calibracion.objects.create(
                equipo=equipo,
                fecha_programada=fecha_calibracion,
                proveedor_externo='Laboratorio de Calibración Certificado',
                estado='Programada',
                observaciones=f'Calibración programada para {fecha_calibracion.strftime("%d/%m/%Y")}'
            )

            # Actualizar fecha en el equipo
            equipo.proxima_calibracion = fecha_calibracion
            equipo.save()

        # Mantenimiento próximo (aleatoria en los próximos 30 días)
        if random.choice([True, False]):  # 50% probabilidad
            dias_hasta_mantenimiento = random.randint(0, 30)
            fecha_mantenimiento = hoy + timedelta(days=dias_hasta_mantenimiento)

            mantenimiento = Mantenimiento.objects.create(
                equipo=equipo,
                fecha_programada=fecha_mantenimiento,
                tipo_mantenimiento=random.choice(['Preventivo', 'Correctivo']),
                descripcion_trabajo='Mantenimiento programado de rutina',
                tecnico_responsable='Técnico de Mantenimiento',
                estado='Programado'
            )

            # Actualizar fecha en el equipo
            equipo.proximo_mantenimiento = fecha_mantenimiento
            equipo.save()

        # Comprobación próxima (aleatoria en los próximos 30 días)
        if random.choice([True, False]):  # 50% probabilidad
            dias_hasta_comprobacion = random.randint(0, 30)
            fecha_comprobacion = hoy + timedelta(days=dias_hasta_comprobacion)

            comprobacion = Comprobacion.objects.create(
                equipo=equipo,
                fecha_programada=fecha_comprobacion,
                tipo_comprobacion='Comprobación intermedia',
                descripcion_procedimiento='Verificación de funcionamiento básico',
                tecnico_responsable='Técnico de Calidad',
                estado='Programada'
            )

            # Actualizar fecha en el equipo
            equipo.proxima_comprobacion = fecha_comprobacion
            equipo.save()