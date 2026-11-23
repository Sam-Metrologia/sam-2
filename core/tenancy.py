# core/tenancy.py
# Punto único para resolver la empresa activa del usuario en la request actual.

SESSION_KEY_EMPRESA_ACTIVA = 'empresa_activa_id'


def get_empresas_seleccionables(user):
    """
    Devuelve las empresas entre las que un usuario puede alternar como
    "empresa activa": su propia empresa, y si es GERENCIA de una empresa
    matriz (empresa_matriz is None) con sedes, también esas sedes. El
    superusuario con empresa asignada puede alternar en el grupo de esa empresa.

    Para cualquier otro caso (usuario sin empresa, GERENCIA de una sede,
    ADMINISTRADOR/TECNICO) devuelve solo su propia empresa — no hay nada
    entre qué elegir, por lo que no debe mostrarse ningún selector.
    """
    empresa = getattr(user, 'empresa', None)
    if not empresa:
        return []
    if user.is_superuser:
        return get_grupo(empresa)
    if empresa.empresa_matriz_id is not None:
        return [empresa]
    if not user.is_gerente():
        return [empresa]
    return get_grupo(empresa)


def get_grupo(empresa):
    """Grupo al que pertenece una empresa: [matriz, sede, sede...] (sin sedes eliminadas)."""
    matriz = empresa.empresa_matriz or empresa
    return [matriz] + list(matriz.sedes.filter(is_deleted=False).order_by('nombre'))


def get_matrices():
    """Empresas que tienen al menos una sede (para que el superusuario elija grupo)."""
    from .models import Empresa
    return list(
        Empresa.objects.filter(is_deleted=False, sedes__is_deleted=False).distinct().order_by('nombre'))


def get_empresa_id_filtro(request):
    """
    Empresa por la que el SUPERUSUARIO está filtrando una pantalla: la que viene en la
    URL (?empresa_id=, vacío = todas) o, si no viene, la sede elegida en el selector.
    Para los demás usuarios devuelve None: ellos solo ven su empresa activa.
    """
    if not request.user.is_superuser:
        return None
    if 'empresa_id' in request.GET:
        return request.GET.get('empresa_id')
    session = getattr(request, 'session', None)
    elegida = session.get(SESSION_KEY_EMPRESA_ACTIVA) if session is not None else None
    if elegida:
        empresa = get_empresa_activa(request)
        if empresa and empresa.id == elegida:
            return str(empresa.id)
    return None


def get_grupo_consulta(request):
    """
    Grupo completo [matriz, sedes...] del que se puede elegir en el listado y en su Excel:
    el propio para el gerente de la matriz; el de ?empresa_id=grupo-<id matriz> para el
    superusuario. [] si no hay un grupo entre el cual elegir.
    """
    if request.user.is_superuser:
        elegida = get_empresa_id_filtro(request) or ''
        matriz = next((m for m in get_matrices() if f'grupo-{m.id}' == elegida), None) \
            if elegida.startswith('grupo-') else None
        return get_grupo(matriz) if matriz else []
    grupo = [e for e in get_empresas_seleccionables(request.user) if not e.is_deleted]
    return grupo if len(grupo) > 1 else []


def _sedes_marcadas(request, grupo):
    """Sedes del grupo pedidas en la URL (?sede=8&sede=24 o ?sede=todas). Ids ajenos se ignoran."""
    pedidas = set(request.GET.getlist('sede'))
    if 'todas' in pedidas:
        return grupo
    return [e for e in grupo if str(e.id) in pedidas]


def get_empresas_consulta(request):
    """
    Empresas que se están consultando en el listado de equipos o en su Excel:
        (empresas, seleccion)
    - Gerente de matriz: una o varias sedes de su grupo (?sede=...); si no, su sede activa.
    - Superusuario: ?empresa_id=<id>, vacío = todas (empresas=None), o ?empresa_id=grupo-<id matriz>
      (todo el grupo, o solo las sedes marcadas con ?sede=...).
    - Los demás: siempre su empresa. Un id ajeno en la URL se ignora.
    Conserva el orden del grupo (la matriz primero). [] = nada que mostrar.
    """
    from .models import Empresa
    if request.user.is_superuser:
        elegida = get_empresa_id_filtro(request) or ''
        if not elegida:
            return None, ''
        if elegida.startswith('grupo-'):
            grupo = get_grupo_consulta(request)
            return _sedes_marcadas(request, grupo) or grupo, elegida
        if not elegida.isdigit():
            return [], elegida
        return list(Empresa.objects.filter(pk=elegida, is_deleted=False)), elegida

    activa = get_empresa_activa(request)
    if not activa or activa.is_deleted:
        return [], ''
    marcadas = _sedes_marcadas(request, get_grupo_consulta(request))
    if len(marcadas) > 1:
        return marcadas, ''
    return (marcadas or [activa]), str((marcadas or [activa])[0].id)


def get_empresa_formato(empresas, grupo):
    """Empresa cuyo formato encabeza el listado: la matriz si son varias sedes; si no, la única."""
    if not empresas:
        return None
    return grupo[0] if grupo and len(empresas) > 1 else empresas[0]


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

    if not empresa_default:
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
