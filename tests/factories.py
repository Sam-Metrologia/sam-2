"""
Factory Boy factories for generating test data.

These factories create realistic test data for models, making tests
more readable and maintainable.

Usage:
    # Create a simple empresa
    empresa = EmpresaFactory()

    # Create with custom attributes
    empresa = EmpresaFactory(nombre="Mi Empresa")

    # Create multiple instances
    empresas = EmpresaFactory.create_batch(5)

    # Build without saving to database
    empresa = EmpresaFactory.build()
"""
import factory
from factory.django import DjangoModelFactory
from faker import Faker
from django.utils import timezone
from datetime import timedelta
import random

# Use Colombian locale for realistic data
fake = Faker('es_CO')


# ============================================================================
# EMPRESA FACTORY
# ============================================================================

class EmpresaFactory(DjangoModelFactory):
    """Factory for creating Empresa test instances."""

    class Meta:
        model = 'core.Empresa'

    nombre = factory.Sequence(lambda n: f'Empresa Test {n}')
    nit = factory.Sequence(lambda n: f'{900000000 + n}-{n % 10}')
    email = factory.LazyAttribute(lambda obj: f'contacto@{obj.nombre.lower().replace(" ", "")}.com')
    telefono = factory.LazyFunction(lambda: fake.phone_number()[:20])
    direccion = factory.LazyFunction(lambda: fake.address()[:200])

    # Plan settings (using actual field names)
    limite_equipos_empresa = factory.LazyFunction(lambda: random.choice([10, 25, 50, 100, 500]))
    es_periodo_prueba = True
    duracion_prueba_dias = 30

    # Logo can be added in tests if needed
    # logo_empresa will be None by default

    @factory.post_generation
    def with_logo(obj, create, extracted, **kwargs):
        """
        Add logo to empresa if requested.

        Usage:
            empresa = EmpresaFactory(with_logo=True)
        """
        if extracted:
            from django.core.files.uploadedfile import SimpleUploadedFile
            image_content = (
                b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
                b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01'
                b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
            )
            obj.logo_empresa = SimpleUploadedFile(
                name='logo.png',
                content=image_content,
                content_type='image/png'
            )
            if create:
                obj.save()


# ============================================================================
# USER FACTORY
# ============================================================================

class UserFactory(DjangoModelFactory):
    """Factory for creating CustomUser test instances."""

    class Meta:
        model = 'core.CustomUser'
        django_get_or_create = ('username',)

    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@example.com')
    first_name = factory.LazyFunction(lambda: fake.first_name())
    last_name = factory.LazyFunction(lambda: fake.last_name())

    # Company relationship
    empresa = factory.SubFactory(EmpresaFactory)

    # Status
    is_active = True
    is_staff = False
    is_superuser = False

    # Role
    rol_usuario = factory.LazyFunction(lambda: random.choice([
        'Administrador', 'Técnico', 'Gerente', 'Coordinador', 'Analista'
    ]))
    is_management_user = False
    can_access_dashboard_decisiones = False

    @factory.post_generation
    def password(obj, create, extracted, **kwargs):
        """
        Set password for the user.
        Default password is 'testpass123'

        Usage:
            user = UserFactory()  # password is 'testpass123'
            user = UserFactory(password='custom_pass')
        """
        password = extracted if extracted else 'testpass123'
        obj.set_password(password)
        if create:
            obj.save()

    @factory.post_generation
    def groups(obj, create, extracted, **kwargs):
        """
        Add user to groups.

        Usage:
            user = UserFactory(groups=['Admin', 'Managers'])
        """
        if not create:
            return

        if extracted:
            from django.contrib.auth.models import Group
            for group_name in extracted:
                group, _ = Group.objects.get_or_create(name=group_name)
                obj.groups.add(group)


class AdminUserFactory(UserFactory):
    """Factory for creating superuser instances."""

    is_staff = True
    is_superuser = True
    username = factory.Sequence(lambda n: f'admin{n}')


# ============================================================================
# EQUIPO FACTORY
# ============================================================================

