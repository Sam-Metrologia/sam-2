# core/busqueda_equipos.py
# Búsqueda, filtro por estado y conteo de equipos. Lo comparten el listado de equipos
# y el resumen del grupo (matriz + sedes), para que los dos cuenten igual.

import re
import unicodedata

from .constants import (
    EQUIPO_ESTADO_CHOICES, ESTADO_ACTIVO, ESTADO_DE_BAJA, ESTADO_INACTIVO,
)

# Valores especiales del filtro de estado (además de cada estado puntual).
FILTRO_ACTIVOS = 'activos'  # predeterminado: todo lo que no está inactivo ni de baja
FILTRO_TODOS = 'todos'

ESTADOS_FUERA_DE_SERVICIO = (ESTADO_INACTIVO, ESTADO_DE_BAJA)

# "Activo" no se repite como opción suelta: ya está "Activos".
OPCIONES_ESTADO = [
    (FILTRO_ACTIVOS, 'Activos'),
    (FILTRO_TODOS, 'Todos (incluye inactivos y de baja)'),
] + [(valor, texto) for valor, texto in EQUIPO_ESTADO_CHOICES if valor != ESTADO_ACTIVO]

CAMPOS_BUSQUEDA = (
    'codigo_interno', 'nombre', 'marca', 'modelo', 'numero_serie', 'responsable', 'ubicacion',
)


def normalizar(texto):
    """Minúsculas, sin tildes y sin espacios repetidos: 'Cinta  Métrica' -> 'cinta metrica'."""
    texto = unicodedata.normalize('NFKD', str(texto or ''))
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', texto).strip().lower()


def _variantes(palabra):
    """La palabra y su posible singular, para que 'cintas' encuentre 'cinta'."""
    variantes = [palabra]
    if len(palabra) >= 5 and palabra.isalpha() and palabra.endswith('s'):
        variantes.append(palabra[:-1])
        if palabra.endswith('es') and len(palabra) >= 7:
            variantes.append(palabra[:-2])
    return variantes


def filtrar_por_texto(queryset, query):
    """
    Busca sin distinguir tildes ni mayúsculas. Todas las palabras deben estar en un MISMO
    campo: así 'cinta 5' no cuenta las cintas que solo tienen un 5 en la serie.
    Se hace en Python porque el resultado debe ser igual en SQLite y PostgreSQL.
    """
    palabras = [_variantes(p) for p in normalizar(query).split()]
    if not palabras:
        return queryset
    ids = []
    for fila in queryset.order_by().values_list('pk', *CAMPOS_BUSQUEDA):
        for valor in fila[1:]:
            texto = normalizar(valor)
            if texto and all(any(v in texto for v in variantes) for variantes in palabras):
                ids.append(fila[0])
                break
    return queryset.filter(pk__in=ids)


def estado_valido(valor):
    """Filtro de estado a usar: si viene vacío o desconocido, 'activos'."""
    if valor == ESTADO_ACTIVO:
        return FILTRO_ACTIVOS
    return valor if valor in dict(OPCIONES_ESTADO) else FILTRO_ACTIVOS


def filtrar_por_estado(queryset, estado):
    """Aplica un filtro ya validado con estado_valido()."""
    if estado == FILTRO_TODOS:
        return queryset
    if estado == FILTRO_ACTIVOS:
        return queryset.exclude(estado__in=ESTADOS_FUERA_DE_SERVICIO)
    return queryset.filter(estado=estado)


def _nuevo_conteo():
    return {'activos': 0, 'inactivos': 0, 'de_baja': 0, 'total': 0}


def _sumar(conteo, estado):
    if estado == ESTADO_INACTIVO:
        conteo['inactivos'] += 1
    elif estado == ESTADO_DE_BAJA:
        conteo['de_baja'] += 1
    else:
        conteo['activos'] += 1
    conteo['total'] += 1


def contar(queryset):
    """
    Cuenta los equipos (sin filtrar por estado) en total, por nombre y por empresa.
    'activos' = todo lo que no está inactivo ni de baja (incluye en calibración, etc.).
    """
    total, por_nombre, por_empresa = _nuevo_conteo(), {}, {}
    for nombre, estado, empresa_id in queryset.order_by().values_list('nombre', 'estado', 'empresa_id'):
        _sumar(total, estado)
        clave = normalizar(nombre)
        if clave not in por_nombre:
            por_nombre[clave] = {'nombre': nombre.strip(), **_nuevo_conteo()}
        _sumar(por_nombre[clave], estado)
        _sumar(por_empresa.setdefault(empresa_id, _nuevo_conteo()), estado)
    nombres = sorted(por_nombre.values(), key=lambda n: (-n['total'], normalizar(n['nombre'])))
    return {'total': total, 'por_nombre': nombres, 'por_empresa': por_empresa}


def querystring_sin(request, *claves):
    """Parámetros actuales de la URL sin algunas claves (para enlaces que conservan los filtros)."""
    params = request.GET.copy()
    for clave in claves:
        params.pop(clave, None)
    return params.urlencode()
