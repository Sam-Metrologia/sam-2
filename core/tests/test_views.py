# core/tests/test_views.py
# Tests básicos para vistas críticas

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from core.models import Empresa, Equipo

User = get_user_model()


class ViewsSecurityTest(TestCase):
    """Tests de seguridad para vistas principales."""

    def setUp(self):
        self.client = Client()
        self.empresa = Empresa.objects.create(
            nombre="Empresa Test Views",
            nit="333444555"
        )

        # Usuario normal
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            empresa=self.empresa
        )

        # Superusuario
        self.superuser = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass123"
        )

    def test_dashboard_requires_login(self):
        """Test que el dashboard requiere autenticación."""
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_dashboard_accessible_when_logged_in(self):
        """Test que el dashboard es accesible cuando está logueado."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_user_sees_only_own_company_data(self):
        """Test que usuario normal solo ve datos de su empresa."""
        # Crear otra empresa con equipos
        otra_empresa = Empresa.objects.create(
            nombre="Otra Empresa",
            nit="999888777"
        )

        # Equipos en empresa del usuario
        equipo_propio = Equipo.objects.create(
            codigo_interno="PROP001",
            nombre="Equipo Propio",
            empresa=self.empresa,
            tipo_equipo="Equipo de Medición"
        )

        # Equipo en otra empresa
        equipo_ajeno = Equipo.objects.create(
            codigo_interno="AJENO001",
            nombre="Equipo Ajeno",
            empresa=otra_empresa,
            tipo_equipo="Equipo de Medición"
        )

        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('core:home'))

        # Verificar que solo ve sus equipos
        equipos_en_respuesta = response.context['equipos']
        codigos_visibles = [eq.codigo_interno for eq in equipos_en_respuesta]

        self.assertIn('PROP001', codigos_visibles)
        self.assertNotIn('AJENO001', codigos_visibles)

    def test_superuser_permission_views(self):
        """Test que solo superusuarios pueden acceder a vistas administrativas."""
        # URL que requiere superusuario
        urls_admin = [
            'core:listar_usuarios',
            'core:listar_empresas',
        ]

        for url_name in urls_admin:
            # Test usuario normal no puede acceder
            self.client.login(username='testuser', password='testpass123')
            response = self.client.get(reverse(url_name))
            self.assertIn(response.status_code, [302, 403])  # Redirect o Forbidden

            # Test superusuario sí puede acceder
            self.client.login(username='admin', password='adminpass123')
            response = self.client.get(reverse(url_name))
            self.assertEqual(response.status_code, 200)


class EquipoCRUDTest(TestCase):
    """Tests para operaciones CRUD de equipos."""

    def setUp(self):
        self.client = Client()
        self.empresa = Empresa.objects.create(
            nombre="Empresa CRUD Test",
            nit="666777888"
        )

        self.user = User.objects.create_user(
            username="cruduser",
            email="crud@example.com",
            password="crudpass123",
            empresa=self.empresa
        )

        # Asignar permisos necesarios
        content_type = ContentType.objects.get_for_model(Equipo)
        permisos = [
            'add_equipo',
            'change_equipo',
            'view_equipo',
            'delete_equipo'
        ]

        for permiso_code in permisos:
            permiso = Permission.objects.get(
                codename=permiso_code,
                content_type=content_type
            )
            self.user.user_permissions.add(permiso)

    def test_crear_equipo_success(self):
        """Test creación exitosa de equipo."""
        self.client.login(username='cruduser', password='crudpass123')

        data = {
            'codigo_interno': 'CRUD001',
            'nombre': 'Equipo CRUD Test',
            'empresa': self.empresa.id,
            'tipo_equipo': 'Equipo de Medición',
            'marca': 'Test Brand',
            'modelo': 'Test Model',
            'estado': 'Activo'
        }

        response = self.client.post(reverse('core:añadir_equipo'), data)

        # Verificar redirección exitosa
        self.assertEqual(response.status_code, 302)

        # Verificar que el equipo se creó
        equipo = Equipo.objects.get(codigo_interno='CRUD001')
        self.assertEqual(equipo.nombre, 'Equipo CRUD Test')
        self.assertEqual(equipo.empresa, self.empresa)

    def test_editar_equipo_success(self):
        """Test edición exitosa de equipo."""
        # Crear equipo para editar
        equipo = Equipo.objects.create(
            codigo_interno='EDIT001',
            nombre='Equipo Original',
            empresa=self.empresa,
            tipo_equipo='Equipo de Medición'
        )

        self.client.login(username='cruduser', password='crudpass123')

        data = {
            'codigo_interno': 'EDIT001',
            'nombre': 'Equipo Editado',
            'empresa': self.empresa.id,
            'tipo_equipo': 'Equipo de Medición',
            'marca': 'Nueva Marca',
            'estado': 'Activo'
        }

        response = self.client.post(
            reverse('core:editar_equipo', kwargs={'pk': equipo.pk}),
            data
        )

        # Verificar redirección exitosa
        self.assertEqual(response.status_code, 302)

        # Verificar cambios
        equipo.refresh_from_db()
        self.assertEqual(equipo.nombre, 'Equipo Editado')
        self.assertEqual(equipo.marca, 'Nueva Marca')

    def test_delete_equipo_permission(self):
        """Test eliminación de equipo con permisos."""
        equipo = Equipo.objects.create(
            codigo_interno='DEL001',
            nombre='Equipo a Eliminar',
            empresa=self.empresa,
            tipo_equipo='Equipo de Medición'
        )

        self.client.login(username='cruduser', password='crudpass123')

        response = self.client.post(
            reverse('core:eliminar_equipo', kwargs={'pk': equipo.pk})
        )

        # Verificar redirección (eliminación exitosa)
        self.assertEqual(response.status_code, 302)

        # Verificar que el equipo ya no existe
        with self.assertRaises(Equipo.DoesNotExist):
            Equipo.objects.get(pk=equipo.pk)


class DownloadPermissionTest(TestCase):
    """Tests para funcionalidad de permisos de descarga."""

    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass123"
        )

        self.empresa = Empresa.objects.create(
            nombre="Empresa Permisos",
            nit="111222333"
        )

        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            empresa=self.empresa
        )

    def test_toggle_download_permission_superuser_only(self):
        """Test que solo superusuarios pueden cambiar permisos."""
        # Usuario normal no puede acceder
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('core:toggle_download_permission'),
            data={'user_id': self.user.id, 'grant_permission': True},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 302)  # Redirect por falta de permisos

        # Superusuario sí puede acceder
        self.client.login(username='admin', password='adminpass123')
        response = self.client.post(
            reverse('core:toggle_download_permission'),
            data='{"user_id": ' + str(self.user.id) + ', "grant_permission": true}',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)

    def test_has_export_permission_property(self):
        """Test propiedad has_export_permission del usuario."""
        # Inicialmente no debe tener permiso
        self.assertFalse(self.user.has_export_permission)

        # Crear y asignar permiso
        content_type = ContentType.objects.get_for_model(Equipo)
        permission, created = Permission.objects.get_or_create(
            codename='can_export_reports',
            content_type=content_type,
            defaults={'name': 'Can export reports'}
        )

        self.user.user_permissions.add(permission)

        # Ahora debe tener el permiso
        self.assertTrue(self.user.has_export_permission)