class EquipoFactory(DjangoModelFactory):
    """Factory for creating Equipo test instances."""

    class Meta:
        model = 'core.Equipo'

    codigo_interno = factory.Sequence(lambda n: f'EQ-{n:05d}')
    nombre = factory.LazyFunction(lambda: f'{fake.word().title()} {random.choice(["Digital", "Analógico", "Electrónico", "Mecánico"])}')

    # Equipment details (using ACTUAL field names)
    marca = factory.LazyFunction(lambda: random.choice([
        'Mettler Toledo', 'Sartorius', 'Fluke', 'Testo', 'Mitutoyo',
        'Ohaus', 'AND', 'Kern', 'Adam', 'Radwag'
    ]))
    modelo = factory.LazyFunction(lambda: fake.bothify('??-####'))
    numero_serie = factory.LazyFunction(lambda: fake.bothify('SN-########'))

    # Classification
    tipo_equipo = factory.LazyFunction(lambda: random.choice([
        'Balanza', 'Termómetro', 'Higrómetro', 'Manómetro', 'Multímetro',
        'Calibrador', 'Medidor', 'Analizador', 'Sensor', 'Detector'
    ]))

    # Location
    ubicacion = factory.LazyFunction(lambda: random.choice([
        'Laboratorio Principal', 'Área de Producción', 'Bodega',
        'Sala de Calidad', 'Planta 1', 'Planta 2', 'Almacén'
    ]))

    responsable = factory.LazyFunction(lambda: fake.name())

    # Status
    estado = factory.LazyFunction(lambda: random.choice([
        'operativo', 'en_mantenimiento', 'en_reparacion', 'fuera_de_servicio', 'en_calibracion'
    ]))

    # Company relationship
    empresa = factory.SubFactory(EmpresaFactory)

    # Dates
    fecha_adquisicion = factory.LazyFunction(
        lambda: timezone.now().date() - timedelta(days=random.randint(30, 1825))
    )

    # Technical specs (optional)
    rango_medida = factory.LazyFunction(lambda: f'0-{random.choice([100, 500, 1000])} {random.choice(["g", "°C", "Pa", "V"])}')
    resolucion = factory.LazyFunction(lambda: f'{random.choice([0.001, 0.01, 0.1, 1])} {random.choice(["g", "°C", "Pa", "V"])}')

    @factory.post_generation
    def with_image(obj, create, extracted, **kwargs):
        """Add image to equipment if requested."""
        if extracted:
            from django.core.files.uploadedfile import SimpleUploadedFile
            image_content = (
                b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
                b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01'
                b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
            )
            obj.imagen_equipo = SimpleUploadedFile(
                name='equipo.png',
                content=image_content,
                content_type='image/png'
            )
            if create:
                obj.save()


# ============================================================================
# ACTIVIDAD FACTORIES
# ============================================================================

class CalibracionFactory(DjangoModelFactory):
    """Factory for creating Calibracion instances."""

    class Meta:
        model = 'core.Calibracion'

    equipo = factory.SubFactory(EquipoFactory)

    fecha_calibracion = factory.LazyFunction(
        lambda: timezone.now().date() - timedelta(days=random.randint(90, 300))
    )

    # Proveedor as string (nombre_proveedor field)
    nombre_proveedor = factory.LazyFunction(lambda: fake.company())

    resultado = factory.LazyFunction(lambda: random.choice([
        'Aprobado', 'No Aprobado'  # Fixed: correct choice values from model
    ]))

    numero_certificado = factory.LazyFunction(lambda: fake.bothify('CERT-####-????'))
    costo_calibracion = factory.LazyFunction(lambda: random.randint(200000, 2000000))
    tiempo_empleado_horas = factory.LazyFunction(lambda: random.randint(2, 12))


class MantenimientoFactory(DjangoModelFactory):
    """Factory for creating Mantenimiento instances."""

    class Meta:
        model = 'core.Mantenimiento'

    equipo = factory.SubFactory(EquipoFactory)

    fecha_mantenimiento = factory.LazyFunction(
        lambda: timezone.now().date() - timedelta(days=random.randint(30, 180))
    )

    tipo_mantenimiento = factory.LazyFunction(lambda: random.choice([
        'Preventivo', 'Correctivo', 'Predictivo'
    ]))

    # Proveedor can be SubFactory or nombre_proveedor as string
    nombre_proveedor = factory.LazyFunction(lambda: fake.company())

    responsable = factory.LazyFunction(lambda: fake.name())

    descripcion = factory.LazyFunction(
        lambda: f'Mantenimiento preventivo - {fake.sentence()}'
    )

    costo = factory.LazyFunction(lambda: random.randint(100000, 1000000))
    tiempo_empleado_horas = factory.LazyFunction(lambda: random.randint(1, 8))


