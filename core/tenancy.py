# core/tenancy.py
# Punto único para resolver la empresa activa del usuario en la request actual.

SESSION_KEY_EMPRESA_ACTIVA = 'empresa_activa_id'


def get_empresas_seleccionables(user):
    """
    Devuelve las empresas entre las que un usuario puede alternar como
    "empresa activa": su propia empresa, y si es GERENCIA de una empresa
    matriz (empresa_matriz is None) con sedes, también esas sedes.

    Para cualquier otro caso (usuario sin empresa, GERENCIA de una sede,
    ADMINISTRADOR/TECNICO) devuelve solo su propia empresa — no hay nada
    entre qué elegir, por lo que no debe mostrarse ningún selector.
    """
    empresa = getattr(user, 'empresa', None)
    if not empresa:
        return []
    if empresa.empresa_matriz_id is not None:
        return [empresa]
    if not user.is_gerente():
        return [empresa]
    sedes = list(empresa.sedes.filter(is_deleted=False).order_by('nombre'))
    return [empresa] + sedes


def get_empresa_activa(request):
    """
    Devuelve la empresa "activa" para la request actual.

    Para el 99% de los usuarios (una sola empresa, sin sedes) esto es un
    passthrough exacto de request.user.empresa — comportamiento idéntico al
    histórico. Si el usuario es GERENCIA de una empresa matriz con sedes y
    tiene una sede elegida en sesión, devuelve esa sede en vez de su empresa
    por defecto — siempre validando que la sede elegida esté realmente entre
    las que ese usuario puede ver (nunca se confía ciegamente en lo guardado
    en sesión).
    """
    user = request.user
    empresa_default = getattr(user, 'empresa', None)

    if not empresa_default or user.is_superuser:
        return empresa_default

    # Requests construidas con RequestFactory (tests que llaman la vista
    # directamente) no pasan por SessionMiddleware y no tienen .session.
    # Tratarlo igual que "sin selección en sesión" — comportamiento histórico.
    session = getattr(request, 'session', None)
    empresa_id_sesion = session.get(SESSION_KEY_EMPRESA_ACTIVA) if session is not None else None
    if not empresa_id_sesion:
        return empresa_default

    seleccionables = get_empresas_seleccionables(user)
    for empresa in seleccionables:
        if empresa.id == empresa_id_sesion:
            return empresa

    return empresa_default
