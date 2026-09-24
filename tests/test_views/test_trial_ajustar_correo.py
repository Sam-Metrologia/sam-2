import pytest
from django.core import mail
from django.urls import reverse

from core.models import Empresa, CustomUser


@pytest.mark.django_db
def test_ajustar_correo_en_paso1_reenvia_credenciales(client, mailoutbox):
    data = {
        'nombre_empresa': 'Ajuste Correo S.A.S.',
        'nit': '900333222-1',
        'email_empresa': 'correoDeRelleno@test.com',
        'telefono': '+57 300 000 0002',
    }
    resp = client.post(reverse('core:solicitar_trial'), data=data, follow=True)
    assert len(mail.outbox) == 1  # correo de bienvenida inicial, al correo de relleno
    assert mail.outbox[0].to == ['correoDeRelleno@test.com']

    empresa = Empresa.objects.get(nit='900333222-1')
    admin = CustomUser.objects.get(empresa=empresa, rol_usuario='ADMINISTRADOR')

    # Paso 1: corrige el correo Y pone su propia clave
    resp2 = client.post(reverse('core:trial_exitoso'), data={
        'email': 'correo.real@empresa.com',
        'new_password1': 'MiClaveDeVerdad2026!',
        'new_password2': 'MiClaveDeVerdad2026!',
    }, follow=True)
    assert resp2.redirect_chain[-1][0] == reverse('core:dashboard')

    admin.refresh_from_db()
    empresa.refresh_from_db()
    assert admin.email == 'correo.real@empresa.com'
    assert empresa.email == 'correo.real@empresa.com'
    assert admin.check_password('MiClaveDeVerdad2026!')

    # Se reenviaron las credenciales al correo correcto
    assert len(mail.outbox) == 2
    assert mail.outbox[1].to == ['correo.real@empresa.com']
    gerente = CustomUser.objects.get(empresa=empresa, rol_usuario='GERENCIA')
    assert gerente.username in mail.outbox[1].body

    # Login por el correo nuevo funciona
    client.logout()
    assert client.login(username='correo.real@empresa.com', password='MiClaveDeVerdad2026!')


@pytest.mark.django_db
def test_no_reenvia_si_no_cambia_el_correo(client, mailoutbox):
    data = {
        'nombre_empresa': 'Sin Cambio S.A.S.',
        'nit': '900111222-1',
        'email_empresa': 'correo.correcto@test.com',
        'telefono': '+57 300 000 0003',
    }
    client.post(reverse('core:solicitar_trial'), data=data)
    assert len(mail.outbox) == 1

    client.post(reverse('core:trial_exitoso'), data={
        'email': 'correo.correcto@test.com',  # el mismo
        'new_password1': 'OtraClave2026!',
        'new_password2': 'OtraClave2026!',
    })

    # No se reenvía nada porque el correo no cambió
    assert len(mail.outbox) == 1