class ComprobacionFactory(DjangoModelFactory):
    """Factory for creating Comprobacion instances."""

    class Meta:
        model = 'core.Comprobacion'

    equipo = factory.SubFactory(EquipoFactory)

    fecha_comprobacion = factory.LazyFunction(
        lambda: timezone.now().date() - timedelta(days=random.randint(15, 90))
    )

    # Proveedor as string (nombre_proveedor field)
    nombre_proveedor = factory.LazyFunction(lambda: fake.company())

    responsable = factory.LazyFunction(lambda: fake.name())

    resultado = factory.LazyFunction(lambda: random.choice([
        'Aprobado', 'No Aprobado'  # Fixed: correct choice values from model
    ]))

    observaciones = 'Comprobación intermedia'
    costo_comprobacion = factory.LazyFunction(lambda: random.randint(50000, 500000))
    tiempo_empleado_horas = factory.LazyFunction(lambda: random.randint(1, 4))


# ============================================================================
# NOTIFICACION FACTORIES
# ============================================================================

# NOTE: Temporarily commented out - model names need verification
# Uncomment and adjust when implementing notification tests

# class NotificacionZipFactory(DjangoModelFactory):
#     """Factory for creating NotificacionZip instances."""
#
#     class Meta:
#         model = 'core.NotificacionZip'
#
#     # Add fields based on actual model

# class NotificacionVencimientoFactory(DjangoModelFactory):
#     """Factory for creating NotificacionVencimiento instances."""
#
#     class Meta:
#         model = 'core.NotificacionVencimiento'
#
#     # Add fields based on actual model


# ============================================================================
# MAINTENANCE TASK FACTORY
# ============================================================================

class MaintenanceTaskFactory(DjangoModelFactory):
    """Factory for creating MaintenanceTask instances."""

    class Meta:
        model = 'core.MaintenanceTask'

    task_type = factory.LazyFunction(lambda: random.choice([
        'backup_db', 'clear_cache', 'cleanup_files', 'check_system',
        'optimize_db', 'collect_static', 'migrate_db'
    ]))

    status = 'pending'
    created_by = factory.SubFactory(AdminUserFactory)

    created_at = factory.LazyFunction(
        lambda: timezone.now() - timedelta(minutes=random.randint(1, 1440))
    )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_empresa_with_users(num_users=3):
    """
    Create an empresa with multiple users.

    Usage:
        empresa, users = create_empresa_with_users(5)
    """
    empresa = EmpresaFactory()
    users = [UserFactory(empresa=empresa) for _ in range(num_users)]
    return empresa, users


def create_empresa_with_equipos(num_equipos=5, with_activities=True):
    """
    Create an empresa with multiple equipos and optional activities.

    Usage:
        empresa, equipos = create_empresa_with_equipos(10, with_activities=True)
    """
    empresa = EmpresaFactory()
    equipos = [EquipoFactory(empresa=empresa) for _ in range(num_equipos)]

    if with_activities:
        for equipo in equipos:
            # Add 1-3 activities per equipment
            num_activities = random.randint(1, 3)
            for _ in range(num_activities):
                activity_type = random.choice([
                    MantenimientoFactory,
                    CalibracionFactory,
                    ComprobacionFactory
                ])
                activity_type(equipo=equipo)

    return empresa, equipos


def create_full_test_scenario():
    """
    Create a complete test scenario with multiple companies, users, and equipment.

    Returns:
        dict with 'empresas', 'users', 'equipos', 'actividades'

    Usage:
        scenario = create_full_test_scenario()
        empresa1 = scenario['empresas'][0]
        user1 = scenario['users'][0]
    """
    # Create 3 companies
    empresas = [EmpresaFactory() for _ in range(3)]

    # Create users for each company
    users = []
    for empresa in empresas:
        company_users = [UserFactory(empresa=empresa) for _ in range(2)]
        users.extend(company_users)

    # Create equipment for each company
    equipos = []
    actividades = []
    for empresa in empresas:
        for _ in range(5):
            equipo = EquipoFactory(empresa=empresa)
            equipos.append(equipo)

            # Add activities
            actividad = MantenimientoFactory(equipo=equipo)
            actividades.append(actividad)

    return {
        'empresas': empresas,
        'users': users,
        'equipos': equipos,
        'actividades': actividades
    }
