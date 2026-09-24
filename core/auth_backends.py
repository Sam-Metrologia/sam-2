# core/auth_backends.py
# Backend de autenticación que permite iniciar sesión con el username
# generado automáticamente O con el correo electrónico del usuario.

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

UserModel = get_user_model()


class EmailOrUsernameBackend(ModelBackend):
    """
    Igual que el ModelBackend de Django, pero si el "username" que llega
    no coincide con ningún usuario, intenta buscarlo por correo.

    Si el correo está repetido en más de un usuario (el campo email no es
    único en CustomUser), no se arriesga a elegir uno al azar: la
    autenticación falla igual que con credenciales inválidas.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        try:
            user = UserModel.objects.get(username__iexact=username)
        except UserModel.DoesNotExist:
            candidatos = UserModel.objects.filter(email__iexact=username)
            if candidatos.count() != 1:
                # Correo no encontrado o compartido por varias cuentas.
                # Igual que ModelBackend, se corre un hash "falso" para
                # mitigar ataques de timing.
                UserModel().set_password(password)
                return None
            user = candidatos.first()
        except UserModel.MultipleObjectsReturned:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
