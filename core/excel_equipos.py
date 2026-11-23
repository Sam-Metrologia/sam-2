# core/excel_equipos.py
# Excel único de equipos: lo usan el "Listado General Equipos" de Informes (una sede o
# todo el grupo) y el Informe_Consolidado.xlsx de los ZIP. Hojas: Resumen, Conteo por
# nombre, Equipos, Proveedores, Procedimientos, Préstamos y Dashboard.

import io
from datetime import date, datetime, timedelta

from django.utils import timezone
from openpyxl import Workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .busqueda_equipos import ESTADOS_FUERA_DE_SERVICIO, normalizar
from .tenancy import get_empresa_formato

AZUL_OSCURO, AZUL = '1F4E79', '4F81BD'
FILA_TITULOS = 5  # los títulos de columna van siempre en esta fila

COLUMNAS_EQUIPOS = [
    'Código Interno', 'Nombre', 'Empresa / Sede', 'Tipo de Equipo', 'Marca', 'Modelo', 'Número de Serie',
    'Ubicación', 'Responsable', 'Estado', 'Fecha de Adquisición', 'Rango de Medida', 'Resolución',
    'Error Máximo Permisible', 'Puntos de Calibración', 'Fecha de Registro', 'Observaciones',
    'Último Certificado Calibración', 'Fecha Última Calibración', 'Próxima Calibración',
    'Frecuencia Calibración (meses)', 'Fecha Último Mantenimiento', 'Próximo Mantenimiento',
    'Frecuencia Mantenimiento (meses)', 'Fecha Última Comprobación', 'Próxima Comprobación',
    'Frecuencia Comprobación (meses)',
]


def _valor(valor):
    """Deja el valor listo para Excel (sin zona horaria ni caracteres que Excel rechaza)."""
    if isinstance(valor, datetime) and timezone.is_aware(valor):
        return timezone.localtime(valor).replace(tzinfo=None)
    if isinstance(valor, str):
        return ILLEGAL_CHARACTERS_RE.sub('', valor)
    return valor


def _fila(hoja, valores):
    hoja.append([_valor(v) for v in valores])
    for celda in hoja[hoja.max_row]:
        # Un texto del usuario que empiece por "=" no debe ejecutarse como fórmula.
        if celda.data_type == 'f':
            celda.data_type = 's'


def _titulos(hoja, titulos):
    # La primera tabla va en FILA_TITULOS; las siguientes, dejando una fila en blanco.
    fila = hoja.max_row + 2 if hoja.max_row >= FILA_TITULOS else FILA_TITULOS
    for columna, texto in enumerate(titulos, 1):
        celda = hoja.cell(row=fila, column=columna, value=texto)
        celda.font = Font(bold=True, color='FFFFFF')
        celda.fill = PatternFill('solid', start_color=AZUL, end_color=AZUL)
        celda.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    return fila


def _hoja(libro, nombre, titulos, encabezado, anchos=None):
    """Hoja con encabezado de SAM, línea de formato y títulos de columna."""
    hoja = libro.create_sheet(nombre)
    ultima = get_column_letter(max(len(titulos), 5))
    hoja.merge_cells(f'A1:{ultima}1')
    hoja['A1'] = 'INFORMES GENERADOS POR SAM METROLOGÍA SAS'
    hoja['A1'].font = Font(bold=True, size=16, color='FFFFFF')
    hoja['A1'].fill = PatternFill('solid', start_color=AZUL_OSCURO, end_color=AZUL_OSCURO)
    hoja['A1'].alignment = Alignment(horizontal='left', vertical='center')
    hoja.row_dimensions[1].height = 30
    for numero, texto in enumerate(encabezado, 2):
        hoja.cell(row=numero, column=1, value=_valor(texto)).font = Font(bold=True, size=11, color=AZUL_OSCURO)
    _titulos(hoja, titulos)
    for i in range(1, max(len(titulos), 5) + 1):
        hoja.column_dimensions[get_column_letter(i)].width = (anchos or {}).get(i, 20)
    return hoja


