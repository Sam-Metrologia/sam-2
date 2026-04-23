# core/views/confirmacion.py
"""
Vistas para Confirmación Metrológica e Intervalos de Calibración
Integrado con datos reales de la base de datos
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
from core.models import Equipo, Calibracion, meses_decimales_a_relativedelta
from core.decorators_pdf import safe_pdf_response
from .base import access_check, trial_check
from core.monitoring import monitor_view
from datetime import datetime
import json
import re
import base64
from io import BytesIO
import matplotlib
matplotlib.use('Agg')  # Backend sin GUI
import matplotlib.pyplot as plt
import numpy as np
import logging

logger = logging.getLogger('core')


def safe_float(value, default=0.0):
    """
    Convierte un valor a float de forma segura.
    Maneja cadenas vacías, None, y valores inválidos.

    Args:
        value: Valor a convertir
        default: Valor por defecto si la conversión falla (default: 0.0)

    Returns:
        float: Valor convertido o default
    """
    if value is None or value == '' or (isinstance(value, str) and value.strip() == ''):
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _generar_grafica_confirmacion(puntos_medicion, emp_valor, emp_unidad, unidad_equipo):
    """
    Genera gráfica de confirmación metrológica normalizada por EMP.
    Y = error / EMP_absoluto  →  límites siempre en ±1, sin efecto embudo.
    """
    try:
        puntos_validos = [p for p in puntos_medicion
                         if p.get('nominal') and (p.get('error') is not None or p.get('lectura') is not None)]
        if not puntos_validos:
            return None

        nominales = [safe_float(p.get('nominal', 0), 0) for p in puntos_validos]

        # Calcular error por punto
        errores = []
        for p in puntos_validos:
            if p.get('error') is not None:
                errores.append(safe_float(p['error'], 0))
            else:
                errores.append(safe_float(p.get('lectura', 0), 0) - safe_float(p['nominal'], 0))

        incertidumbres = [safe_float(p.get('incertidumbre', 0), 0) for p in puntos_validos]

        # Calcular EMP absoluto por punto (unifica % y abs)
        emps_abs = []
        for i, p in enumerate(puntos_validos):
            if p.get('emp_absoluto') is not None and safe_float(p['emp_absoluto'], 0) != 0:
                emps_abs.append(safe_float(p['emp_absoluto'], 0))
            else:
                # Calcular desde emp_valor global
                n = nominales[i]
                if emp_unidad == '%':
                    emps_abs.append(abs(n) * (emp_valor / 100) if n != 0 else emp_valor)
                else:
                    emps_abs.append(emp_valor if emp_valor != 0 else 1)

        # Normalizar: Y = error / EMP_abs  (±1 = en el límite)
        y_norm = [e / ea if ea != 0 else 0 for e, ea in zip(errores, emps_abs)]
        u_norm = [u / ea if ea != 0 else 0 for u, ea in zip(incertidumbres, emps_abs)]

        # Detectar si EMP varía entre puntos
        emp_variable = max(emps_abs) / min(emps_abs) > 1.05 if min(emps_abs) > 0 else False

        n_puntos = len(puntos_validos)
        ancho_fig = max(12, n_puntos * 0.9)
        markersize = max(4, 9 - max(0, n_puntos - 8))
        fig, ax = plt.subplots(figsize=(ancho_fig, 6))

        # Escala log en X si el rango nominal supera 100x
        nominales_pos = [n for n in nominales if n > 0]
        usar_log = len(nominales_pos) > 1 and max(nominales_pos) / min(nominales_pos) > 100
        if usar_log:
            ax.set_xscale('log')
            import math
            log_min = math.log10(min(nominales_pos))
            log_max = math.log10(max(nominales_pos))
            pad = (log_max - log_min) * 0.06
            ax.set_xlim(10 ** (log_min - pad), 10 ** (log_max + pad))
        elif nominales:
            span = max(nominales) - min(nominales)
            margin = span * 0.06 if span > 0 else abs(nominales[0]) * 0.5 or 1
            ax.set_xlim(min(nominales) - margin, max(nominales) + margin)

        # Puntos con barras de incertidumbre normalizadas
        ax.errorbar(nominales, y_norm, yerr=u_norm,
                   fmt='o-', color='#3b82f6', linewidth=2, markersize=markersize,
                   ecolor='#60a5fa', elinewidth=2, capsize=4, capthick=2,
                   label='Error normalizado (Error/EMP) ± Incertidumbre')

        # Límites EMP: siempre ±1
        if emp_variable:
            # EMP diferente por punto → líneas escalonadas en ±1 con anotación del valor real
            ax.step(nominales, [1.0] * n_puntos, where='mid',
                   color='r', linestyle='--', linewidth=2, label='Límite EMP (variable)')
            ax.step(nominales, [-1.0] * n_puntos, where='mid',
                   color='r', linestyle='--', linewidth=2)
            # Anotar el EMP real de cada punto
            for i, (n, ea) in enumerate(zip(nominales, emps_abs)):
                emp_tipo = puntos_validos[i].get('emp_tipo', emp_unidad)
                label_emp = f'{ea:.3g} {emp_tipo}'
                ax.annotate(label_emp, xy=(n, 1.0), xytext=(0, 6),
                           textcoords='offset points', ha='center',
                           fontsize=7, color='darkred')
        else:
            ax.axhline(y=1.0, color='r', linestyle='--', linewidth=2, label='+EMP')
            ax.axhline(y=-1.0, color='r', linestyle='--', linewidth=2, label='−EMP')

        ax.axhline(y=0, color='black', linestyle='-', linewidth=1, alpha=0.3)

        # Zona de conformidad sombreada
        ax.axhspan(-1.0, 1.0, alpha=0.04, color='green')

        ax.set_xlabel(f'Valor Nominal ({unidad_equipo})', fontsize=12, fontweight='bold')
        ax.set_ylabel('Error normalizado  (Error / EMP)', fontsize=12, fontweight='bold')
        ax.set_title('Confirmación Metrológica — Error normalizado por EMP  (±1 = límite)',
                    fontsize=13, fontweight='bold', pad=20)

        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.12),
                 ncol=3, fontsize=9, framealpha=0.95, edgecolor='gray')
        ax.grid(True, alpha=0.3, linestyle='--')
        plt.tight_layout()
        plt.subplots_adjust(bottom=0.15)

        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        plt.close(fig)
        return f'data:image/png;base64,{image_base64}'

    except Exception as e:
        logger.error(f"Error generando gráfica confirmacion: {str(e)}")
        return None


def _preparar_contexto_confirmacion(request, equipo, ultima_calibracion, datos_confirmacion=None):
    """
    Función helper para preparar el contexto de confirmación metrológica

    Reutilizable tanto para la vista HTML como para generación de PDF
    """
    # Obtener TODAS las calibraciones históricas para la gráfica
    calibraciones_historicas = Calibracion.objects.filter(
        equipo=equipo
    ).order_by('-fecha_calibracion')  # Sin límite, todas

    # ==================== DATOS PREVIOS GUARDADOS (para pre-llenar el form) ====================
    datos_guardados = None
    if (not datos_confirmacion and
            ultima_calibracion and
            hasattr(ultima_calibracion, 'confirmacion_metrologica_datos') and
            ultima_calibracion.confirmacion_metrologica_datos):
        datos_guardados = ultima_calibracion.confirmacion_metrologica_datos

    # ==================== PARSEAR PUNTOS DE CALIBRACIÓN ====================
    puntos_medicion = []

    if datos_confirmacion and 'puntos_medicion' in datos_confirmacion:
        # Si vienen datos del POST, usarlos
        puntos_medicion = datos_confirmacion['puntos_medicion']
    elif datos_guardados and datos_guardados.get('puntos_medicion'):
        # Si hay datos previos guardados (sin POST), pre-llenar con mediciones completas
        puntos_medicion = datos_guardados['puntos_medicion']
    elif equipo.puntos_calibracion:
        # Sino, parsear desde el equipo
        puntos_texto = equipo.puntos_calibracion.replace('\n', ',').replace(';', ',')
        puntos_lista = [p.strip() for p in puntos_texto.split(',') if p.strip()]

        for punto_str in puntos_lista:
            try:
                nominal = float(punto_str)
                puntos_medicion.append({
                    'nominal': nominal,
                    'lectura': '',
                    'incertidumbre': '',
                    'error': '',
                    'conformidad': ''
                })
            except ValueError:
                continue

    # Si no hay puntos definidos, usar puntos genéricos del rango
    if not puntos_medicion and equipo.rango_medida:
        rango_match = re.search(r'(\d+\.?\d*)\s*-\s*(\d+\.?\d*)', equipo.rango_medida)
        if rango_match:
            min_val = float(rango_match.group(1))
            max_val = float(rango_match.group(2))

            if max_val > min_val:
                paso = (max_val - min_val) / 4
                for i in range(5):
                    nominal = min_val + (paso * i)
                    puntos_medicion.append({
                        'nominal': round(nominal, 2),
                        'lectura': '',
                        'incertidumbre': '',
                        'error': '',
                        'conformidad': ''
                    })

    # ==================== PREPARAR DATOS HISTÓRICOS PARA GRÁFICA ====================
    calibraciones_dict = {}

    for cal in calibraciones_historicas:
        anio = cal.fecha_calibracion.year

        # TODO: Cuando se implemente modelo PuntoMedicion, cargar desde ahí
        # Por ahora, estructura vacía para que JavaScript sepa que hay calibraciones
        calibraciones_dict[str(anio)] = {
            'fecha': cal.fecha_calibracion.strftime('%Y-%m-%d'),
            'resultado': cal.resultado,
            'certificado': cal.numero_certificado or 'N/A',
            'puntos': []  # Aquí irían los puntos de medición guardados
        }

    # ==================== PARSEAR EMP ====================
    emp_info = {
        'valor': 8,  # Valor en formato de usuario (8 para 8%)
        'unidad': '%',
        'texto': '8%'
    }

    if equipo.error_maximo_permisible:
        emp_texto = equipo.error_maximo_permisible.strip()
        emp_match = re.search(r'([\d.]+)\s*(%|mm|lx|μm|°C|g|kg|m)?', emp_texto)
        if emp_match:
            emp_info['valor'] = float(emp_match.group(1))
            emp_info['unidad'] = emp_match.group(2) if emp_match.group(2) else ''
            emp_info['texto'] = emp_texto

            # NO dividir por 100 aquí - dejar el valor tal cual lo ingresó el usuario
            # La conversión se hace en JavaScript

    # ==================== CONTEXTO ====================
    # Determinar valores de formato específico de CONFIRMACIÓN (usar POST si está disponible, sino empresa)
    if datos_confirmacion and 'formato' in datos_confirmacion:
        formato_codigo = datos_confirmacion['formato'].get('codigo', equipo.empresa.confirmacion_codigo or 'SAM-CONF-001')
        formato_version = datos_confirmacion['formato'].get('version', equipo.empresa.confirmacion_version or '01')
        formato_fecha_str = datos_confirmacion['formato'].get('fecha')
        if formato_fecha_str:
            from datetime import datetime as dt
            try:
                formato_fecha = dt.strptime(formato_fecha_str, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                formato_fecha = equipo.empresa.confirmacion_fecha_formato or None
        else:
            formato_fecha = equipo.empresa.confirmacion_fecha_formato or None
    else:
        formato_codigo = equipo.empresa.confirmacion_codigo or 'SAM-CONF-001'
        formato_version = equipo.empresa.confirmacion_version or '01'
        formato_fecha = equipo.empresa.confirmacion_fecha_formato or None

    # Formatear fecha del formato si existe
    # IMPORTANTE: Respetar el campo _display que puede ser YYYY-MM o YYYY-MM-DD
    formato_fecha_formateada = None
    # Primero intentar usar el campo _display que preserva el formato original
    if equipo.empresa.confirmacion_fecha_formato_display:
        formato_fecha_formateada = equipo.empresa.confirmacion_fecha_formato_display
    elif formato_fecha:
        try:
            if isinstance(formato_fecha, str):
                # Si es string, usarlo directamente
                formato_fecha_formateada = formato_fecha
            else:
                # Si ya es date object, formatear como YYYY-MM-DD
                formato_fecha_formateada = formato_fecha.strftime('%Y-%m-%d')
        except:
            formato_fecha_formateada = str(formato_fecha)

    # Preparar magnitudes para el template de impresión (soporte v1 y v2)
    def _emp_resumen(mag_dict):
        """Genera un resumen legible del EMP basado en los valores reales de la tabla."""
        puntos = mag_dict.get('puntos_medicion', [])
        vistos = []
        seen = set()
        for p in puntos:
            v = p.get('emp_valor', '')
            t = p.get('emp_tipo', '%')
            if v and v != 0:
                label = f"{v} {t if t == '%' else 'Abs'}"
                if label not in seen:
                    seen.add(label)
                    vistos.append(label)
        if vistos:
            return ' / '.join(vistos)
        # Fallback: usar el emp del tab si no hay filas con EMP
        emp_val = mag_dict.get('emp', '')
        emp_uni = mag_dict.get('emp_unidad', '%')
        return f"{emp_val} {emp_uni}" if emp_val else '—'

    if datos_confirmacion and 'magnitudes' in datos_confirmacion:
        magnitudes_template = datos_confirmacion['magnitudes']
    elif datos_guardados and datos_guardados.get('magnitudes'):
        magnitudes_template = datos_guardados['magnitudes']
    else:
        # v1: envolver puntos_medicion como única magnitud
        magnitudes_template = [{
            'nombre': '',
            'unidad': (datos_confirmacion.get('unidad_equipo') if datos_confirmacion else None) or emp_info['unidad'],
            'emp': (datos_confirmacion.get('emp') if datos_confirmacion else None) or emp_info['valor'],
            'emp_unidad': (datos_confirmacion.get('emp_unidad') if datos_confirmacion else None) or emp_info['unidad'],
            'puntos_medicion': puntos_medicion,
            'resultado': None,
        }]

    # Agregar resumen de EMP real (desde las filas) a cada magnitud
    for mag in magnitudes_template:
        mag['emp_resumen'] = _emp_resumen(mag)

    # Preparar estructura datos_confirmacion para el template de impresión
    datos_confirmacion_template = {
        'formato': {
            'codigo': formato_codigo,
            'version': formato_version,
            'fecha': formato_fecha_formateada,
        },
        'equipo': {
            'nombre': datos_confirmacion.get('equipo', {}).get('nombre', equipo.nombre) if datos_confirmacion else equipo.nombre,
            'codigo_interno': datos_confirmacion.get('equipo', {}).get('codigo_interno', equipo.codigo_interno) if datos_confirmacion else equipo.codigo_interno,
            'numero_serie': datos_confirmacion.get('equipo', {}).get('numero_serie', equipo.numero_serie or 'N/A') if datos_confirmacion else (equipo.numero_serie or 'N/A'),
            'marca': datos_confirmacion.get('equipo', {}).get('marca', equipo.marca or 'N/A') if datos_confirmacion else (equipo.marca or 'N/A'),
            'modelo': datos_confirmacion.get('equipo', {}).get('modelo', equipo.modelo or 'N/A') if datos_confirmacion else (equipo.modelo or 'N/A'),
            'fecha_analisis': datos_confirmacion.get('equipo', {}).get('fecha_analisis', datetime.now().date()) if datos_confirmacion else datetime.now().date(),
        },
        'laboratorio': datos_confirmacion.get('laboratorio', ultima_calibracion.proveedor.nombre_empresa if ultima_calibracion and ultima_calibracion.proveedor else 'N/A') if datos_confirmacion else (ultima_calibracion.proveedor.nombre_empresa if ultima_calibracion and ultima_calibracion.proveedor else 'N/A'),
        'fecha_certificado': datos_confirmacion.get('fecha_certificado', ultima_calibracion.fecha_calibracion if ultima_calibracion else None) if datos_confirmacion else (ultima_calibracion.fecha_calibracion if ultima_calibracion else None),
        'numero_certificado': datos_confirmacion.get('numero_certificado', ultima_calibracion.numero_certificado if ultima_calibracion else 'N/A') if datos_confirmacion else (ultima_calibracion.numero_certificado if ultima_calibracion else 'N/A'),
        'emp': datos_confirmacion.get('emp', emp_info['valor']) if datos_confirmacion else emp_info['valor'],
        'emp_unidad': datos_confirmacion.get('emp_unidad', emp_info['unidad']) if datos_confirmacion else emp_info['unidad'],
        'emp_texto': equipo.error_maximo_permisible or f"{emp_info['valor']} {emp_info['unidad']}",
        'unidad_equipo': datos_confirmacion.get('unidad_equipo', emp_info['unidad']) if datos_confirmacion else emp_info['unidad'],
        'regla_decision': datos_confirmacion.get('regla_decision', 'guard_band_U') if datos_confirmacion else 'guard_band_U',
        'puntos_medicion': puntos_medicion,
        'magnitudes': magnitudes_template,
        'conclusion': datos_confirmacion.get('conclusion', {
            'decision': 'Pendiente',
            'observaciones': '',
            'responsable': ''
        }) if datos_confirmacion else {
            'decision': 'Pendiente',
            'observaciones': '',
            'responsable': ''
        },
    }

    context = {
        'equipo': equipo,
        'ultima_calibracion': ultima_calibracion,
        'calibraciones_historicas': calibraciones_historicas,
        'fecha_actual': datetime.now().date(),

        # Datos para JavaScript
        'puntos_medicion_json': json.dumps(puntos_medicion),
        'calibraciones_historicas_json': json.dumps(calibraciones_dict),  # NUEVO: Datos para gráfica
        'emp_info': emp_info,

        # Metadatos
        'nombre_empresa': equipo.empresa.nombre,
        'logo_empresa_url': equipo.empresa.logo_empresa.url if equipo.empresa.logo_empresa else None,

        # Codificación del formato (usar POST si está disponible)
        'formato_codigo': formato_codigo,
        'formato_version': formato_version,
        'formato_fecha': formato_fecha,
        'formato_fecha_display': equipo.empresa.confirmacion_fecha_formato_display or (formato_fecha.strftime('%Y-%m-%d') if formato_fecha else ''),

        # ID de calibración específica (si viene por GET)
        'calibracion_id': ultima_calibracion.id if ultima_calibracion else None,

        # Datos del POST si los hay
        'regla_decision': datos_confirmacion.get('regla_decision', 'guard_band_U') if datos_confirmacion else 'guard_band_U',
        'checklist': datos_confirmacion.get('checklist', {}) if datos_confirmacion else {},
        'metodo_intervalo': datos_confirmacion.get('metodo_intervalo', {}) if datos_confirmacion else {},

        # Estructura completa para el template de impresión
        'datos_confirmacion': datos_confirmacion_template,

        # Pre-llenado del formulario con datos previos guardados
        'datos_previos_json': json.dumps(datos_guardados) if datos_guardados else 'null',
        'confirmacion_estado': (ultima_calibracion.confirmacion_estado_aprobacion
                                if ultima_calibracion else None),
        'razon_rechazo': (ultima_calibracion.confirmacion_observaciones_rechazo
                          if ultima_calibracion else None),
    }

    return context


@monitor_view
@access_check
@login_required
@permission_required('core.can_view_calibracion', raise_exception=True)
def confirmacion_metrologica(request, equipo_id):
    """
    Vista para generar el documento de Confirmación Metrológica

    Extrae datos del equipo y calibraciones de la BD y los pasa al template
    Si se pasa calibracion_id por GET, usa esa calibración específica
    """
    if request.user.is_superuser:
        equipo = get_object_or_404(Equipo, id=equipo_id)
    else:
        equipo = get_object_or_404(Equipo, id=equipo_id, empresa=request.user.empresa)

    # Obtener calibración específica si se pasa por GET, sino la última
    calibracion_id = request.GET.get('calibracion_id')
    if calibracion_id:
        ultima_calibracion = get_object_or_404(
            Calibracion,
            id=calibracion_id,
            equipo=equipo
        )
    else:
        # Obtener última calibración
        ultima_calibracion = Calibracion.objects.filter(
            equipo=equipo
        ).order_by('-fecha_calibracion').first()

    # Preparar contexto usando función helper
    context = _preparar_contexto_confirmacion(request, equipo, ultima_calibracion)

    return render(request, 'core/confirmacion_metrologica.html', context)


def _calcular_deriva_variable(puntos_actual, puntos_anterior, emp_info, fecha_actual, fecha_anterior):
    """
    Calcula la deriva para UNA variable (lista de puntos de calibración actual vs anterior).
    Retorna dict con puntos_detalle como lista Python, o None si no hay puntos coincidentes.
    """
    if not puntos_actual or not puntos_anterior:
        return None
    dias = (fecha_actual - fecha_anterior).days
    meses = dias / 30.44
    if meses <= 0:
        return None

    emp_valor = emp_info['valor']
    emp_unidad = emp_info['unidad']

    puntos_coincidentes = []
    for p_actual in puntos_actual:
        nominal_actual = p_actual.get('nominal')
        if nominal_actual is None:
            continue
        mejor_match, mejor_dif = None, float('inf')
        for p_anterior in puntos_anterior:
            nominal_anterior = p_anterior.get('nominal')
            if nominal_anterior is None:
                continue
            dif_abs = abs(nominal_actual - nominal_anterior)
            dif_rel = dif_abs / abs(nominal_actual) if nominal_actual != 0 else dif_abs
            if dif_rel < mejor_dif and dif_rel <= 0.05:
                mejor_match = p_anterior
                mejor_dif = dif_rel
        if mejor_match:
            puntos_coincidentes.append({
                'nominal': nominal_actual,
                'desviacion_actual': p_actual.get('desviacion_abs', 0),
                'desviacion_anterior': mejor_match.get('desviacion_abs', 0),
                'cambio_desviacion': abs(p_actual.get('desviacion_abs', 0) - mejor_match.get('desviacion_abs', 0)),
            })

    if not puntos_coincidentes:
        return None

    punto_max_cambio = max(puntos_coincidentes, key=lambda p: p['cambio_desviacion'])

    for punto in puntos_coincidentes:
        nominal = punto['nominal']
        emp_pv = next((p.get('emp_valor') for p in puntos_actual
                       if p.get('nominal') is not None and
                       (abs(p['nominal'] - nominal) / abs(nominal) <= 0.05 if nominal != 0 else abs(p['nominal'] - nominal) < 1e-9)),
                      None)
        emp_pt = next((p.get('emp_tipo') for p in puntos_actual
                       if p.get('nominal') is not None and
                       (abs(p['nominal'] - nominal) / abs(nominal) <= 0.05 if nominal != 0 else abs(p['nominal'] - nominal) < 1e-9)),
                      None)
        if emp_pv is not None and emp_pt is not None:
            emp_punto = nominal * (emp_pv / 100) if emp_pt == '%' else emp_pv
        elif emp_unidad == '%':
            emp_punto = nominal * (emp_valor / 100)
        else:
            emp_punto = emp_valor

        punto['emp_punto'] = round(emp_punto, 4)
        deriva_p = punto['cambio_desviacion'] / meses
        punto['deriva_punto'] = round(deriva_p, 6)
        punto['intervalo_punto'] = round(emp_punto / deriva_p, 1) if deriva_p > 0 else None

        cambio = punto['cambio_desviacion']
        max_cambio = punto_max_cambio['cambio_desviacion']
        if cambio == max_cambio:
            punto['estado'] = 'MAYOR CAMBIO'; punto['es_maximo'] = True
        elif cambio > max_cambio * 0.7:
            punto['estado'] = 'ALTO'; punto['es_maximo'] = False
        elif cambio > max_cambio * 0.3:
            punto['estado'] = 'MODERADO'; punto['es_maximo'] = False
        else:
            punto['estado'] = 'BAJO'; punto['es_maximo'] = False

    puntos_con_i = [p for p in puntos_coincidentes if p.get('intervalo_punto') is not None]
    if puntos_con_i:
        punto_lim = min(puntos_con_i, key=lambda p: p['intervalo_punto'])
        for p in puntos_coincidentes:
            p['es_limitante'] = (p.get('intervalo_punto') == punto_lim['intervalo_punto'])
        intervalo_limitante = punto_lim['intervalo_punto']
    else:
        for p in puntos_coincidentes:
            p['es_limitante'] = False
        intervalo_limitante = None

    return {
        'fecha_anterior': fecha_anterior.strftime('%Y-%m-%d'),
        'fecha_actual': fecha_actual.strftime('%Y-%m-%d'),
        'meses_transcurridos': round(meses, 2),
        'desviacion_anterior': punto_max_cambio['desviacion_anterior'],
        'desviacion_actual': punto_max_cambio['desviacion_actual'],
        'cambio_desviacion': punto_max_cambio['cambio_desviacion'],
        'deriva_por_mes': round(punto_max_cambio['cambio_desviacion'] / meses, 6),
        'puntos_coincidentes': len(puntos_coincidentes),
        'nominal_referencia': punto_max_cambio['nominal'],
        'puntos_detalle': puntos_coincidentes,   # lista Python
        'intervalo_limitante': intervalo_limitante,
    }


@monitor_view
@access_check
@login_required
@permission_required('core.can_view_calibracion', raise_exception=True)
def intervalos_calibracion(request, equipo_id):
    """
    Vista para generar el documento de Intervalos de Calibración (Métodos ILAC G-24)

    Este será el segundo documento separado
    Si se pasa calibracion_id por GET, usa esa calibración como actual

    MEJORA: Reutiliza datos de Confirmación Metrológica si existe el PDF
    """
    if request.user.is_superuser:
        equipo = get_object_or_404(Equipo, id=equipo_id)
    else:
        equipo = get_object_or_404(Equipo, id=equipo_id, empresa=request.user.empresa)

    # Obtener calibración específica si se pasa por GET
    calibracion_id = request.GET.get('calibracion_id')
    if calibracion_id:
        cal_actual = get_object_or_404(
            Calibracion,
            id=calibracion_id,
            equipo=equipo
        )
        # Obtener la calibración anterior a esta
        cal_anterior = Calibracion.objects.filter(
            equipo=equipo,
            fecha_calibracion__lt=cal_actual.fecha_calibracion
        ).order_by('-fecha_calibracion').first()
    else:
        # Obtener últimas 2 calibraciones para cálculo de deriva
        calibraciones = Calibracion.objects.filter(
            equipo=equipo
        ).order_by('-fecha_calibracion')[:2]

        cal_actual = calibraciones[0] if len(calibraciones) > 0 else None
        cal_anterior = calibraciones[1] if len(calibraciones) > 1 else None

    # ==================== PARSEAR EMP ====================
    emp_info = {
        'valor': 8,  # Valor en formato de usuario (8 para 8%)
        'unidad': '%',
        'texto': '8%'
    }

    if equipo.error_maximo_permisible:
        emp_texto = equipo.error_maximo_permisible.strip()
        emp_match = re.search(r'([\d.]+)\s*(%|mm|lx|μm|°C|g|kg|m)?', emp_texto)
        if emp_match:
            emp_info['valor'] = float(emp_match.group(1))
            emp_info['unidad'] = emp_match.group(2) if emp_match.group(2) else ''
            emp_info['texto'] = emp_texto

            # NO dividir por 100 aquí - dejar el valor tal cual lo ingresó el usuario
            # La conversión se hace en JavaScript

    # ==================== VERIFICAR SI EXISTE CONFIRMACIÓN METROLÓGICA ====================
    tiene_confirmacion = False
    url_confirmacion_pdf = None

    if cal_actual and cal_actual.confirmacion_metrologica_pdf:
        tiene_confirmacion = True
        url_confirmacion_pdf = cal_actual.confirmacion_metrologica_pdf.url

    # ==================== LEER DATOS DE CONFIRMACIONES PARA DERIVA AUTOMÁTICA ====================
    datos_confirmacion_actual = None
    datos_confirmacion_anterior = None
    deriva_automatica = None

    if cal_actual and hasattr(cal_actual, 'confirmacion_metrologica_datos') and cal_actual.confirmacion_metrologica_datos:
        datos_confirmacion_actual = cal_actual.confirmacion_metrologica_datos

    if cal_anterior and hasattr(cal_anterior, 'confirmacion_metrologica_datos') and cal_anterior.confirmacion_metrologica_datos:
        datos_confirmacion_anterior = cal_anterior.confirmacion_metrologica_datos

    # Calcular deriva automáticamente si tenemos ambas confirmaciones
    derivas_por_variable = []   # resumen por variable para el template
    if datos_confirmacion_actual and datos_confirmacion_anterior:
        # Detectar v2 (multi-variable) o v1 (una variable)
        mags_act = datos_confirmacion_actual.get('magnitudes', [])
        mags_ant = datos_confirmacion_anterior.get('magnitudes', [])

        if mags_act and mags_ant:
            # v2: iterar sobre cada variable
            for mag_act in mags_act:
                nombre_var = mag_act.get('nombre', '') or ''
                unidad_var = mag_act.get('unidad', '') or ''
                pts_act = mag_act.get('puntos_medicion', [])
                # Buscar variable coincidente en la anterior por nombre; si no, usar la primera
                mag_ant = next((m for m in mags_ant if (m.get('nombre') or '') == nombre_var),
                               mags_ant[0] if mags_ant else None)
                pts_ant = mag_ant.get('puntos_medicion', []) if mag_ant else []
                resultado = _calcular_deriva_variable(
                    pts_act, pts_ant, emp_info,
                    cal_actual.fecha_calibracion, cal_anterior.fecha_calibracion
                )
                if resultado:
                    resultado['nombre'] = nombre_var
                    resultado['unidad'] = unidad_var
                    resultado['es_mas_restrictiva'] = False
                    derivas_por_variable.append(resultado)
        else:
            # v1: una sola variable
            pts_act = datos_confirmacion_actual.get('puntos_medicion', [])
            pts_ant = datos_confirmacion_anterior.get('puntos_medicion', [])
            resultado = _calcular_deriva_variable(
                pts_act, pts_ant, emp_info,
                cal_actual.fecha_calibracion, cal_anterior.fecha_calibracion
            )
            if resultado:
                resultado['nombre'] = ''
                resultado['unidad'] = ''
                resultado['es_mas_restrictiva'] = False
                derivas_por_variable.append(resultado)

        # La variable más restrictiva = menor intervalo limitante
        vars_con_i = [v for v in derivas_por_variable if v.get('intervalo_limitante') is not None]
        if vars_con_i:
            var_rest = min(vars_con_i, key=lambda v: v['intervalo_limitante'])
        elif derivas_por_variable:
            var_rest = derivas_por_variable[0]
        else:
            var_rest = None

        if var_rest:
            var_rest['es_mas_restrictiva'] = True
            # deriva_automatica mantiene el mismo formato (puntos_detalle como JSON string para JS)
            deriva_automatica = {
                **var_rest,
                'puntos_detalle': json.dumps(var_rest['puntos_detalle']),
            }

    # ==================== CALCULAR ERROR MÁXIMO PARA MÉTODO 1B ====================
    error_maximo_info = None
    puntos_metodo1b = []  # NUEVO: Lista de todos los puntos para tabla editable

    if datos_confirmacion_actual:
        # Soportar v2: agregar puntos de todas las variables
        mags_1b = datos_confirmacion_actual.get('magnitudes', [])
        if mags_1b:
            puntos = [p for m in mags_1b for p in m.get('puntos_medicion', [])]
        else:
            puntos = datos_confirmacion_actual.get('puntos_medicion', [])
        if puntos:
            # NUEVO: Buscar el punto con el porcentaje de EMP más alto (error/EMP)
            # Esto identifica el punto más crítico
            punto_max_porcentaje_emp = None
            max_porcentaje_emp = 0

            for punto in puntos:
                error_abs = abs(punto.get('error', 0))
                nominal = punto.get('nominal', 1)
                emp_valor = punto.get('emp_valor')
                emp_tipo = punto.get('emp_tipo')
                emp_absoluto = punto.get('emp_absoluto', 0)

                # Si no hay EMP absoluto pre-calculado, calcularlo
                if emp_absoluto == 0 and emp_valor and nominal != 0:
                    if emp_tipo == '%':
                        emp_absoluto = nominal * (emp_valor / 100)
                    else:
                        emp_absoluto = emp_valor

                # Calcular porcentaje del EMP
                porcentaje_emp = 0
                if emp_absoluto > 0:
                    porcentaje_emp = (error_abs / emp_absoluto) * 100
                    if porcentaje_emp > max_porcentaje_emp:
                        max_porcentaje_emp = porcentaje_emp
                        punto_max_porcentaje_emp = punto

                # Agregar punto a la lista para tabla editable
                puntos_metodo1b.append({
                    'nominal': nominal,
                    'error_absoluto': error_abs,
                    'emp_punto': emp_absoluto,
                    'porcentaje_emp': porcentaje_emp,
                    'es_critico': False  # Se marcará después
                })

            if punto_max_porcentaje_emp:
                error_abs = abs(punto_max_porcentaje_emp.get('error', 0))
                nominal = punto_max_porcentaje_emp.get('nominal', 1)

                error_maximo_info = {
                    'punto_nominal': nominal,
                    'error_absoluto': error_abs,
                    'porcentaje_emp': max_porcentaje_emp,
                    'emp_punto': punto_max_porcentaje_emp.get('emp_absoluto', 0)
                }

                # Marcar el punto crítico en la lista
                for p in puntos_metodo1b:
                    if p['nominal'] == nominal:
                        p['es_critico'] = True
                        break

    # ==================== CONTEXTO ====================
    total_calibraciones = Calibracion.objects.filter(equipo=equipo).count()
    context = {
        'equipo': equipo,
        'cal_actual': cal_actual,
        'cal_anterior': cal_anterior,
        'fecha_actual': datetime.now().date(),
        'emp_info': emp_info,

        # Datos para cálculos de intervalos
        'frecuencia_actual': equipo.frecuencia_calibracion_meses,
        'proxima_calibracion': equipo.proxima_calibracion,

        # NUEVO: Información de Confirmación Metrológica
        'tiene_confirmacion': tiene_confirmacion,
        'url_confirmacion_pdf': url_confirmacion_pdf,

        # NUEVO: Datos de confirmaciones para deriva automática
        'datos_confirmacion_actual': datos_confirmacion_actual,
        'datos_confirmacion_anterior': datos_confirmacion_anterior,
        'deriva_automatica': deriva_automatica,
        # Tabla resumen por variable (solo cuando hay múltiples variables)
        'derivas_por_variable': derivas_por_variable if len(derivas_por_variable) > 1 else [],

        # NUEVO: Error máximo para Método 1B
        'error_maximo_info': error_maximo_info,
        'puntos_metodo1b': json.dumps(puntos_metodo1b),  # Serializar para JavaScript
        'total_calibraciones': total_calibraciones,

        # Metadatos para el PDF - usar campos específicos de INTERVALOS
        'nombre_empresa': equipo.empresa.nombre,
        'logo_empresa_url': equipo.empresa.logo_empresa.url if equipo.empresa.logo_empresa else None,
        'formato_codigo': equipo.empresa.intervalos_codigo or 'SAM-INT-001',
        'formato_version': equipo.empresa.intervalos_version or '01',
        'formato_fecha': equipo.empresa.intervalos_fecha_formato or None,
        'formato_fecha_display': equipo.empresa.intervalos_fecha_formato_display or (equipo.empresa.intervalos_fecha_formato.strftime('%Y-%m-%d') if equipo.empresa.intervalos_fecha_formato else ''),
    }

    return render(request, 'core/intervalos_calibracion.html', context)


@monitor_view
@access_check
@login_required
@trial_check
@permission_required('core.can_change_calibracion', raise_exception=True)
def generar_pdf_confirmacion(request, equipo_id):
    """
    Genera PDF de la confirmación metrológica Y lo guarda en la calibración específica

    Recibe datos JSON del template via POST:
    - puntos_medicion: Array de objetos con {nominal, lectura, incertidumbre, error, conformidad}
    - regla_decision: String con la regla ILAC G8 seleccionada
    - checklist: Objeto con los items verificados
    - metodo_intervalo: Datos del método de intervalos seleccionado

    Si se pasa calibracion_id por GET, usa esa calibración específica
    """
    from django.template.loader import render_to_string
    from django.core.files.base import ContentFile
    from django.contrib import messages
    import json

    if request.user.is_superuser:
        equipo = get_object_or_404(Equipo, id=equipo_id)
    else:
        equipo = get_object_or_404(Equipo, id=equipo_id, empresa=request.user.empresa)

    # Obtener calibración específica si se pasa por GET, sino la última
    calibracion_id = request.GET.get('calibracion_id')
    if calibracion_id:
        ultima_calibracion = get_object_or_404(
            Calibracion,
            id=calibracion_id,
            equipo=equipo
        )
    else:
        # Obtener última calibración
        ultima_calibracion = Calibracion.objects.filter(
            equipo=equipo
        ).order_by('-fecha_calibracion').first()

    if not ultima_calibracion:
        messages.error(request, "No hay calibraciones registradas para generar confirmación metrológica")
        return redirect('core:detalle_equipo', pk=equipo_id)

    # Si es GET y ya existe PDF guardado, servirlo directamente
    if request.method == 'GET' and calibracion_id and ultima_calibracion.confirmacion_metrologica_pdf:
        try:
            pdf_file = ultima_calibracion.confirmacion_metrologica_pdf.read()
            response = HttpResponse(pdf_file, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="confirmacion_{equipo.codigo_interno}.pdf"'
            return response
        except Exception as e:
            logger.error(f"Error al servir PDF existente: {e}")
            # Si falla, continuar con la generación

    # Si es POST, recibir datos del formulario
    datos_confirmacion = {}
    if request.method == 'POST' and request.content_type == 'application/json':
        datos_confirmacion = json.loads(request.body)

        # ============ GUARDAR FORMATO EN EMPRESA ============
        # Si vienen datos de formato en el POST, actualizar la empresa
        if 'formato' in datos_confirmacion:
            formato_data = datos_confirmacion['formato']
            empresa = equipo.empresa

            # Actualizar campos específicos de CONFIRMACIÓN METROLÓGICA de la empresa
            if 'codigo' in formato_data:
                empresa.confirmacion_codigo = formato_data['codigo']
            if 'version' in formato_data:
                empresa.confirmacion_version = formato_data['version']
            if 'fecha' in formato_data and formato_data['fecha']:
                fecha_str = formato_data['fecha'].strip()
                # Guardar el campo _display con el formato original (YYYY-MM o YYYY-MM-DD)
                empresa.confirmacion_fecha_formato_display = fecha_str
                # Convertir string de fecha a objeto date para el DateField
                from datetime import datetime as dt
                import re
                try:
                    if re.match(r'^\d{4}-\d{2}$', fecha_str):
                        # Formato YYYY-MM: agregar día 01
                        empresa.confirmacion_fecha_formato = dt.strptime(fecha_str + '-01', '%Y-%m-%d').date()
                    else:
                        # Formato YYYY-MM-DD
                        empresa.confirmacion_fecha_formato = dt.strptime(fecha_str, '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    pass  # Si hay error en el formato, mantener valor actual

            empresa.save()

    # Preparar contexto (igual que confirmacion_metrologica pero con datos del POST)
    context = _preparar_contexto_confirmacion(request, equipo, ultima_calibracion, datos_confirmacion)

    # ============ GENERAR GRÁFICA(S) CON MATPLOTLIB ============
    es_v2 = datos_confirmacion and 'magnitudes' in datos_confirmacion
    if es_v2:
        # v2: una gráfica por magnitud; la incrustamos en cada magnitud del template
        mags_template = context['datos_confirmacion'].get('magnitudes', [])
        graficas = []
        for i, mag in enumerate(datos_confirmacion['magnitudes']):
            puntos_mag = mag.get('puntos_medicion', [])
            emp_valor_mag = safe_float(mag.get('emp', 0), 0)
            emp_unidad_mag = mag.get('emp_unidad', '%')
            unidad_mag = mag.get('unidad', datos_confirmacion.get('unidad_equipo', ''))
            g = _generar_grafica_confirmacion(puntos_mag, emp_valor_mag, emp_unidad_mag, unidad_mag)
            graficas.append(g)
            # Embeber gráfica en la magnitud del template para acceso fácil
            if i < len(mags_template):
                mags_template[i]['grafica'] = g
        context['graficas'] = graficas
        context['grafica_imagen'] = graficas[0] if graficas else None  # compatibilidad v1
    elif datos_confirmacion and 'puntos_medicion' in datos_confirmacion:
        # v1: una sola gráfica
        puntos = datos_confirmacion['puntos_medicion']
        emp_valor = safe_float(datos_confirmacion.get('emp') or context['datos_confirmacion']['emp'], 0)
        emp_unidad = datos_confirmacion.get('emp_unidad', context['datos_confirmacion']['emp_unidad'])
        unidad_equipo = datos_confirmacion.get('unidad_equipo', context['datos_confirmacion']['unidad_equipo'])
        grafica_base64 = _generar_grafica_confirmacion(puntos, emp_valor, emp_unidad, unidad_equipo)
        context['grafica_imagen'] = grafica_base64
        context['graficas'] = [grafica_base64]
        # Embeber en la única magnitud del template
        mags_template = context['datos_confirmacion'].get('magnitudes', [])
        if mags_template:
            mags_template[0]['grafica'] = grafica_base64
    else:
        context['grafica_imagen'] = None
        context['graficas'] = []

    # Renderizar HTML
    html_string = render_to_string('core/confirmacion_metrologica_print.html', context)

    # Generar PDF con WeasyPrint
    try:
        from weasyprint import HTML, CSS
        from weasyprint.text.fonts import FontConfiguration

        font_config = FontConfiguration()
        html_pdf = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
        pdf_file = html_pdf.write_pdf(font_config=font_config)

        # ============ GUARDAR DATOS JSON PARA CÁLCULO DE DERIVA ============
        def _procesar_puntos(puntos):
            """Normaliza y procesa una lista de puntos de medición."""
            desviacion_maxima = 0
            puntos_procesados = []
            for punto in puntos:
                nominal = safe_float(punto.get('nominal', 0), 0)
                error = safe_float(punto.get('error', 0), 0)
                desviacion_abs = error
                if abs(desviacion_abs) > desviacion_maxima:
                    desviacion_maxima = abs(desviacion_abs)
                lectura_punto = safe_float(punto.get('lectura', 0), 0)
                factor_correccion = (nominal / lectura_punto) if lectura_punto != 0 else 0
                p = {
                    'nominal': nominal,
                    'lectura': lectura_punto,
                    'incertidumbre': safe_float(punto.get('incertidumbre', 0), 0),
                    'error': error,
                    'factor_correccion': factor_correccion,
                    'error_mas_u': safe_float(punto.get('error_mas_u', 0), 0),
                    'error_menos_u': safe_float(punto.get('error_menos_u', 0), 0),
                    'conformidad': punto.get('conformidad', 'Pendiente'),
                    'desviacion_abs': desviacion_abs,
                }
                if punto.get('emp_valor') is not None:
                    p['emp_valor'] = safe_float(punto['emp_valor'], 0)
                if punto.get('emp_tipo') is not None:
                    p['emp_tipo'] = punto['emp_tipo']
                if punto.get('emp_absoluto') is not None:
                    p['emp_absoluto'] = safe_float(punto['emp_absoluto'], 0)
                puntos_procesados.append(p)
            return puntos_procesados, desviacion_maxima

        campos_comunes = {
            'fecha_confirmacion': datetime.now().strftime('%Y-%m-%d'),
            'regla_decision': datos_confirmacion.get('regla_decision', 'guard_band_U'),
            'decision': datos_confirmacion.get('conclusion', {}).get('decision', 'Pendiente'),
            'responsable': datos_confirmacion.get('conclusion', {}).get('responsable', request.user.get_full_name() or request.user.username),
            'laboratorio': datos_confirmacion.get('laboratorio', ''),
            'fecha_certificado': datos_confirmacion.get('fecha_certificado', ''),
            'numero_certificado': datos_confirmacion.get('numero_certificado', ''),
            'conclusion': datos_confirmacion.get('conclusion', {
                'decision': 'Pendiente',
                'observaciones': '',
                'responsable': request.user.get_full_name() or request.user.username
            }),
        }

        if datos_confirmacion and 'magnitudes' in datos_confirmacion:
            # ── Formato v2: múltiples magnitudes ──
            magnitudes_procesadas = []
            desviacion_maxima_global = 0
            for mag in datos_confirmacion['magnitudes']:
                puntos_mag, desv_mag = _procesar_puntos(mag.get('puntos_medicion', []))
                if desv_mag > desviacion_maxima_global:
                    desviacion_maxima_global = desv_mag
                magnitudes_procesadas.append({
                    'nombre': mag.get('nombre', ''),
                    'unidad': mag.get('unidad', ''),
                    'emp': safe_float(mag.get('emp', 0), 0),
                    'emp_unidad': mag.get('emp_unidad', '%'),
                    'puntos_medicion': puntos_mag,
                    'resultado': 'APTO' if all(
                        p.get('conformidad', '') in ('Cumple', 'CUMPLE') for p in puntos_mag
                    ) else 'NO APTO',
                })
            # Primera magnitud como referencia legacy (usada por intervalos de calibración)
            primera = magnitudes_procesadas[0] if magnitudes_procesadas else {}
            ultima_calibracion.confirmacion_metrologica_datos = {
                **campos_comunes,
                'version': 2,
                'magnitudes': magnitudes_procesadas,
                'desviacion_maxima': desviacion_maxima_global,
                # Campos legacy (primera magnitud) para compatibilidad con intervalos de calibración
                'puntos_medicion': primera.get('puntos_medicion', []),
                'emp_valor': primera.get('emp', 0),
                'emp': primera.get('emp', 0),
                'emp_unidad': primera.get('emp_unidad', '%'),
                'unidad_equipo': primera.get('unidad', datos_confirmacion.get('unidad_equipo', '')),
            }
        elif datos_confirmacion and 'puntos_medicion' in datos_confirmacion:
            # ── Formato v1: magnitud única ──
            puntos_procesados, desviacion_maxima = _procesar_puntos(datos_confirmacion['puntos_medicion'])
            ultima_calibracion.confirmacion_metrologica_datos = {
                **campos_comunes,
                'puntos_medicion': puntos_procesados,
                'desviacion_maxima': desviacion_maxima,
                'emp_valor': safe_float(datos_confirmacion.get('emp', 0), 0),
                'emp': safe_float(datos_confirmacion.get('emp', 0), 0),
                'emp_unidad': datos_confirmacion.get('emp_unidad', '%'),
                'unidad_equipo': datos_confirmacion.get('unidad_equipo', ''),
            }

        # GUARDAR EN BD - Campo confirmacion_metrologica_pdf de Calibracion
        filename = f'confirmacion_metrologica_{equipo.codigo_interno}_{ultima_calibracion.fecha_calibracion.strftime("%Y%m%d")}.pdf'
        ultima_calibracion.confirmacion_metrologica_pdf.save(
            filename,
            ContentFile(pdf_file),
            save=False  # No guardar aún
        )

        # ============ SISTEMA DE APROBACIÓN - CONFIRMACIÓN ============
        # Establecer creado_por y estado pendiente para CONFIRMACIÓN
        ultima_calibracion.creado_por = request.user
        ultima_calibracion.confirmacion_estado_aprobacion = 'pendiente'
        ultima_calibracion.confirmacion_aprobado_por = None
        ultima_calibracion.confirmacion_fecha_aprobacion = None
        ultima_calibracion.confirmacion_observaciones_rechazo = None

        # ============ REGISTRAR EN OBSERVACIONES DE CALIBRACIÓN ============
        # DESHABILITADO: Las observaciones se diligencian manualmente por el cliente
        # observacion_confirmacion = f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Confirmación Metrológica generada por {request.user.get_full_name() or request.user.username}. Decisión: {datos_confirmacion.get('conclusion', {}).get('decision', 'Pendiente')}"

        # if ultima_calibracion.observaciones:
        #     ultima_calibracion.observaciones += observacion_confirmacion
        # else:
        #     ultima_calibracion.observaciones = observacion_confirmacion.strip()

        ultima_calibracion.save()

        messages.success(request, f"✅ PDF de Confirmación Metrológica generado y guardado exitosamente. Actividad registrada.")

        # Retornar JSON con éxito para que JavaScript redirija
        from django.http import JsonResponse
        from django.urls import reverse
        return JsonResponse({
            'success': True,
            'message': 'PDF generado y actividad registrada exitosamente',
            'redirect_url': reverse('core:detalle_equipo', kwargs={'pk': equipo.id})
        })

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"Error generando PDF: {error_detail}")

        from django.http import JsonResponse
        return JsonResponse({
            'success': False,
            'message': f'Error al generar PDF: {str(e)}'
        }, status=500)


@monitor_view
@access_check
@login_required
@trial_check
@permission_required('core.can_change_calibracion', raise_exception=True)
@safe_pdf_response
def generar_pdf_intervalos(request, equipo_id):
    """
    Genera PDF de intervalos de calibración Y actualiza automáticamente:
    - equipo.frecuencia_calibracion_meses
    - equipo.proxima_calibracion
    - calibracion.intervalos_calibracion_pdf

    Recibe datos JSON del template via POST:
    - metodo_seleccionado: Método ILAC G-24 aplicado (metodo1, metodo2, metodo3, manual)
    - nuevo_intervalo_meses: Nuevo intervalo calculado en meses
    - justificacion: Justificación técnica de la decisión
    - responsable: Nombre del responsable de la decisión
    - fecha_decision: Fecha de la decisión
    - metodo1_resultado, metodo2_deriva, metodo3_horas: Datos de cada método
    """
    from django.template.loader import render_to_string
    from django.core.files.base import ContentFile
    from django.contrib import messages
    from django.http import JsonResponse
    from django.urls import reverse
    from dateutil.relativedelta import relativedelta
    import json
    import logging

    logger = logging.getLogger(__name__)

    logger.info(f"=== INICIO generar_pdf_intervalos ===")
    logger.info(f"User: {request.user.username} (ID: {request.user.id})")
    logger.info(f"Equipo ID: {equipo_id}")
    logger.info(f"Method: {request.method}")
    logger.info(f"Content-Type: {request.content_type}")

    if request.user.is_superuser:
        equipo = get_object_or_404(Equipo, id=equipo_id)
    else:
        equipo = get_object_or_404(Equipo, id=equipo_id, empresa=request.user.empresa)

    logger.info(f"User.empresa: {request.user.empresa} (ID: {request.user.empresa.id if request.user.empresa else None})")
    logger.info(f"Equipo.empresa: {equipo.empresa} (ID: {equipo.empresa.id if equipo.empresa else None})")
    logger.info(f"User.is_superuser: {request.user.is_superuser}")

    # Obtener calibración específica si se pasa por GET, sino la última
    calibracion_id = request.GET.get('calibracion_id')
    if calibracion_id:
        calibracion_actual = get_object_or_404(
            Calibracion,
            id=calibracion_id,
            equipo=equipo
        )
    else:
        calibracion_actual = Calibracion.objects.filter(
            equipo=equipo
        ).order_by('-fecha_calibracion').first()

    if not calibracion_actual:
        return JsonResponse({
            'success': False,
            'message': 'No hay calibraciones registradas para generar intervalos de calibración'
        }, status=400)

    # Si es GET y ya existe PDF guardado, servirlo directamente
    if request.method == 'GET' and calibracion_id and calibracion_actual.intervalos_calibracion_pdf:
        try:
            pdf_file = calibracion_actual.intervalos_calibracion_pdf.read()
            response = HttpResponse(pdf_file, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="intervalos_{equipo.codigo_interno}.pdf"'
            return response
        except Exception as e:
            logger.error(f"Error al servir PDF existente: {e}")
            # Si falla, continuar con la generación

    # Si es POST, recibir datos del formulario (usando FormData)
    datos_json = request.POST.get('datos_intervalos')
    if datos_json:
        datos_intervalos = json.loads(datos_json)
        logger.info(f"Datos intervalos recibidos: {len(datos_intervalos)} campos")
    else:
        datos_intervalos = {}
        logger.warning("No se recibieron datos de intervalos en el POST")

    # Obtener calibración anterior para el contexto
    cal_anterior = Calibracion.objects.filter(
        equipo=equipo,
        fecha_calibracion__lt=calibracion_actual.fecha_calibracion
    ).order_by('-fecha_calibracion').first()

    # ==================== PARSEAR EMP ====================
    emp_info = {
        'valor': 8,
        'unidad': '%',
        'texto': '8%'
    }

    if equipo.error_maximo_permisible:
        emp_texto = equipo.error_maximo_permisible.strip()
        emp_match = re.search(r'([\d.]+)\s*(%|mm|lx|μm|°C|g|kg|m)?', emp_texto)
        if emp_match:
            emp_info['valor'] = float(emp_match.group(1))
            emp_info['unidad'] = emp_match.group(2) if emp_match.group(2) else ''
            emp_info['texto'] = emp_texto

    # Obtener deriva automática para incluir en PDF (siempre que haya datos de confirmación)
    deriva_automatica_pdf = None
    derivas_por_variable_pdf = []
    if (cal_anterior and
            hasattr(calibracion_actual, 'confirmacion_metrologica_datos') and calibracion_actual.confirmacion_metrologica_datos and
            hasattr(cal_anterior, 'confirmacion_metrologica_datos') and cal_anterior.confirmacion_metrologica_datos):
        datos_actual_pdf = calibracion_actual.confirmacion_metrologica_datos
        datos_anterior_pdf = cal_anterior.confirmacion_metrologica_datos

        mags_act_pdf = datos_actual_pdf.get('magnitudes', [])
        mags_ant_pdf = datos_anterior_pdf.get('magnitudes', [])

        if mags_act_pdf and mags_ant_pdf:
            for mag_act in mags_act_pdf:
                nombre_var = mag_act.get('nombre', '') or ''
                unidad_var = mag_act.get('unidad', '') or ''
                pts_act = mag_act.get('puntos_medicion', [])
                mag_ant = next((m for m in mags_ant_pdf if (m.get('nombre') or '') == nombre_var),
                               mags_ant_pdf[0] if mags_ant_pdf else None)
                pts_ant = mag_ant.get('puntos_medicion', []) if mag_ant else []
                resultado = _calcular_deriva_variable(
                    pts_act, pts_ant, emp_info,
                    calibracion_actual.fecha_calibracion, cal_anterior.fecha_calibracion
                )
                if resultado:
                    resultado['nombre'] = nombre_var
                    resultado['unidad'] = unidad_var
                    resultado['es_mas_restrictiva'] = False
                    derivas_por_variable_pdf.append(resultado)
        else:
            pts_act = datos_actual_pdf.get('puntos_medicion', [])
            pts_ant = datos_anterior_pdf.get('puntos_medicion', [])
            resultado = _calcular_deriva_variable(
                pts_act, pts_ant, emp_info,
                calibracion_actual.fecha_calibracion, cal_anterior.fecha_calibracion
            )
            if resultado:
                resultado['nombre'] = ''
                resultado['unidad'] = ''
                resultado['es_mas_restrictiva'] = False
                derivas_por_variable_pdf.append(resultado)

        vars_con_i_pdf = [v for v in derivas_por_variable_pdf if v.get('intervalo_limitante') is not None]
        if vars_con_i_pdf:
            var_rest_pdf = min(vars_con_i_pdf, key=lambda v: v['intervalo_limitante'])
        elif derivas_por_variable_pdf:
            var_rest_pdf = derivas_por_variable_pdf[0]
        else:
            var_rest_pdf = None

        if var_rest_pdf:
            var_rest_pdf['es_mas_restrictiva'] = True
            deriva_automatica_pdf = {
                **var_rest_pdf,
                'puntos_detalle': var_rest_pdf['puntos_detalle'],  # lista para el template PDF
            }

    # Obtener logo de empresa de forma segura
    logo_empresa_url = None
    try:
        if equipo.empresa and equipo.empresa.logo_empresa:
            logo_empresa_url = equipo.empresa.logo_empresa.url
    except Exception as logo_error:
        logger = logging.getLogger(__name__)
        logger.warning(f"No se pudo obtener logo de empresa: {logo_error}")
        logo_empresa_url = None

    # Formatear fecha del formato si existe
    # IMPORTANTE: Respetar el campo _display que puede ser YYYY-MM o YYYY-MM-DD
    formato_fecha_formateada_int = None
    # Primero intentar usar el campo _display que preserva el formato original
    if equipo.empresa.intervalos_fecha_formato_display:
        formato_fecha_formateada_int = equipo.empresa.intervalos_fecha_formato_display
        datos_intervalos.setdefault('formato', {})['fecha'] = formato_fecha_formateada_int
    elif datos_intervalos.get('formato', {}).get('fecha'):
        # Usar el valor existente sin forzar formato
        formato_fecha_formateada_int = datos_intervalos['formato']['fecha']

    # Preparar contexto para el PDF
    context = {
        'equipo': equipo,
        'cal_actual': calibracion_actual,
        'cal_anterior': cal_anterior,
        'fecha_actual': datetime.now().date(),
        'nombre_empresa': equipo.empresa.nombre,
        'logo_empresa_url': logo_empresa_url,
        'emp_info': emp_info,

        # Pasar todos los datos_intervalos al template
        'datos_intervalos': datos_intervalos,

        # Pasar deriva automática para tabla detallada en PDF
        'deriva_automatica': deriva_automatica_pdf,
        'derivas_por_variable': derivas_por_variable_pdf if len(derivas_por_variable_pdf) > 1 else [],
        'total_calibraciones': Calibracion.objects.filter(equipo=equipo).count(),
        'emp_texto': equipo.error_maximo_permisible or f"{emp_info['valor']} {emp_info['unidad']}",
    }

    # Renderizar HTML
    html_string = render_to_string('core/intervalos_calibracion_print.html', context)

    # Generar PDF con WeasyPrint
    try:
        from weasyprint import HTML
        from weasyprint.text.fonts import FontConfiguration

        font_config = FontConfiguration()
        html_pdf = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
        pdf_file = html_pdf.write_pdf(font_config=font_config)

        # ============ ACTUALIZAR INTERVALO AUTOMÁTICAMENTE (ANTES DE GUARDAR PDF) ============
        nuevo_intervalo = safe_float(datos_intervalos.get('intervalo_definitivo', equipo.frecuencia_calibracion_meses or 12), 12)
        fecha_base = calibracion_actual.fecha_calibracion

        equipo.frecuencia_calibracion_meses = nuevo_intervalo
        # Usar la función helper para manejar decimales correctamente (ej: 60.0 meses, 1.5 meses, etc.)
        nueva_proxima_calibracion = fecha_base + meses_decimales_a_relativedelta(nuevo_intervalo)
        equipo.proxima_calibracion = nueva_proxima_calibracion

        # Usar update_fields para evitar que el método save() recalcule automáticamente las fechas
        equipo.save(update_fields=['frecuencia_calibracion_meses', 'proxima_calibracion'])

        # ============ GUARDAR PDF EN CALIBRACIÓN (CON SIGNAL DESHABILITADO) ============
        # IMPORTANTE: Guardamos el PDF DESPUÉS de actualizar el equipo
        # y deshabilitamos temporalmente el signal para evitar que sobrescriba nuestros valores
        from django.db.models.signals import post_save
        from core.models import update_equipo_calibracion_info

        post_save.disconnect(update_equipo_calibracion_info, sender=Calibracion)

        try:
            filename = f'intervalos_calibracion_{equipo.codigo_interno}_{calibracion_actual.fecha_calibracion.strftime("%Y%m%d")}.pdf'
            calibracion_actual.intervalos_calibracion_pdf.save(
                filename,
                ContentFile(pdf_file),
                save=False  # No guardar aún
            )

            # ============ GUARDAR DATOS DE INTERVALOS PARA REGENERACIÓN ============
            calibracion_actual.intervalos_calibracion_datos = datos_intervalos

            # ============ SISTEMA DE APROBACIÓN ============
            # Establecer creado_por y estado pendiente para INTERVALOS
            calibracion_actual.creado_por = request.user
            calibracion_actual.intervalos_estado_aprobacion = 'pendiente'
            calibracion_actual.intervalos_aprobado_por = None
            calibracion_actual.intervalos_fecha_aprobacion = None
            calibracion_actual.intervalos_observaciones_rechazo = None

            # Ahora sí guardar
            calibracion_actual.save()
        finally:
            # Reactivar el signal
            post_save.connect(update_equipo_calibracion_info, sender=Calibracion)

        # ============ REGISTRAR EN OBSERVACIONES DE CALIBRACIÓN ============
        metodo_nombre = {
            'manual': 'Método Manual',
            'metodo1a': 'Método 1A - Escalera (IC Regular)',
            'metodo1b': 'Método 1B - Escalera (Ajuste por Conformidad)',
            'metodo2': 'Método 2 - Carta de Control (Tiempo Calendario)',
            'metodo3': 'Método 3 - Tiempo en Uso'
        }.get(datos_intervalos.get('metodo_seleccionado', 'manual'), 'Método no especificado')

        # DESHABILITADO: Las observaciones se diligencian manualmente por el cliente
        # observacion_intervalos = f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Intervalos de Calibración generados por {request.user.get_full_name() or request.user.username}. Método: {metodo_nombre}. Nuevo intervalo: {nuevo_intervalo} meses."

        # if calibracion_actual.observaciones:
        #     calibracion_actual.observaciones += observacion_intervalos
        # else:
        #     calibracion_actual.observaciones = observacion_intervalos.strip()

        calibracion_actual.save()

        # Retornar JSON con éxito
        return JsonResponse({
            'success': True,
            'message': f'PDF generado exitosamente. Intervalo actualizado a {nuevo_intervalo} meses. Próxima calibración: {equipo.proxima_calibracion.strftime("%Y-%m-%d")}',
            'redirect_url': reverse('core:detalle_equipo', kwargs={'pk': equipo.id})
        })

    except Exception as e:
        import traceback
        import logging
        error_detail = traceback.format_exc()
        logger = logging.getLogger(__name__)
        logger.error(f"Error generando PDF de intervalos: {error_detail}")

        return JsonResponse({
            'success': False,
            'message': f'Error al generar PDF: {str(e)}'
        }, status=500)


@monitor_view
@access_check
@login_required
@trial_check
@permission_required('core.can_change_calibracion', raise_exception=True)
def guardar_confirmacion(request, equipo_id):
    """
    Guarda los resultados de la confirmación metrológica en la BD

    Recibe datos del formulario vía POST y actualiza:
    - Campo confirmacion_metrologica_pdf en la última Calibracion
    - Opcionalmente crea un nuevo modelo ConfirmacionMetrologica
    """
    if request.method != 'POST':
        return redirect('core:confirmacion_metrologica', equipo_id=equipo_id)

    if request.user.is_superuser:
        equipo = get_object_or_404(Equipo, id=equipo_id)
    else:
        equipo = get_object_or_404(Equipo, id=equipo_id, empresa=request.user.empresa)

    # Obtener última calibración
    ultima_cal = Calibracion.objects.filter(equipo=equipo).order_by('-fecha_calibracion').first()

    if not ultima_cal:
        return HttpResponse("No hay calibraciones para este equipo", status=400)

    # Aquí procesarías los datos del POST
    # Por ejemplo: puntos de medición, resultado de conformidad, etc.

    # TODO: Implementar lógica de guardado
    # - Crear modelo ConfirmacionMetrologica
    # - Guardar puntos de medición
    # - Generar PDF y guardarlo en ultima_cal.confirmacion_metrologica_pdf

    return redirect('core:detalle_equipo', pk=equipo_id)


@monitor_view
@access_check
@login_required
@trial_check
def actualizar_formato_empresa(request):
    """
    Actualiza la información del formato (código, versión, fecha) de la empresa.
    Estos cambios se aplican a todos los equipos de la empresa.

    Requiere parámetro 'tipo' en el JSON para especificar qué formato actualizar:
    - 'intervalos': Actualiza intervalos_codigo, intervalos_version, intervalos_fecha_formato
    - 'mantenimiento': Actualiza mantenimiento_codigo, mantenimiento_version, mantenimiento_fecha_formato
    - 'confirmacion': Actualiza confirmacion_codigo, confirmacion_version, confirmacion_fecha_formato
    - 'comprobacion': Actualiza comprobacion_codigo, comprobacion_version, comprobacion_fecha_formato
    """
    from django.http import JsonResponse
    from core.models import Empresa
    import json
    from datetime import datetime

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)

    try:
        # RESTRICCIÓN: Solo Admin y Gerente pueden cambiar formatos
        if request.user.rol_usuario == 'TECNICO':
            return JsonResponse({
                'success': False,
                'message': 'Solo Administradores y Gerentes pueden modificar los formatos'
            }, status=403)

        datos = json.loads(request.body)

        # Obtener la empresa del usuario
        empresa = request.user.empresa
        if not empresa:
            return JsonResponse({'success': False, 'message': 'Usuario no tiene empresa asociada'}, status=400)

        # Determinar qué tipo de formato actualizar
        tipo = datos.get('tipo', 'intervalos')  # Default a intervalos por compatibilidad

        # Mapeo de campos según el tipo
        campos_map = {
            'intervalos': {
                'codigo': 'intervalos_codigo',
                'version': 'intervalos_version',
                'fecha': 'intervalos_fecha_formato'
            },
            'mantenimiento': {
                'codigo': 'mantenimiento_codigo',
                'version': 'mantenimiento_version',
                'fecha': 'mantenimiento_fecha_formato'
            },
            'confirmacion': {
                'codigo': 'confirmacion_codigo',
                'version': 'confirmacion_version',
                'fecha': 'confirmacion_fecha_formato'
            },
            'comprobacion': {
                'codigo': 'comprobacion_codigo',
                'version': 'comprobacion_version',
                'fecha': 'comprobacion_fecha_formato'
            }
        }

        if tipo not in campos_map:
            return JsonResponse({'success': False, 'message': f'Tipo de formato inválido: {tipo}'}, status=400)

        campos = campos_map[tipo]

        # Actualizar los campos específicos del tipo de formato
        if 'codigo' in datos and datos['codigo']:
            setattr(empresa, campos['codigo'], datos['codigo'])

        if 'version' in datos and datos['version']:
            setattr(empresa, campos['version'], datos['version'])

        if 'fecha' in datos:
            try:
                # Convertir string de fecha a objeto date
                fecha_str = datos['fecha']
                if fecha_str:
                    fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                    setattr(empresa, campos['fecha'], fecha_obj)
                else:
                    setattr(empresa, campos['fecha'], None)
            except (ValueError, TypeError):
                pass  # Si hay error en la fecha, no actualizar

        empresa.save()

        # Obtener valores actualizados para respuesta
        codigo_actual = getattr(empresa, campos['codigo']) or ''
        version_actual = getattr(empresa, campos['version']) or ''
        fecha_actual = getattr(empresa, campos['fecha'])
        fecha_str = fecha_actual.strftime('%Y-%m-%d') if fecha_actual else ''

        return JsonResponse({
            'success': True,
            'message': f'Formato de {tipo} actualizado correctamente para todos los equipos de la empresa',
            'datos': {
                'codigo': codigo_actual,
                'version': version_actual,
                'fecha': fecha_str,
                'tipo': tipo
            }
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error al actualizar formato: {str(e)}'
        }, status=500)
