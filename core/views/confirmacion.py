# core/views/confirmacion.py
"""
Vistas para Confirmación Metrológica e Intervalos de Calibración
Integrado con datos reales de la base de datos
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
from core.models import Equipo, Calibracion, meses_decimales_a_relativedelta
from core.decorators_pdf import safe_pdf_response
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
    Genera una gráfica de confirmación metrológica usando matplotlib
    ACTUALIZADO: Usa EMPs por punto si están disponibles en los datos

    Returns:
        str: Imagen en base64 para incluir en HTML
    """
    try:
        # Filtrar puntos válidos: deben tener nominal y (error O lectura)
        # Si tienen lectura pero no error, calcularemos el error
        puntos_validos = [p for p in puntos_medicion
                         if p.get('nominal') and (p.get('error') is not None or p.get('lectura') is not None)]

        if not puntos_validos:
            return None

        # Extraer datos y calcular error si no existe
        nominales = [safe_float(p.get('nominal', 0), 0) for p in puntos_validos]

        # Calcular errores: usar error si existe, sino calcular de lectura - nominal
        errores = []
        for p in puntos_validos:
            if p.get('error') is not None:
                errores.append(safe_float(p.get('error', 0), 0))
            elif p.get('lectura') is not None:
                nominal = safe_float(p.get('nominal', 0), 0)
                lectura = safe_float(p.get('lectura', 0), 0)
                error = lectura - nominal
                errores.append(error)
            else:
                errores.append(0)

        # Calcular medidos: medido = nominal + error
        medidos = [n + e for n, e in zip(nominales, errores)]
        incertidumbres = [safe_float(p.get('incertidumbre', 0), 0) for p in puntos_validos]

        # NUEVO: Verificar si hay EMPs por punto
        tiene_emp_por_punto = all(p.get('emp_absoluto') is not None for p in puntos_validos)

        # Determinar si EMP es porcentaje (del primer punto o global)
        if tiene_emp_por_punto and puntos_validos[0].get('emp_tipo'):
            emp_es_porcentaje = (puntos_validos[0].get('emp_tipo') == '%')
        else:
            emp_es_porcentaje = (emp_unidad == '%')

        # Crear figura
        fig, ax = plt.subplots(figsize=(10, 6))

        if emp_es_porcentaje:
            # NORMALIZAR: Dividir medido / nominal para que quede cerca de 1
            valores_normalizados = [m / n if n != 0 else 1 for m, n in zip(medidos, nominales)]

            # Normalizar incertidumbres también
            incertidumbres_norm = [inc / n if n != 0 else 0 for inc, n in zip(incertidumbres, nominales)]

            # Dibujar línea normalizada con barras de incertidumbre
            ax.errorbar(nominales, valores_normalizados, yerr=incertidumbres_norm,
                       fmt='o-', color='#3b82f6', linewidth=2, markersize=8,
                       ecolor='#60a5fa', elinewidth=2, capsize=5, capthick=2,
                       label='Valor Normalizado (Medido/Nominal) ± Incertidumbre')

            # NUEVO: Dibujar líneas EMP escalonadas o globales
            if tiene_emp_por_punto:
                # EMPs por punto - líneas escalonadas
                emps_normalizados_sup = []
                emps_normalizados_inf = []

                for i, p in enumerate(puntos_validos):
                    emp_abs = safe_float(p.get('emp_absoluto', 0), 0)
                    nominal = nominales[i]
                    if nominal != 0:
                        emp_norm = emp_abs / nominal
                    else:
                        emp_norm = 0
                    emps_normalizados_sup.append(1 + emp_norm)
                    emps_normalizados_inf.append(1 - emp_norm)

                # Dibujar líneas escalonadas
                ax.step(nominales, emps_normalizados_sup, where='mid', color='r',
                       linestyle='--', linewidth=2, label='Límite Superior EMP (variable)')
                ax.step(nominales, emps_normalizados_inf, where='mid', color='r',
                       linestyle='--', linewidth=2, label='Límite Inferior EMP (variable)')
            else:
                # EMP global - líneas horizontales tradicionales
                emp_decimal = emp_valor / 100
                ax.axhline(y=1 + emp_decimal, color='r', linestyle='--', linewidth=2,
                          label=f'Límite Superior +{emp_valor}%')
                ax.axhline(y=1 - emp_decimal, color='r', linestyle='--', linewidth=2,
                          label=f'Límite Inferior -{emp_valor}%')

            # Línea de referencia en 1 (valor ideal normalizado)
            ax.axhline(y=1, color='black', linestyle='-', linewidth=1, alpha=0.3)

            # Etiquetas
            ax.set_xlabel(f'Valor Nominal ({unidad_equipo})', fontsize=12, fontweight='bold')
            ax.set_ylabel('Valor Normalizado (Medido/Nominal)', fontsize=12, fontweight='bold')
            titulo = 'Gráfica de Comportamiento Histórico - Confirmación Metrológica (Normalizada)'
            if tiene_emp_por_punto:
                titulo += ' - EMPs Variables'
            ax.set_title(titulo, fontsize=14, fontweight='bold', pad=20)
        else:
            # EMP en unidades absolutas - gráfica tradicional
            ax.errorbar(nominales, errores, yerr=incertidumbres,
                       fmt='o-', color='#3b82f6', linewidth=2, markersize=8,
                       ecolor='#60a5fa', elinewidth=2, capsize=5, capthick=2,
                       label='Error ± Incertidumbre')

            # NUEVO: Dibujar líneas EMP escalonadas o globales
            if tiene_emp_por_punto:
                # EMPs por punto - líneas escalonadas
                emps_absolutos = [safe_float(p.get('emp_absoluto', 0), 0) for p in puntos_validos]

                # Dibujar líneas escalonadas
                ax.step(nominales, emps_absolutos, where='mid', color='r',
                       linestyle='--', linewidth=2, label='Límite EMP+ (variable)')
                ax.step(nominales, [-e for e in emps_absolutos], where='mid', color='r',
                       linestyle='--', linewidth=2, label='Límite EMP- (variable)')
            else:
                # EMP global - líneas horizontales tradicionales
                ax.axhline(y=emp_valor, color='r', linestyle='--', linewidth=2,
                          label=f'Límite EMP +{emp_valor} {emp_unidad}')
                ax.axhline(y=-emp_valor, color='r', linestyle='--', linewidth=2,
                          label=f'Límite EMP -{emp_valor} {emp_unidad}')

            # Línea de referencia en cero
            ax.axhline(y=0, color='black', linestyle='-', linewidth=1, alpha=0.3)

            # Etiquetas
            ax.set_xlabel(f'Valor Nominal ({unidad_equipo})', fontsize=12, fontweight='bold')
            ax.set_ylabel(f'Error ({unidad_equipo})', fontsize=12, fontweight='bold')
            titulo = 'Gráfica de Comportamiento Histórico - Confirmación Metrológica'
            if tiene_emp_por_punto:
                titulo += ' - EMPs Variables'
            ax.set_title(titulo, fontsize=14, fontweight='bold', pad=20)

        # Leyenda - Colocarla fuera de la gráfica (debajo)
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.12),
                 ncol=3, fontsize=9, framealpha=0.95, edgecolor='gray')

        # Grid
        ax.grid(True, alpha=0.3, linestyle='--')

        # Ajustar layout con espacio para la leyenda
        plt.tight_layout()
        plt.subplots_adjust(bottom=0.15)

        # Guardar en buffer
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)

        # Convertir a base64
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        plt.close(fig)

        return f'data:image/png;base64,{image_base64}'

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error generando gráfica: {str(e)}")
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

    # ==================== PARSEAR PUNTOS DE CALIBRACIÓN ====================
    puntos_medicion = []

    if datos_confirmacion and 'puntos_medicion' in datos_confirmacion:
        # Si vienen datos del POST, usarlos
        puntos_medicion = datos_confirmacion['puntos_medicion']
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
    # Determinar valores de formato (usar POST si está disponible, sino empresa)
    if datos_confirmacion and 'formato' in datos_confirmacion:
        formato_codigo = datos_confirmacion['formato'].get('codigo', equipo.empresa.formato_codificacion_empresa or 'REG-SAM-CM-001')
        formato_version = datos_confirmacion['formato'].get('version', equipo.empresa.formato_version_empresa or '3.0')
        formato_fecha_str = datos_confirmacion['formato'].get('fecha')
        if formato_fecha_str:
            from datetime import datetime as dt
            try:
                formato_fecha = dt.strptime(formato_fecha_str, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                formato_fecha = equipo.empresa.formato_fecha_version_empresa or datetime.now().date()
        else:
            formato_fecha = equipo.empresa.formato_fecha_version_empresa or datetime.now().date()
    else:
        formato_codigo = equipo.empresa.formato_codificacion_empresa or 'REG-SAM-CM-001'
        formato_version = equipo.empresa.formato_version_empresa or '3.0'
        formato_fecha = equipo.empresa.formato_fecha_version_empresa or datetime.now().date()

    # Preparar estructura datos_confirmacion para el template de impresión
    datos_confirmacion_template = {
        'formato': {
            'codigo': formato_codigo,
            'version': formato_version,
            'fecha': formato_fecha,
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
        'unidad_equipo': datos_confirmacion.get('unidad_equipo', emp_info['unidad']) if datos_confirmacion else emp_info['unidad'],
        'regla_decision': datos_confirmacion.get('regla_decision', 'guard_band_U') if datos_confirmacion else 'guard_band_U',
        'puntos_medicion': puntos_medicion,
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

        # ID de calibración específica (si viene por GET)
        'calibracion_id': ultima_calibracion.id if ultima_calibracion else None,

        # Datos del POST si los hay
        'regla_decision': datos_confirmacion.get('regla_decision', 'guard_band_U') if datos_confirmacion else 'guard_band_U',
        'checklist': datos_confirmacion.get('checklist', {}) if datos_confirmacion else {},
        'metodo_intervalo': datos_confirmacion.get('metodo_intervalo', {}) if datos_confirmacion else {},

        # Estructura completa para el template de impresión
        'datos_confirmacion': datos_confirmacion_template,
    }

    return context


@login_required
def confirmacion_metrologica(request, equipo_id):
    """
    Vista para generar el documento de Confirmación Metrológica

    Extrae datos del equipo y calibraciones de la BD y los pasa al template
    Si se pasa calibracion_id por GET, usa esa calibración específica
    """
    equipo = get_object_or_404(Equipo, id=equipo_id)

    # Verificar que el usuario tenga permiso para ver este equipo
    if request.user.empresa != equipo.empresa and not request.user.is_superuser:
        return HttpResponse("No tiene permisos para ver este equipo", status=403)

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


@login_required
def intervalos_calibracion(request, equipo_id):
    """
    Vista para generar el documento de Intervalos de Calibración (Métodos ILAC G-24)

    Este será el segundo documento separado
    Si se pasa calibracion_id por GET, usa esa calibración como actual

    MEJORA: Reutiliza datos de Confirmación Metrológica si existe el PDF
    """
    equipo = get_object_or_404(Equipo, id=equipo_id)

    # Verificar permisos
    if request.user.empresa != equipo.empresa and not request.user.is_superuser:
        return HttpResponse("No tiene permisos para ver este equipo", status=403)

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
    if datos_confirmacion_actual and datos_confirmacion_anterior:
        # Comparar puntos de calibración con tolerancia 5%
        puntos_actual = datos_confirmacion_actual.get('puntos_medicion', [])
        puntos_anterior = datos_confirmacion_anterior.get('puntos_medicion', [])


        puntos_coincidentes = []
        for idx_actual, p_actual in enumerate(puntos_actual):
            nominal_actual = p_actual['nominal']

            # Buscar punto coincidente en calibración anterior (tolerancia 5%)
            mejor_match = None
            mejor_diferencia = float('inf')

            for idx_anterior, p_anterior in enumerate(puntos_anterior):
                nominal_anterior = p_anterior['nominal']

                # Calcular diferencia absoluta y relativa
                diferencia_absoluta = abs(nominal_actual - nominal_anterior)
                if nominal_actual != 0:
                    diferencia_relativa = diferencia_absoluta / abs(nominal_actual)
                else:
                    diferencia_relativa = diferencia_absoluta

                # Usar tolerancia más estricta: debe ser casi exacto
                if diferencia_relativa < mejor_diferencia and diferencia_relativa <= 0.05:
                    mejor_match = (idx_anterior, p_anterior)
                    mejor_diferencia = diferencia_relativa

            if mejor_match:
                idx_anterior, p_anterior = mejor_match

                # Punto coincidente encontrado
                puntos_coincidentes.append({
                    'nominal': nominal_actual,
                    'desviacion_actual': p_actual['desviacion_abs'],
                    'desviacion_anterior': p_anterior['desviacion_abs'],
                    'cambio_desviacion': abs(p_actual['desviacion_abs'] - p_anterior['desviacion_abs'])
                })

        # Calcular deriva basándose en el punto con mayor cambio
        if puntos_coincidentes:
            punto_max_cambio = max(puntos_coincidentes, key=lambda p: p['cambio_desviacion'])

            # Calcular tiempo transcurrido en meses
            fecha_actual = cal_actual.fecha_calibracion
            fecha_anterior = cal_anterior.fecha_calibracion
            dias_transcurridos = (fecha_actual - fecha_anterior).days
            meses_transcurridos = dias_transcurridos / 30.44  # Promedio dias por mes

            # Calcular deriva (cambio por mes)
            if meses_transcurridos > 0:
                deriva_por_mes = punto_max_cambio['cambio_desviacion'] / meses_transcurridos
            else:
                deriva_por_mes = 0

            # Obtener EMP para calcular EMP especifico de cada punto
            emp_valor = emp_info['valor']
            emp_unidad = emp_info['unidad']

            # Calcular deriva individual y EMP especifico para cada punto
            for idx_punto, punto in enumerate(puntos_coincidentes):
                # Deriva de este punto específico (cambio / tiempo)
                if meses_transcurridos > 0:
                    deriva_punto = punto['cambio_desviacion'] / meses_transcurridos
                else:
                    deriva_punto = 0

                punto['deriva_punto'] = round(deriva_punto, 6)

                # NUEVO: Buscar EMP especifico de este punto en datos_confirmacion_actual
                nominal_punto = punto['nominal']
                emp_punto_encontrado = None
                emp_tipo_encontrado = None

                for p_actual in puntos_actual:
                    if abs(p_actual['nominal'] - nominal_punto) / nominal_punto <= 0.05 if nominal_punto != 0 else False:
                        # Encontramos el punto, extraer su EMP
                        emp_punto_encontrado = p_actual.get('emp_valor')
                        emp_tipo_encontrado = p_actual.get('emp_tipo')
                        break

                # Calcular EMP especifico de este punto
                if emp_punto_encontrado is not None and emp_tipo_encontrado is not None:
                    # Usar EMP del punto guardado en confirmacion
                    if emp_tipo_encontrado == '%':
                        emp_punto = nominal_punto * (emp_punto_encontrado / 100)
                    else:  # 'abs'
                        emp_punto = emp_punto_encontrado
                else:
                    # Fallback: usar EMP global del equipo (compatibilidad con datos antiguos)
                    if emp_unidad == '%':
                        emp_punto = nominal_punto * (emp_valor / 100)
                    else:
                        emp_punto = emp_valor

                punto['emp_punto'] = round(emp_punto, 4)

                # Determinar estado basado en cambio
                if punto['cambio_desviacion'] == punto_max_cambio['cambio_desviacion']:
                    punto['estado'] = 'MÁXIMO'
                    punto['es_maximo'] = True
                elif punto['cambio_desviacion'] > punto_max_cambio['cambio_desviacion'] * 0.7:
                    punto['estado'] = 'ALTO'
                    punto['es_maximo'] = False
                elif punto['cambio_desviacion'] > punto_max_cambio['cambio_desviacion'] * 0.3:
                    punto['estado'] = 'MODERADO'
                    punto['es_maximo'] = False
                else:
                    punto['estado'] = 'BAJO'
                    punto['es_maximo'] = False

            deriva_automatica = {
                'fecha_anterior': fecha_anterior.strftime('%Y-%m-%d'),
                'fecha_actual': fecha_actual.strftime('%Y-%m-%d'),
                'meses_transcurridos': round(meses_transcurridos, 2),
                'desviacion_anterior': punto_max_cambio['desviacion_anterior'],
                'desviacion_actual': punto_max_cambio['desviacion_actual'],
                'cambio_desviacion': punto_max_cambio['cambio_desviacion'],
                'deriva_por_mes': deriva_por_mes,
                'puntos_coincidentes': len(puntos_coincidentes),
                'nominal_referencia': punto_max_cambio['nominal'],
                'puntos_detalle': json.dumps(puntos_coincidentes)  # Serializar a JSON string para el template
            }

    # ==================== CALCULAR ERROR MÁXIMO PARA MÉTODO 1B ====================
    error_maximo_info = None
    puntos_metodo1b = []  # NUEVO: Lista de todos los puntos para tabla editable

    if datos_confirmacion_actual:
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

        # NUEVO: Error máximo para Método 1B
        'error_maximo_info': error_maximo_info,
        'puntos_metodo1b': json.dumps(puntos_metodo1b),  # Serializar para JavaScript

        # Metadatos para el PDF
        'nombre_empresa': equipo.empresa.nombre,
        'logo_empresa_url': equipo.empresa.logo_empresa.url if equipo.empresa.logo_empresa else None,
        'formato_codigo': equipo.empresa.formato_codificacion_empresa or 'REG-SAM-IC-001',
        'formato_version': equipo.empresa.formato_version_empresa or '3.0',
        'formato_fecha': equipo.empresa.formato_fecha_version_empresa or datetime.now().date(),
    }

    return render(request, 'core/intervalos_calibracion.html', context)


@login_required
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

    equipo = get_object_or_404(Equipo, id=equipo_id)

    # Verificar permisos
    if request.user.empresa != equipo.empresa and not request.user.is_superuser:
        return HttpResponse("No tiene permisos", status=403)

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

    # Si es POST, recibir datos del formulario
    datos_confirmacion = {}
    if request.method == 'POST' and request.content_type == 'application/json':
        datos_confirmacion = json.loads(request.body)

        # ============ GUARDAR FORMATO EN EMPRESA ============
        # Si vienen datos de formato en el POST, actualizar la empresa
        if 'formato' in datos_confirmacion:
            formato_data = datos_confirmacion['formato']
            empresa = equipo.empresa

            # Actualizar campos de formato de la empresa
            if 'codigo' in formato_data:
                empresa.formato_codificacion_empresa = formato_data['codigo']
            if 'version' in formato_data:
                empresa.formato_version_empresa = formato_data['version']
            if 'fecha' in formato_data:
                # Convertir string de fecha a objeto date
                from datetime import datetime as dt
                try:
                    empresa.formato_fecha_version_empresa = dt.strptime(formato_data['fecha'], '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    pass  # Si hay error en el formato, mantener valor actual

            empresa.save()

    # Preparar contexto (igual que confirmacion_metrologica pero con datos del POST)
    context = _preparar_contexto_confirmacion(request, equipo, ultima_calibracion, datos_confirmacion)

    # ============ GENERAR GRÁFICA CON MATPLOTLIB ============
    if datos_confirmacion and 'puntos_medicion' in datos_confirmacion:
        puntos = datos_confirmacion['puntos_medicion']
        emp_valor = safe_float(datos_confirmacion.get('emp') or context['datos_confirmacion']['emp'], 0)
        emp_unidad = datos_confirmacion.get('emp_unidad', context['datos_confirmacion']['emp_unidad'])
        unidad_equipo = datos_confirmacion.get('unidad_equipo', context['datos_confirmacion']['unidad_equipo'])

        grafica_base64 = _generar_grafica_confirmacion(puntos, emp_valor, emp_unidad, unidad_equipo)
        context['grafica_imagen'] = grafica_base64
    else:
        context['grafica_imagen'] = None

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
        # Guardamos los datos de confirmación para usarlos en intervalos de calibración
        if datos_confirmacion and 'puntos_medicion' in datos_confirmacion:
            # Calcular desviación máxima absoluta (para deriva)
            puntos = datos_confirmacion['puntos_medicion']
            desviacion_maxima = 0
            puntos_procesados = []

            for punto in puntos:
                # Calcular desviación absoluta del punto
                nominal = safe_float(punto.get('nominal', 0), 0)
                error = safe_float(punto.get('error', 0), 0)
                desviacion_abs = abs(error)

                if desviacion_abs > desviacion_maxima:
                    desviacion_maxima = desviacion_abs

                # NUEVO: Incluir datos de EMP por punto
                emp_valor_punto = punto.get('emp_valor')
                emp_tipo_punto = punto.get('emp_tipo')
                emp_absoluto_punto = punto.get('emp_absoluto')

                # Guardar punto procesado con todos los datos
                punto_procesado = {
                    'nominal': nominal,
                    'lectura': safe_float(punto.get('lectura', 0), 0),
                    'incertidumbre': safe_float(punto.get('incertidumbre', 0), 0),
                    'error': error,
                    'error_mas_u': safe_float(punto.get('error_mas_u', 0), 0),
                    'error_menos_u': safe_float(punto.get('error_menos_u', 0), 0),
                    'conformidad': punto.get('conformidad', 'Pendiente'),
                    'desviacion_abs': desviacion_abs
                }

                # Agregar EMPs solo si existen
                if emp_valor_punto is not None:
                    punto_procesado['emp_valor'] = safe_float(emp_valor_punto, 0)
                if emp_tipo_punto is not None:
                    punto_procesado['emp_tipo'] = emp_tipo_punto
                if emp_absoluto_punto is not None:
                    punto_procesado['emp_absoluto'] = safe_float(emp_absoluto_punto, 0)

                puntos_procesados.append(punto_procesado)

            # Guardar en campo JSON
            ultima_calibracion.confirmacion_metrologica_datos = {
                'fecha_confirmacion': datetime.now().strftime('%Y-%m-%d'),
                'puntos_medicion': puntos_procesados,
                'desviacion_maxima': desviacion_maxima,
                'emp_valor': safe_float(datos_confirmacion.get('emp', 0), 0),
                'emp_unidad': datos_confirmacion.get('emp_unidad', '%'),
                'unidad_equipo': datos_confirmacion.get('unidad_equipo', ''),
                'regla_decision': datos_confirmacion.get('regla_decision', 'guard_band_U'),
                'decision': datos_confirmacion.get('conclusion', {}).get('decision', 'Pendiente'),
                'responsable': datos_confirmacion.get('conclusion', {}).get('responsable', request.user.get_full_name() or request.user.username)
            }

        # GUARDAR EN BD - Campo confirmacion_metrologica_pdf de Calibracion
        filename = f'confirmacion_metrologica_{equipo.codigo_interno}_{ultima_calibracion.fecha_calibracion.strftime("%Y%m%d")}.pdf'
        ultima_calibracion.confirmacion_metrologica_pdf.save(
            filename,
            ContentFile(pdf_file),
            save=True
        )

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


@login_required
@require_http_methods(["POST"])
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

    equipo = get_object_or_404(Equipo, id=equipo_id)

    logger.info(f"User.empresa: {request.user.empresa} (ID: {request.user.empresa.id if request.user.empresa else None})")
    logger.info(f"Equipo.empresa: {equipo.empresa} (ID: {equipo.empresa.id if equipo.empresa else None})")
    logger.info(f"User.is_superuser: {request.user.is_superuser}")

    # Verificar permisos
    if request.user.empresa != equipo.empresa and not request.user.is_superuser:
        logger.error(f"PERMISO DENEGADO: User empresa {request.user.empresa} != Equipo empresa {equipo.empresa}")
        return JsonResponse({'success': False, 'message': 'No tiene permisos'}, status=403)

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

    # Obtener deriva automática para incluir en PDF si usó Método 2 o 3
    deriva_automatica_pdf = None
    if datos_intervalos.get('metodo_seleccionado') in ['metodo2', 'metodo3']:
        # Recalcular deriva automática igual que en la vista de intervalos
        cal_anterior_pdf = Calibracion.objects.filter(
            equipo=equipo,
            fecha_calibracion__lt=calibracion_actual.fecha_calibracion
        ).order_by('-fecha_calibracion').first()

        if (hasattr(calibracion_actual, 'confirmacion_metrologica_datos') and calibracion_actual.confirmacion_metrologica_datos and
            cal_anterior_pdf and hasattr(cal_anterior_pdf, 'confirmacion_metrologica_datos') and cal_anterior_pdf.confirmacion_metrologica_datos):
            datos_actual = calibracion_actual.confirmacion_metrologica_datos
            datos_anterior = cal_anterior_pdf.confirmacion_metrologica_datos

            puntos_actual = datos_actual.get('puntos_medicion', [])
            puntos_anterior = datos_anterior.get('puntos_medicion', [])

            puntos_coincidentes_pdf = []
            for p_actual in puntos_actual:
                nominal_actual = p_actual['nominal']
                for p_anterior in puntos_anterior:
                    nominal_anterior = p_anterior['nominal']
                    diferencia_porcentual = abs(nominal_actual - nominal_anterior) / nominal_actual if nominal_actual != 0 else 0

                    if diferencia_porcentual <= 0.05:
                        # Calcular EMP específico de este punto
                        emp_punto_encontrado = p_actual.get('emp_valor')
                        emp_tipo_encontrado = p_actual.get('emp_tipo')

                        if emp_punto_encontrado is not None and emp_tipo_encontrado is not None:
                            # Usar EMP del punto guardado en confirmación
                            if emp_tipo_encontrado == '%':
                                emp_punto = nominal_actual * (emp_punto_encontrado / 100)
                            else:  # 'abs'
                                emp_punto = emp_punto_encontrado
                        else:
                            # Fallback: usar EMP global del equipo
                            if emp_info['unidad'] == '%':
                                emp_punto = nominal_actual * (emp_info['valor'] / 100)
                            else:
                                emp_punto = emp_info['valor']

                        puntos_coincidentes_pdf.append({
                            'nominal': nominal_actual,
                            'desviacion_actual': p_actual['desviacion_abs'],
                            'desviacion_anterior': p_anterior['desviacion_abs'],
                            'cambio_desviacion': abs(p_actual['desviacion_abs'] - p_anterior['desviacion_abs']),
                            'emp_punto': round(emp_punto, 4)
                        })
                        break

            if puntos_coincidentes_pdf:
                punto_max_cambio_pdf = max(puntos_coincidentes_pdf, key=lambda p: p['cambio_desviacion'])
                fecha_actual_pdf = calibracion_actual.fecha_calibracion
                fecha_anterior_pdf = cal_anterior_pdf.fecha_calibracion
                dias_transcurridos_pdf = (fecha_actual_pdf - fecha_anterior_pdf).days
                meses_transcurridos_pdf = dias_transcurridos_pdf / 30.44

                # Calcular deriva individual para cada punto (EMP ya se calculó antes por punto)
                for punto in puntos_coincidentes_pdf:
                    deriva_punto = punto['cambio_desviacion'] / meses_transcurridos_pdf if meses_transcurridos_pdf > 0 else 0
                    punto['deriva_punto'] = round(deriva_punto, 6)

                    # Estado basado en cambio de desviación
                    if punto['cambio_desviacion'] == punto_max_cambio_pdf['cambio_desviacion']:
                        punto['estado'] = 'MÁXIMO'
                        punto['es_maximo'] = True
                    elif punto['cambio_desviacion'] > punto_max_cambio_pdf['cambio_desviacion'] * 0.7:
                        punto['estado'] = 'ALTO'
                        punto['es_maximo'] = False
                    elif punto['cambio_desviacion'] > punto_max_cambio_pdf['cambio_desviacion'] * 0.3:
                        punto['estado'] = 'MODERADO'
                        punto['es_maximo'] = False
                    else:
                        punto['estado'] = 'BAJO'
                        punto['es_maximo'] = False

                deriva_automatica_pdf = {
                    'puntos_detalle': puntos_coincidentes_pdf,
                    'puntos_coincidentes': len(puntos_coincidentes_pdf)
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
                save=True
            )
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


@login_required
def guardar_confirmacion(request, equipo_id):
    """
    Guarda los resultados de la confirmación metrológica en la BD

    Recibe datos del formulario vía POST y actualiza:
    - Campo confirmacion_metrologica_pdf en la última Calibracion
    - Opcionalmente crea un nuevo modelo ConfirmacionMetrologica
    """
    if request.method != 'POST':
        return redirect('confirmacion_metrologica', equipo_id=equipo_id)

    equipo = get_object_or_404(Equipo, id=equipo_id)

    # Verificar permisos
    if request.user.empresa != equipo.empresa and not request.user.is_superuser:
        return HttpResponse("No tiene permisos", status=403)

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

    return redirect('detalle_equipo', equipo_id=equipo_id)


@login_required
def actualizar_formato_empresa(request):
    """
    Actualiza la información del formato (código, versión, fecha) de la empresa.
    Estos cambios se aplican a todos los equipos de la empresa.
    """
    from django.http import JsonResponse
    from core.models import Empresa
    import json
    from datetime import datetime

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)

    try:
        datos = json.loads(request.body)

        # Obtener la empresa del usuario
        empresa = request.user.empresa
        if not empresa:
            return JsonResponse({'success': False, 'message': 'Usuario no tiene empresa asociada'}, status=400)

        # Actualizar los campos de formato
        if 'codigo' in datos:
            empresa.formato_codificacion_empresa = datos['codigo']

        if 'version' in datos:
            empresa.formato_version_empresa = datos['version']

        if 'fecha' in datos:
            try:
                # Convertir string de fecha a objeto date
                fecha_str = datos['fecha']
                fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                empresa.formato_fecha_version_empresa = fecha_obj
            except (ValueError, TypeError):
                pass  # Si hay error en la fecha, no actualizar

        empresa.save()

        return JsonResponse({
            'success': True,
            'message': 'Formato actualizado correctamente para todos los equipos de la empresa',
            'datos': {
                'codigo': empresa.formato_codificacion_empresa or '',
                'version': empresa.formato_version_empresa or '',
                'fecha': empresa.formato_fecha_version_empresa.strftime('%Y-%m-%d') if empresa.formato_fecha_version_empresa else ''
            }
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error al actualizar formato: {str(e)}'
        }, status=500)