def _encabezado(empresa, titulo, parcial=''):
    """Líneas 2 a 4: de quién es el listado, el formato y, si no son todas, qué sedes incluye."""
    lineas = [f'{titulo} — Generado el {timezone.localtime():%Y-%m-%d %H:%M}']
    if empresa:
        fecha = empresa.listado_fecha_formato_display or (
            empresa.listado_fecha_formato.strftime('%Y-%m-%d') if empresa.listado_fecha_formato else 'N/A')
        lineas.append(f'FORMATO: Código: {empresa.listado_codigo or "N/A"} | '
                      f'Versión: {empresa.listado_version or "N/A"} | Fecha: {fecha}')
    if parcial:
        lineas.append(parcial)
    return lineas


def _contar(equipos, clave):
    """{clave: [etiqueta, activos, inactivos, de baja, total]} conservando el orden de llegada."""
    conteo = {}
    for equipo in equipos:
        llave, etiqueta = clave(equipo)
        fila = conteo.setdefault(llave, [etiqueta, 0, 0, 0, 0])
        columna = {'Inactivo': 2, 'De Baja': 3}.get(equipo.estado, 1)
        fila[columna] += 1
        fila[4] += 1
    return conteo


def _ultimos_certificados(equipos):
    """{equipo_id: número del certificado de su última calibración} con una sola consulta."""
    from .models import Calibracion
    certificados = {}
    consulta = Calibracion.objects.filter(
        equipo__empresa_id__in={e.empresa_id for e in equipos}
    ).order_by('fecha_calibracion', 'id').values_list('equipo_id', 'numero_certificado')
    for equipo_id, numero in consulta:
        certificados[equipo_id] = numero
    return certificados


def _hoja_dashboard(libro, equipos, encabezado):
    from .models import Calibracion, Comprobacion, Mantenimiento
    hoja = _hoja(libro, 'Dashboard', ['Estado', 'Cantidad', 'Porcentaje'], encabezado, {1: 32, 3: 40})
    hoy = date.today()
    limite = hoy + timedelta(days=30)
    total = len(equipos)
    ids_empresas = {e.empresa_id for e in equipos}

    por_estado = {}
    for equipo in equipos:
        por_estado[equipo.estado] = por_estado.get(equipo.estado, 0) + 1
    for estado, cantidad in sorted(por_estado.items(), key=lambda x: -x[1]):
        _fila(hoja, [estado, cantidad, f'{cantidad / total * 100:.1f}%'])
    _fila(hoja, ['TOTAL', total])

    _titulos(hoja, ['Actividad', f'Realizadas {hoy.year}', 'Vencidas', 'Próximas (30 días)'])
    en_servicio = [e for e in equipos if e.estado not in ESTADOS_FUERA_DE_SERVICIO]
    for nombre, modelo, campo_fecha, campo_proxima in (
            ('Calibraciones', Calibracion, 'fecha_calibracion', 'proxima_calibracion'),
            ('Mantenimientos', Mantenimiento, 'fecha_mantenimiento', 'proximo_mantenimiento'),
            ('Comprobaciones', Comprobacion, 'fecha_comprobacion', 'proxima_comprobacion')):
        realizadas = modelo.objects.filter(
            equipo__empresa_id__in=ids_empresas, **{f'{campo_fecha}__year': hoy.year}).count()
        fechas = [f for f in (getattr(e, campo_proxima) for e in en_servicio) if f]
        _fila(hoja, [nombre, realizadas, sum(f < hoy for f in fechas), sum(hoy <= f <= limite for f in fechas)])

    correctivos = Mantenimiento.objects.filter(
        equipo__empresa_id__in=ids_empresas, tipo_mantenimiento='Correctivo', fecha_mantenimiento__year=hoy.year,
    ).select_related('equipo', 'equipo__empresa').order_by('-fecha_mantenimiento')
    _titulos(hoja, [f'Correctivos {hoy.year}: equipo', 'Fecha', 'Descripción', 'Responsable', 'Sede'])
    for m in correctivos:
        _fila(hoja, [m.equipo.codigo_interno, m.fecha_mantenimiento, m.descripcion or '', m.responsable or '',
                     m.equipo.empresa.nombre])


