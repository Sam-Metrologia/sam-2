# core/management/commands/restaurar_empresa_demo.py
# Restaura la empresa SAM METROLOGIA SAS (demo) con sus equipos y usuarios.
# Uso: python manage.py restaurar_empresa_demo

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date
from core.models import Empresa, CustomUser, Equipo


EQUIPOS_DATA = [
    # (codigo, nombre, marca, modelo, serie, frec_cal_meses, proxima_cal, observaciones)
    ('GP-001', 'Calibrador pie de rey (digital)', 'Stanley', 'N.R', '2517', 12, '2026-07-30', 'V1.0'),
    ('GP-002', 'Calibrador pie de rey (digital)', 'Stanley', 'N.R', '2518', 12, '2026-07-30', ''),
    ('GP-003', 'Dinamometro', 'DILLON', 'ED JUNIOR', 'DEDC2502128', 12, '2026-06-09', ''),
    ('GP-004', 'Luxometro', 'EXTECH INSTRUMENTS', 'SDL400', 'A.059000', 6, '2026-02-28', ''),
    ('GP-005', 'Medidor de espesores UT', 'DAKOTA ULTRASONICS', 'MX-3', '41912', 12, '2026-07-28', ''),
    ('GP-006', 'Cinta Metrica', 'STANLEY', '30-626', 'n.r', 12, '2026-08-01', ''),
    ('GP-007', 'Cinta Metrica', 'STANLEY', '30-626', 'N.r', 12, '2026-08-01', ''),
    ('GP-008', 'Gausimetro', 'MAGNAFLUX', 'N.R', 'JTS3056-F', 6, '2026-01-25', ''),
    ('GP-009', 'Manometro', 'Digital Pressure Gauge', 'N.R', '12359646', 12, '2027-01-22', ''),
    ('GP-010', 'Cinta Metrica', 'STARRETT', 'TS510-30N', '2525', 12, '2026-07-24', ''),
    ('GP-011', 'Yoque', 'PARKER', 'DA 400', '30428', 12, '2027-01-27', ''),
    ('GP-012', 'Pesa Individual', 'N.R', 'N.R', 'N.a', 6, '2026-02-08', ''),
    ('GP-013', 'Escuadra magnetica', 'FastCap', 'Magnetic Micro square', 'N.A', 12, '2026-08-13', ''),
    ('GP-014', 'Escuadra magnetica', 'FastCap', 'Magnetic Micro square', 'N.R.', 12, '2026-08-13', ''),
    ('GP-015', 'Escalerilla', 'Thickness Step wedge Calibration Block', '4 stps-0.250,0.500,0.750,1.000 inch', '64180', 12, '2026-08-26', ''),
    ('GP-016', 'Goniometro (magnetic)', 'ESYNIC', '5342S', '2588', 12, '2026-08-19', ''),
    ('GP-017', 'Termometro (infraroja)', 'UNI-T', 'UT300S', 'N.R..', 12, '2026-08-01', ''),
]

USUARIOS_DATA = [
    {
        'username': 'GerenciaSAM',
        'email': 'direccion@sammetrologia.com',
        'rol': 'GERENCIA',
        'first_name': 'Duvan',
        'last_name': 'Orozco',
        'password_hash': 'pbkdf2_sha256$1000000$DaCNIlWdmW946FYPtxFwU1$/jnrbmaX4OES9xwRmzJ+qLZZyBdMm9zxM38gSGTOMXk=',
    },
    {
        'username': 'TecnicoSAM',
        'email': 'soporte@sammetrologia.com',
        'rol': 'TECNICO',
        'first_name': 'Karen',
        'last_name': 'Arias',
        'password_hash': 'pbkdf2_sha256$1000000$tDMqbU4NhU1Qoqlkb6nFfF$YZH2q3BWg84A2v2WzEFnAEIzdS47/1F1vZxPn4qhYgI=',
    },
]


class Command(BaseCommand):
    help = 'Restaura la empresa SAM METROLOGIA SAS (demo) con sus equipos y usuarios.'

    def handle(self, *args, **options):
        self.stdout.write('=' * 65)
        self.stdout.write('RESTAURAR EMPRESA DEMO — SAM METROLOGIA SAS')
        self.stdout.write('=' * 65)

        NIT = '901853117-1'

        # Verificar si ya existe
        if Empresa.objects.filter(nit=NIT).exists():
            empresa = Empresa.objects.get(nit=NIT)
            self.stdout.write(self.style.WARNING(
                f'\n[!] La empresa ya existe (ID: {empresa.id}, deleted: {empresa.is_deleted})'
            ))
            if empresa.is_deleted:
                empresa.is_deleted = False
                empresa.deleted_at = None
                empresa.save(update_fields=['is_deleted', 'deleted_at'])
                self.stdout.write(self.style.SUCCESS('[OK] Restaurada del soft-delete'))
            else:
                self.stdout.write('[i] Ya está activa, no se modifica')
        else:
            empresa = Empresa.objects.create(
                nombre='SAM METROLOGIA SAS',
                nit=NIT,
                email='direccion@sammetrologia.com',
                telefono='+57 324 7990534',
                estado_suscripcion='Activo',
                es_periodo_prueba=False,
                fecha_inicio_plan=date(2025, 9, 1),
                duracion_suscripcion_meses=12,
                limite_equipos_empresa=150,
                limite_almacenamiento_mb=5120,
                limite_usuarios_empresa=5,
                acceso_manual_activo=True,
            )
            self.stdout.write(self.style.SUCCESS(f'\n[OK] Empresa creada (ID: {empresa.id})'))

        # Usuarios
        self.stdout.write('\n[Usuarios]')
        for ud in USUARIOS_DATA:
            if CustomUser.objects.filter(username=ud['username']).exists():
                self.stdout.write(f'  [ya existe] {ud["username"]}')
                continue
            u = CustomUser(
                username=ud['username'],
                email=ud['email'],
                first_name=ud['first_name'],
                last_name=ud['last_name'],
                rol_usuario=ud['rol'],
                empresa=empresa,
                is_active=True,
            )
            u.password = ud['password_hash']  # hash original, misma contraseña
            u.save()
            self.stdout.write(self.style.SUCCESS(f'  [creado] {u.username} ({u.rol_usuario})'))

        # Equipos
        self.stdout.write('\n[Equipos]')
        creados = 0
        existentes = 0
        for (codigo, nombre, marca, modelo, serie,
             frec_cal, proxima_cal, obs) in EQUIPOS_DATA:
            if Equipo.objects.filter(empresa=empresa, codigo_interno=codigo).exists():
                existentes += 1
                continue
            Equipo.objects.create(
                empresa=empresa,
                codigo_interno=codigo,
                nombre=nombre,
                marca=marca,
                modelo=modelo,
                numero_serie=serie,
                estado='Activo',
                frecuencia_calibracion_meses=frec_cal,
                proxima_calibracion=proxima_cal,
                observaciones=obs,
            )
            creados += 1

        self.stdout.write(self.style.SUCCESS(f'  {creados} equipos creados, {existentes} ya existían'))

        self.stdout.write(self.style.SUCCESS(
            f'\n[LISTO] Empresa ID:{empresa.id} restaurada con '
            f'{empresa.equipos.count()} equipos y '
            f'{empresa.usuarios_empresa.count()} usuarios.'
        ))
        self.stdout.write('=' * 65)