def construir_excel(equipos, proveedores=(), procedimientos=(), prestamos=None, empresas=None, titulo=None,
                    grupo=None, con_formato=True):
    """
    Arma el Excel y devuelve sus bytes. `grupo`: [matriz, sedes...] completo cuando
    `empresas` son sedes de un grupo: si son varias el formato es el de la matriz, y si no son
    todas el encabezado dice cuáles. prestamos=None omite esa hoja.
    """
    equipos = list(equipos)
    empresas = list(empresas) if empresas is not None else list({e.empresa_id: e.empresa for e in equipos}.values())
    if titulo is None:
        titulo = empresas[0].nombre if len(empresas) == 1 else 'Listado de equipos'
    grupo = grupo or empresas
    parcial = ''
    if con_formato and len(empresas) > 1:
        titulo = f'GRUPO {grupo[0].nombre} (matriz y {len(grupo) - 1} sedes)'
        if len(empresas) < len(grupo):
            titulo = f'GRUPO {grupo[0].nombre}'
            parcial = (f'LISTADO PARCIAL: {len(empresas)} de {len(grupo)} sedes — '
                       + ', '.join(e.nombre for e in empresas))
    formato = get_empresa_formato(empresas, grupo) if con_formato else None
    encabezado = _encabezado(formato, titulo, parcial)
    libro = Workbook()
    libro.remove(libro.active)

    columnas = ['Activos', 'Inactivos', 'De baja', 'Total']
    hoja = _hoja(libro, 'Resumen', ['Empresa / Sede'] + columnas, encabezado, {1: 42})
    por_sede = _contar(equipos, lambda e: (e.empresa_id, e.empresa.nombre))
    totales = [0, 0, 0, 0]
    for empresa in empresas:
        fila = por_sede.get(empresa.id, [empresa.nombre, 0, 0, 0, 0])
        _fila(hoja, fila)
        totales = [a + b for a, b in zip(totales, fila[1:])]
    _fila(hoja, [f'TOTAL PARCIAL ({len(empresas)} de {len(grupo)} sedes)' if parcial else 'TOTAL'] + totales)
    for celda in hoja[hoja.max_row]:
        celda.font = Font(bold=True)
    _fila(hoja, ['"Activos" incluye los que están en mantenimiento, calibración o comprobación.'])

    hoja = _hoja(libro, 'Conteo por nombre', ['Nombre'] + columnas, encabezado, {1: 42})
    por_nombre = _contar(equipos, lambda e: (normalizar(e.nombre), e.nombre.strip()))
    for fila in sorted(por_nombre.values(), key=lambda f: (-f[4], normalizar(f[0]))):
        _fila(hoja, fila)

    hoja = _hoja(libro, 'Equipos', COLUMNAS_EQUIPOS, encabezado, {2: 32, 3: 30, 17: 40})
    certificados = _ultimos_certificados(equipos)
    for e in equipos:
        _fila(hoja, [
            e.codigo_interno, e.nombre, e.empresa.nombre, e.get_tipo_equipo_display(), e.marca, e.modelo,
            e.numero_serie, e.ubicacion, e.responsable, e.estado, e.fecha_adquisicion, e.rango_medida,
            e.resolucion, e.error_maximo_permisible, e.puntos_calibracion, e.fecha_registro, e.observaciones,
            certificados.get(e.id) or 'N/A', e.fecha_ultima_calibracion, e.proxima_calibracion,
            e.frecuencia_calibracion_meses, e.fecha_ultimo_mantenimiento, e.proximo_mantenimiento,
            e.frecuencia_mantenimiento_meses, e.fecha_ultima_comprobacion, e.proxima_comprobacion,
            e.frecuencia_comprobacion_meses,
        ])
    hoja.freeze_panes = hoja.cell(row=FILA_TITULOS + 1, column=3)
    hoja.auto_filter.ref = f'A{FILA_TITULOS}:{get_column_letter(len(COLUMNAS_EQUIPOS))}{max(hoja.max_row, FILA_TITULOS)}'

    hoja = _hoja(libro, 'Proveedores', [
        'Nombre Empresa', 'Nombre Contacto', 'Correo Electrónico', 'Número Contacto', 'Tipo Servicio', 'Alcance',
        'Servicio Prestado', 'Página Web', 'Empresa / Sede'], encabezado)
    for p in proveedores:
        _fila(hoja, [p.nombre_empresa, p.nombre_contacto, p.correo_electronico, p.numero_contacto, p.tipo_servicio,
                     p.alcance, p.servicio_prestado, p.pagina_web, p.empresa.nombre if p.empresa else ''])

    hoja = _hoja(libro, 'Procedimientos', [
        'Código', 'Nombre', 'Observaciones', 'Versión', 'Fecha de Emisión', 'Empresa / Sede'], encabezado)
    for p in procedimientos:
        _fila(hoja, [p.codigo, p.nombre, p.observaciones, p.version, p.fecha_emision,
                     p.empresa.nombre if p.empresa else ''])

    if prestamos is not None:
        hoja = _hoja(libro, 'Préstamos', [
            'Código Equipo', 'Nombre Equipo', 'Prestatario', 'Cédula', 'Cargo', 'Teléfono', 'Email',
            'Fecha Préstamo', 'Devolución Programada', 'Devolución Real', 'Estado', 'Observaciones',
            'Empresa / Sede'], encabezado)
        for p in prestamos:
            _fila(hoja, [
                p.equipo.codigo_interno, p.equipo.nombre, p.nombre_prestatario, p.cedula_prestatario,
                p.cargo_prestatario, p.telefono_prestatario, p.email_prestatario, p.fecha_prestamo,
                p.fecha_devolucion_programada, p.fecha_devolucion_real, p.get_estado_prestamo_display(),
                p.observaciones_prestamo, p.empresa.nombre if p.empresa else ''])

    _hoja_dashboard(libro, equipos, encabezado)

    salida = io.BytesIO()
    libro.save(salida)
    return salida.getvalue()


def excel_de_empresas(empresas, con_prestamos, titulo=None, grupo=None):
    """Excel de una o varias empresas (de `grupo`). empresas=None: todas las activas."""
    from .models import Empresa, Equipo, PrestamoEquipo, Procedimiento, Proveedor
    todas = empresas is None
    if todas:
        empresas = list(Empresa.objects.filter(is_deleted=False).order_by('nombre'))
        titulo = 'Todas las empresas'
    ids = [e.id for e in empresas]
    prestamos = None
    if con_prestamos:
        prestamos = PrestamoEquipo.objects.filter(
            empresa_id__in=ids).select_related('equipo', 'empresa').order_by('-fecha_prestamo')
    return construir_excel(
        Equipo.objects.filter(empresa_id__in=ids).select_related('empresa').order_by('empresa__nombre', 'codigo_interno'),
        Proveedor.objects.filter(empresa_id__in=ids).select_related('empresa').order_by('empresa__nombre', 'nombre_empresa'),
        Procedimiento.objects.filter(empresa_id__in=ids).select_related('empresa').order_by('empresa__nombre', 'codigo'),
        # Con todas las empresas de la plataforma no hay un formato único que mostrar.
        prestamos, empresas=empresas, titulo=titulo, grupo=grupo, con_formato=not todas)
