"""
Lectura automática de certificados de calibración con Gemini.

Flujo:
    1. solicitar_lectura(calibracion, usuario) crea/reinicia una LecturaCertificado
       en estado "pendiente" y despierta el despachador.
    2. El despachador (un hilo por proceso, una lectura a la vez por proceso) toma
       lecturas pendientes de la base de datos, manda el PDF a Gemini y guarda:
         - resultado_crudo: lo que leyó Gemini, tal cual.
         - propuesta: los datos convertidos al formato de la confirmación (v2).
    3. La pantalla de confirmación precarga la propuesta para que el técnico la
       revise. Nada queda guardado como confirmación hasta que el técnico la guarda.

Reglas de conversión (decididas con el usuario, 2026-11-21):
    - Si el certificado trae el error, se usa ese (redondeos del laboratorio
      incluidos). Si trae corrección, se usa con el signo cambiado. Si no trae
      error absoluto (trae %, factor o nada), la plataforma lo calcula.
    - Cada tabla / frecuencia / eje queda como una variable (pestaña) aparte.
    - Un punto sin lectura pero con error se completa: lectura = patrón + error.
      Un punto sin lectura ni error se descarta (y la tabla si queda vacía).
    - Incertidumbre en % se convierte a absoluta. Si viene como fórmula queda
      vacía y marcada para que el técnico la llene.

El despachador corre en el mismo proceso web (en producción no hay worker
aparte). Por eso el estado vive en la base de datos: si el servidor se reinicia
a mitad de una lectura, ésta se retoma en la siguiente consulta.
"""
import json
import logging
import math
import re
import threading
import time
from datetime import timedelta

from django.conf import settings
from django.db import close_old_connections, transaction
from django.db.models import F
from django.utils import timezone

logger = logging.getLogger('core')

# Tamaño máximo del PDF que se manda en línea a Gemini (el límite de la API es ~20 MB por petición).
MAX_PDF_BYTES = 18 * 1024 * 1024
# Una lectura en "procesando" por más de este tiempo se considera abandonada (reinicio del servidor).
MINUTOS_LECTURA_ABANDONADA = 10
MAX_INTENTOS = 3
TIMEOUT_GEMINI_MS = 5 * 60 * 1000


# =============================================================================
# 1. Instrucciones y esquema para Gemini
# =============================================================================

PROMPT = """Eres un metrólogo. Lee este PDF, que puede contener UNO O VARIOS certificados de calibración
(a veces escaneados). Devuelve SOLO JSON según el esquema. Reglas:
- Un objeto por certificado. Si el PDF trae varios, sepáralos.
- Una "tabla" por cada función/rango/tipo de medición (p.ej. tensión DC, tensión AC, resistencia;
  exteriores/interiores/profundidad; cada gas; campo eléctrico/magnético). Incluye TODAS las tablas de resultados.
- NO incluyas: precargas, error de cero, coeficientes de polinomios, respuesta en frecuencia relativa
  a una referencia (columnas "Ref."), condiciones ambientales, datos del patrón del laboratorio.
- Si la misma tabla viene en dos unidades (SI y unidad del instrumento), incluye LAS DOS como tablas separadas.
- magnitud: nombre corto y ESTÁNDAR de la magnitud física, siempre igual para el mismo tipo de medición
  (no copies el título del certificado). Usa uno de estos si aplica: Presión, Temperatura, Humedad relativa,
  Masa, Fuerza, Par torsional, Longitud, Ángulo, Tensión DC, Tensión AC, Corriente DC, Corriente AC,
  Resistencia, Resistencia de aislamiento, Resistencia de puesta a tierra, Frecuencia, Iluminancia,
  Campo eléctrico, Campo magnético, Nivel de señal, Concentración de gas, Sonido, Velocidad, Tiempo.
- variante: lo que distingue dos tablas de la misma magnitud en el mismo certificado, en 1 a 3 palabras
  ("Exteriores", "Interiores", "Profundidad", "Linealidad", "Respuesta en frecuencia", "CO", "Metano",
  "Eje X" si la tabla es de un solo eje). null si la magnitud tiene una sola tabla. La unidad NO es
  variante: dos tablas iguales en distinta unidad llevan la misma magnitud y variante null.
- referencia = valor del patrón / valor convencionalmente verdadero. lectura = indicación del equipo
  bajo calibración (promedio si hay varias repeticiones). Fíjate en el SIGNIFICADO, no solo en el nombre
  de la columna (en cintas métricas "Longitud Medida" suele ser la referencia; compruébalo con el error).
- Si el valor real del patrón aparece con más decimales en otra tabla, usa el más exacto.
- Números: escríbelos como número JSON con punto decimal, sin separadores de miles
  ("24,999 6" -> 24.9996; "1,4E+00" -> 1.4; "1,0 x 10³" -> 1000).
- Unidad: la que aplica a ESE valor tal como la imprime el certificado (mV, V, µm, mm, klx, psi...).
  Referencia, lectura, error e incertidumbre pueden tener unidades distintas: dales a cada uno la suya.
- condicion: lo que cambia QUÉ se está midiendo dentro de la tabla: frecuencia ("60 Hz", "1 kHz"),
  eje ("Eje X"), tensión de prueba distinta. Escríbela igual en todos los puntos que la comparten. null si no aplica.
  NO es condición el rango, intervalo o escala del equipo ("0 a 20 Ω", "(20,0 a 199,9) Ω"): los puntos de
  distintos rangos de la misma función van en la misma tabla con la misma condición.
  El gas cero (aire sintético, nitrógeno) es el punto cero de la misma tabla, no una condición aparte.
  Si la tabla tiene columnas por eje (X, Y, Z), haz una tabla por eje.
- error_reportado: el valor tal cual; tipo_error: "error" (lectura-referencia), "correccion"
  (referencia-lectura), "factor" (factor multiplicativo), "relativo_%" o "ninguno".
- Incertidumbre expandida U por punto. Si viene en %, pon incertidumbre_tipo "%". Si solo hay una
  fórmula o un valor global fuera de la tabla, deja null y explícalo en notas (escribe la fórmula).
- k por punto si existe, si no el global, si no null.
- Si un dato no se ve o no existe, usa null. NUNCA inventes.
- confianza: "alta", "media" o "baja" por tabla, según qué tan legible estaba.
"""

_NUM = {"type": "number", "nullable": True}
_TXT = {"type": "string", "nullable": True}
SCHEMA = {
    "type": "object",
    "properties": {"certificados": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "laboratorio": _TXT, "numero_certificado": _TXT,
            "fecha_calibracion": {"type": "string", "nullable": True, "description": "AAAA-MM-DD"},
            "equipo": {"type": "object", "properties": {
                "tipo": _TXT, "marca": _TXT, "modelo": _TXT, "serie": _TXT, "codigo_interno": _TXT,
                "rango": _TXT, "resolucion": _TXT}},
            "tablas": {"type": "array", "items": {"type": "object", "properties": {
                "nombre": {"type": "string"}, "magnitud": _TXT, "variante": _TXT, "confianza": _TXT,
                "puntos": {"type": "array", "items": {"type": "object", "properties": {
                    "condicion": _TXT,
                    "referencia": _NUM, "unidad_referencia": _TXT,
                    "lectura": _NUM, "unidad_lectura": _TXT,
                    "error_reportado": _NUM, "unidad_error": _TXT, "tipo_error": _TXT,
                    "incertidumbre": _NUM, "unidad_incertidumbre": _TXT, "incertidumbre_tipo": _TXT,
                    "k": _NUM}}}},
                "required": ["nombre", "puntos"]}},
            "notas": _TXT},
        "required": ["tablas"]}}},
    "required": ["certificados"],
}


class ErrorLectura(Exception):
    """Error esperado al leer un certificado (se muestra al usuario tal cual)."""


def modelo_configurado():
    return getattr(settings, 'GEMINI_MODEL', '') or 'gemini-3.8-flash'


def leer_pdf_con_gemini(pdf_bytes):
    """Manda el PDF a Gemini y devuelve (datos_json, info_uso)."""
    api_key = getattr(settings, 'GEMINI_API_KEY', '')
    if not api_key:
        raise ErrorLectura('La lectura automática no está configurada (falta GEMINI_API_KEY).')
    if len(pdf_bytes) > MAX_PDF_BYTES:
        raise ErrorLectura('El PDF pesa más de 18 MB; no se puede leer automáticamente.')
    if not pdf_bytes.startswith(b'%PDF'):
        raise ErrorLectura('El documento de la calibración no es un PDF.')

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=TIMEOUT_GEMINI_MS))
    inicio = time.time()
    respuesta = client.models.generate_content(
        model=modelo_configurado(),
        contents=[types.Part.from_bytes(data=pdf_bytes, mime_type='application/pdf'), PROMPT],
        config=types.GenerateContentConfig(
            response_mime_type='application/json', response_schema=SCHEMA, temperature=0),
    )
    try:
        datos = json.loads(respuesta.text)
    except (TypeError, ValueError) as exc:
        raise ErrorLectura('La IA no devolvió datos legibles para este certificado.') from exc

    uso = respuesta.usage_metadata
    info = {
        'segundos': round(time.time() - inicio, 1),
        'tokens_entrada': getattr(uso, 'prompt_token_count', 0) or 0,
        'tokens_salida': (getattr(uso, 'candidates_token_count', 0) or 0)
                         + (getattr(uso, 'thoughts_token_count', 0) or 0),
    }
    return datos, info


# =============================================================================
# 2. Conversión de lo leído al formato de la confirmación metrológica (v2)
# =============================================================================

_PREFIJOS = {'p': 1e-12, 'n': 1e-9, 'µ': 1e-6, 'm': 1e-3, 'c': 1e-2, 'k': 1e3, 'M': 1e6, 'G': 1e9}
_ALIAS_UNIDAD = {'lux': 'lx', 'ohm': 'Ω', 'ohms': 'Ω', 'Ohm': 'Ω', 'ohmios': 'Ω'}


def _normalizar_unidad(unidad):
    if not unidad:
        return ''
    u = str(unidad).strip().replace('μ', 'µ').replace(' ', '')
    if u.startswith('u') and len(u) > 1 and u[1:] in ('m', 'V', 'A', 'T', 's', 'Ω', 'W', 'F', 'H', 'g', 'L'):
        u = 'µ' + u[1:]
    for alias, canon in _ALIAS_UNIDAD.items():
        if u.endswith(alias):
            u = u[: -len(alias)] + canon
            break
    return u


def _separar_prefijo(unidad):
    """Devuelve las formas posibles (factor, base) de una unidad. La forma sin prefijo va primero."""
    formas = [(1.0, unidad)]
    if len(unidad) > 1 and unidad[0] in _PREFIJOS:
        formas.append((_PREFIJOS[unidad[0]], unidad[1:]))
    return formas


def factor_conversion(desde, hacia):
    """Factor para pasar un valor de la unidad `desde` a `hacia` (None si no se puede)."""
    a, b = _normalizar_unidad(desde), _normalizar_unidad(hacia)
    if a == b:
        return 1.0
    if not a or not b:
        return None
    # Una diferencia entre dos niveles en dBµV, dBm... se expresa en dB.
    if a.startswith('dB') and b.startswith('dB'):
        return 1.0
    for fa, base_a in _separar_prefijo(a):
        for fb, base_b in _separar_prefijo(b):
            if base_a == base_b:
                return fa / fb
    return None


def _limpio(valor):
    """Quita el ruido de coma flotante (0.42000000000000004 -> 0.42)."""
    if valor is None:
        return None
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return None
    if math.isnan(v) or math.isinf(v):
        return None
    return float(f"{v:.10g}") + 0.0  # + 0.0 convierte -0.0 en 0.0


def emp_del_equipo(equipo):
    """(valor, tipo) del EMP de la hoja de vida, o ('', '%') si no hay uno usable."""
    texto = (getattr(equipo, 'error_maximo_permisible', '') or '').strip()
    if not texto:
        return '', '%'
    m = re.search(r'([\d]+(?:[.,]\d+)?)\s*(%)?', texto)
    if not m:
        return '', '%'
    valor = float(m.group(1).replace(',', '.'))
    return valor, ('%' if m.group(2) else 'abs')


def _texto_comparable(texto):
    return re.sub(r'[^0-9a-z]', '', str(texto or '').lower())


def _elegir_certificados(certificados, calibracion):
    """
    Un PDF puede traer varios certificados (p.ej. el mismo equipo en años distintos).
    Se queda con el que corresponde a esta calibración; si no se puede saber, con todos.
    """
    if len(certificados) <= 1 or calibracion is None:
        return certificados, []

    numero = _texto_comparable(getattr(calibracion, 'numero_certificado', ''))
    if numero:
        por_numero = [c for c in certificados
                      if _texto_comparable(c.get('numero_certificado')) and (
                          numero in _texto_comparable(c.get('numero_certificado'))
                          or _texto_comparable(c.get('numero_certificado')) in numero)]
        if por_numero:
            return por_numero, [c for c in certificados if c not in por_numero]

    fecha = getattr(calibracion, 'fecha_calibracion', None)
    if fecha:
        por_fecha = [c for c in certificados if (c.get('fecha_calibracion') or '')[:10] == fecha.isoformat()]
        if por_fecha:
            return por_fecha, [c for c in certificados if c not in por_fecha]

    return certificados, []


def _convertir_punto(p, emp_valor, emp_tipo, confianza_baja):
    """
    Convierte un punto leído al formato de la tabla de confirmación.
    Devuelve (punto, unidad) o (None, motivo_descarte).
    """
    ref = _limpio(p.get('referencia'))
    if ref is None:
        return None, 'sin valor de referencia'

    u_lect = _normalizar_unidad(p.get('unidad_lectura'))
    u_ref = _normalizar_unidad(p.get('unidad_referencia'))
    unidad = u_lect or u_ref
    revisar = set()
    notas = []

    # Referencia en la unidad de la lectura.
    if u_ref and unidad and u_ref != unidad:
        f = factor_conversion(u_ref, unidad)
        if f is None:
            revisar.add('nominal')
            notas.append(f'Patrón en {u_ref}, lectura en {unidad}: revisar unidades.')
        else:
            ref = _limpio(ref * f)

    # Error del certificado (solo si es absoluto).
    tipo_error = (p.get('tipo_error') or '').strip().lower()
    err = _limpio(p.get('error_reportado'))
    u_err = _normalizar_unidad(p.get('unidad_error'))
    error_cert = None
    if err is not None and tipo_error in ('error', 'correccion') and u_err != '%':
        f = factor_conversion(u_err, unidad) if (u_err and unidad) else 1.0
        if f is None:
            revisar.add('error')
            notas.append(f'Error en {u_err}, no se pudo pasar a {unidad}.')
        else:
            error_cert = _limpio(err * f * (-1 if tipo_error == 'correccion' else 1))

    # Lectura (o reconstruida desde el error).
    lect = _limpio(p.get('lectura'))
    if lect is None:
        if error_cert is None:
            return None, 'sin lectura ni error'
        lect = _limpio(ref + error_cert)
        revisar.add('lectura')
        notas.append('Lectura calculada como patrón + error del certificado.')

    # Incertidumbre expandida.
    inc = _limpio(p.get('incertidumbre'))
    u_inc = _normalizar_unidad(p.get('unidad_incertidumbre'))
    es_relativa = (p.get('incertidumbre_tipo') or '').strip() == '%' or u_inc == '%'
    if inc is None:
        revisar.add('incertidumbre')
    elif es_relativa:
        inc = _limpio(abs(ref) * inc / 100)
        notas.append(f"U convertida desde {p.get('incertidumbre')} % del valor.")
    elif u_inc and unidad and u_inc != unidad:
        f = factor_conversion(u_inc, unidad)
        if f is None:
            revisar.add('incertidumbre')
            notas.append(f'U en {u_inc}, no se pudo pasar a {unidad}.')
        else:
            inc = _limpio(inc * f)

    if confianza_baja:
        revisar.update({'nominal', 'lectura', 'incertidumbre'})
        notas.append('La IA leyó esta tabla con poca claridad.')

    punto = {
        'nominal': ref,
        'lectura': lect,
        'incertidumbre': inc if inc is not None else '',
        'emp_valor': emp_valor,
        'emp_tipo': emp_tipo,
    }
    if error_cert is not None:
        punto['error_certificado'] = error_cert
    if revisar:
        punto['revisar'] = sorted(revisar)
    if notas:
        punto['nota'] = ' '.join(notas)
    return punto, unidad


_UNIDAD_RANGO = r'[^\W\d_]*[µΩ°%/]*[^\W\d_]*'
_RANGO = re.compile(
    r'\(?\s*-?\d[\d.,]*\s*' + _UNIDAD_RANGO + r'\s*(?:a|-|–|to|hasta)\s*-?\d[\d.,]*\s*\)?\s*' + _UNIDAD_RANGO
    + r'|(?:-?\d[\d.,]*\s*' + _UNIDAD_RANGO + r'\s*)?[≤<≥>].*', re.IGNORECASE)
_GAS_CERO = re.compile(r'\b(aire\s+sint[eé]tico|nitr[oó]geno|gas\s+cero|zero\s+gas)\b', re.IGNORECASE)


def _condicion_limpia(condicion):
    """
    Lo que realmente distingue al punto. El rango/escala del equipo ("(20,0 a 199,9) Ω") no
    cambia lo que se mide, así que se quita: "500 V, 4,00 MΩ a 39,99 MΩ" -> "500 V".
    El gas cero es el punto cero de la misma tabla, no otra condición.
    """
    c = (condicion or '').strip()
    if not c or _GAS_CERO.search(c):
        return ''
    c = _RANGO.sub('', c)
    return re.sub(r'^[\s,;:·\-–()]+|[\s,;:·\-–(]+$', '', c).strip()


def _grupos_por_condicion(puntos):
    """
    Separa los puntos de una tabla por condición (frecuencia, eje...).
    No se separa si cada condición tiene un solo punto: eso es una curva de respuesta
    en frecuencia, donde la frecuencia ES la variable y separarla daría pestañas de 1 punto.
    """
    # Copias: no se toca lo que devolvió Gemini (se guarda tal cual en resultado_crudo).
    puntos = [{**p, 'condicion': _condicion_limpia(p.get('condicion'))} for p in puntos]
    condiciones = []
    for p in puntos:
        if p['condicion'] and p['condicion'] not in condiciones:
            condiciones.append(p['condicion'])
    if len(condiciones) > 1:
        grupos = [[p for p in puntos if p['condicion'] == c] for c in condiciones]
        if any(len(g) >= 2 for g in grupos):
            # Los puntos sin condición (p.ej. el cero medido con gas cero) se quedan en el primer grupo.
            grupos[0] = [p for p in puntos if not p['condicion']] + grupos[0]
            return list(zip(condiciones, grupos))
    unica = condiciones[0] if len(condiciones) == 1 else ''
    return [(unica, puntos)]


def _es_unidad(texto, puntos):
    """True si la 'variante' que puso la IA es solo la unidad de la tabla (p.ej. 'kPa')."""
    t = _normalizar_unidad(texto)
    unidades = {_normalizar_unidad(p.get('unidad_lectura') or p.get('unidad_referencia')) for p in puntos}
    return bool(t) and (t in unidades or t in ('SI', 'unidaddelinstrumento'))


def _nombre_base(tabla, condicion):
    """
    Nombre fijo de la variable: magnitud estándar · variante · condición.
    No se usa el título que le pone el laboratorio a la tabla: la gráfica histórica agrupa
    por nombre, y si el nombre cambia de un año a otro el equipo queda en dos gráficas.
    La unidad nunca va como variante: si hace falta distinguir por unidad se agrega "(kPa)" al final.
    """
    magnitud = (tabla.get('magnitud') or '').strip()
    partes = [magnitud[:1].upper() + magnitud[1:] if magnitud else (tabla.get('nombre') or 'Variable').strip()]
    variante = (tabla.get('variante') or '').strip()
    if _es_unidad(variante, tabla.get('puntos') or []):
        variante = ''
    if variante and variante.lower() not in partes[0].lower():
        partes.append(variante)
    if condicion and condicion.lower() not in ' '.join(partes).lower():
        partes.append(condicion)
    return ' · '.join(partes)


def _unificar_unidad(puntos_con_unidad):
    """
    Pasa todos los puntos de un grupo a una sola unidad (la más usada): un multímetro
    reporta 540 mV y 5,4 V en la misma función, y debe quedar una sola tabla en V.
    Devuelve [(unidad, [puntos])]; los que no se pueden convertir quedan en su propio grupo.
    """
    conteo = {}
    for _, u in puntos_con_unidad:
        conteo[u] = conteo.get(u, 0) + 1
    destino = max(conteo, key=lambda u: conteo[u]) if conteo else ''
    grupos = {destino: []}
    for p, u in puntos_con_unidad:
        f = factor_conversion(u, destino) if u != destino else 1.0
        if f is None:
            grupos.setdefault(u, []).append(p)
            continue
        if f != 1.0:
            p = dict(p)
            for campo in ('nominal', 'lectura', 'incertidumbre', 'error_certificado'):
                if isinstance(p.get(campo), (int, float)):
                    p[campo] = _limpio(p[campo] * f)
        grupos[destino].append(p)
    return [(u, pts) for u, pts in grupos.items() if pts]


def _etiqueta_certificado(cert):
    fecha = (cert.get('fecha_calibracion') or '')[:10]
    return f'cert. {fecha}' if fecha else f"cert. {cert.get('numero_certificado') or '?'}"


def _desambiguar_nombres(magnitudes):
    """Si dos variables quedaron con el mismo nombre, se distinguen por unidad y luego por título de tabla."""
    def repetidos():
        vistos = {}
        for m in magnitudes:
            vistos[m['nombre']] = vistos.get(m['nombre'], 0) + 1
        return {n for n, c in vistos.items() if c > 1}

    rep = repetidos()
    for m in magnitudes:
        if m['nombre'] in rep and m['unidad']:
            m['nombre'] = f"{m['nombre']} ({m['unidad']})"
    rep = repetidos()
    for m in magnitudes:
        if m['nombre'] in rep and m.get('_titulo'):
            m['nombre'] = f"{m['nombre']} · {m['_titulo'][:30]}"
    rep = repetidos()
    contador = {}
    for m in magnitudes:
        if m['nombre'] in rep:
            contador[m['nombre']] = contador.get(m['nombre'], 0) + 1
            m['nombre'] = f"{m['nombre']} #{contador[m['nombre']]}"


def _reusar_nombres_previos(magnitudes, nombres_previos):
    """
    Si el equipo ya tiene confirmaciones guardadas, se reusa el nombre de la variable anterior
    cuando la correspondencia es clara (misma unidad y una sola candidata), para que el nuevo
    año caiga en la misma gráfica histórica. Devuelve los cambios hechos [(nuevo, anterior)].
    """
    if not nombres_previos:
        return []
    previos = []
    for n, u in nombres_previos:
        if (n, _normalizar_unidad(u)) not in previos:
            previos.append((n, _normalizar_unidad(u)))
    nombres_previos_set = {n for n, _ in previos}
    usados = {m['nombre'] for m in magnitudes if m['nombre'] in nombres_previos_set}
    cambios = []
    for m in magnitudes:
        if m['nombre'] in nombres_previos_set:
            continue
        unidad = _normalizar_unidad(m['unidad'])
        nuevas_misma_unidad = [x for x in magnitudes if _normalizar_unidad(x['unidad']) == unidad]
        candidatas = [n for n, u in previos if u == unidad and n not in usados]
        if len(candidatas) == 1 and len(nuevas_misma_unidad) == 1:
            cambios.append((m['nombre'], candidatas[0]))
            m['nombre'] = candidatas[0]
            usados.add(candidatas[0])
    return cambios


def construir_propuesta(resultado, equipo=None, calibracion=None, nombres_previos=None):
    """
    Convierte la respuesta de Gemini en los datos que precargan la confirmación (formato v2).
    Función pura: no toca la base de datos (fácil de probar con certificados reales).

    nombres_previos: [(nombre, unidad)] de las variables de confirmaciones anteriores del
    mismo equipo, para conservar los nombres y no partir la gráfica histórica.
    """
    certificados = (resultado or {}).get('certificados') or []
    avisos = []
    if not certificados:
        return {'version': 2, 'magnitudes': [], 'lectura_ia': {
            'avisos': ['No se encontraron resultados de calibración en el PDF.']}}

    # Si el PDF trae varios certificados (unidos a propósito), se cargan todos en esta confirmación.
    varios = len(certificados) > 1
    if varios:
        avisos.append(f'El PDF trae {len(certificados)} certificados: se cargaron todos, '
                      'cada pestaña indica la fecha de su certificado.')

    emp_valor, emp_tipo = emp_del_equipo(equipo) if equipo is not None else ('', '%')
    if emp_valor == '':
        avisos.append('El equipo no tiene EMP en la hoja de vida: complétalo para calcular la conformidad.')

    magnitudes = []
    descartados_por_motivo = {}
    for cert in certificados:
        if cert.get('notas'):
            avisos.append(f"Nota del certificado {cert.get('numero_certificado') or ''}: {cert['notas']}".strip())
        for tabla in cert.get('tablas') or []:
            confianza_baja = (tabla.get('confianza') or 'alta').lower() in ('baja',)
            for condicion, puntos_crudos in _grupos_por_condicion(tabla.get('puntos') or []):
                convertidos = []
                for p in puntos_crudos:
                    punto, unidad_o_motivo = _convertir_punto(p, emp_valor, emp_tipo, confianza_baja)
                    if punto is None:
                        descartados_por_motivo[unidad_o_motivo] = descartados_por_motivo.get(unidad_o_motivo, 0) + 1
                    else:
                        convertidos.append((punto, unidad_o_motivo))
                if not convertidos:
                    continue
                nombre = _nombre_base(tabla, condicion)
                if varios:
                    nombre = f'{nombre} · {_etiqueta_certificado(cert)}'
                for unidad, puntos in _unificar_unidad(convertidos):
                    if confianza_baja:
                        avisos.append(f'"{nombre}" se leyó con poca claridad: revísala completa.')
                    magnitudes.append({
                        'nombre': nombre[:80],
                        'unidad': unidad,
                        'emp': emp_valor,
                        'emp_unidad': emp_tipo,
                        'puntos_medicion': puntos,
                        '_titulo': (tabla.get('nombre') or '').strip(),
                    })

    _desambiguar_nombres(magnitudes)
    if not varios:
        for nuevo, anterior in _reusar_nombres_previos(magnitudes, nombres_previos):
            avisos.append(f'"{nuevo}" se nombró "{anterior or "(sin nombre)"}" como en las confirmaciones '
                          'anteriores, para que siga en la misma gráfica histórica.')
    for m in magnitudes:
        m.pop('_titulo', None)

    for motivo, n in descartados_por_motivo.items():
        avisos.append(f'Se omitieron {n} punto(s) {motivo}.')
    if not magnitudes:
        avisos.append('No quedó ningún punto usable: llena la tabla a mano.')

    # Datos generales: los del certificado de esta calibración (o el más reciente si no se sabe).
    elegidos, _ = _elegir_certificados(certificados, calibracion)
    principal = (elegidos[0] if len(elegidos) == 1
                 else max(certificados, key=lambda c: c.get('fecha_calibracion') or ''))
    fecha = (principal.get('fecha_calibracion') or '')[:10]
    return {
        'version': 2,
        'laboratorio': principal.get('laboratorio') or '',
        'numero_certificado': principal.get('numero_certificado') or '',
        'fecha_certificado': fecha if re.match(r'^\d{4}-\d{2}-\d{2}$', fecha) else '',
        'magnitudes': magnitudes,
        'lectura_ia': {
            'avisos': avisos,
            'certificados_en_pdf': len(certificados),
            'equipo_leido': principal.get('equipo') or {},
        },
    }


# =============================================================================
# 3. Cola de lecturas
# =============================================================================

def calibracion_tiene_confirmacion(calibracion):
    return bool(calibracion.confirmacion_metrologica_datos)


def nombres_previos_equipo(calibracion):
    """[(nombre, unidad)] de las variables de las otras confirmaciones guardadas del mismo equipo."""
    from core.models import Calibracion

    nombres = []
    otras = (Calibracion.objects.filter(equipo_id=calibracion.equipo_id)
             .exclude(id=calibracion.id).exclude(confirmacion_metrologica_datos__isnull=True)
             .order_by('-fecha_calibracion').values_list('confirmacion_metrologica_datos', flat=True))
    for datos in otras:
        if not isinstance(datos, dict):
            continue
        if datos.get('magnitudes'):
            for m in datos['magnitudes']:
                par = (m.get('nombre') or '', m.get('unidad') or '')
                if par not in nombres:
                    nombres.append(par)
        elif datos.get('puntos_medicion'):
            par = ('', datos.get('unidad_equipo') or '')
            if par not in nombres:
                nombres.append(par)
    return nombres


def solicitar_lectura(calibracion, usuario=None, origen='individual', despertar=True):
    """
    Crea (o reinicia) la lectura de una calibración y la deja en cola.
    Devuelve la LecturaCertificado. No vuelve a encolar una que ya está en curso.
    """
    from core.models import LecturaCertificado

    if not calibracion.documento_calibracion:
        raise ErrorLectura('Esta calibración no tiene el PDF del certificado cargado.')

    with transaction.atomic():
        lectura, creada = LecturaCertificado.objects.select_for_update().get_or_create(
            calibracion=calibracion,
            defaults={'empresa_id': calibracion.equipo.empresa_id, 'solicitado_por': usuario,
                      'origen': origen},
        )
        if not creada and not lectura.en_curso:
            lectura.estado = LecturaCertificado.ESTADO_PENDIENTE
            lectura.intentos = 0
            lectura.mensaje_error = ''
            lectura.solicitado_por = usuario
            lectura.origen = origen
            lectura.iniciado_en = None
            lectura.terminado_en = None
            lectura.save()

    if despertar:
        despertar_despachador()
    return lectura


def _recuperar_abandonadas():
    """Lecturas que quedaron en 'procesando' por un reinicio vuelven a la cola (o fallan tras 3 intentos)."""
    from core.models import LecturaCertificado

    limite = timezone.now() - timedelta(minutes=MINUTOS_LECTURA_ABANDONADA)
    abandonadas = LecturaCertificado.objects.filter(
        estado=LecturaCertificado.ESTADO_PROCESANDO, iniciado_en__lt=limite)
    abandonadas.filter(intentos__gte=MAX_INTENTOS).update(
        estado=LecturaCertificado.ESTADO_FALLO, terminado_en=timezone.now(),
        mensaje_error='La lectura se interrumpió varias veces. Intenta de nuevo.')
    abandonadas.filter(intentos__lt=MAX_INTENTOS).update(estado=LecturaCertificado.ESTADO_PENDIENTE)


def tomar_siguiente():
    """Reserva la siguiente lectura pendiente (seguro aunque haya varios procesos)."""
    from core.models import LecturaCertificado

    _recuperar_abandonadas()
    candidatas = LecturaCertificado.objects.filter(
        estado=LecturaCertificado.ESTADO_PENDIENTE).order_by('creado').values_list('id', flat=True)[:5]
    for lectura_id in candidatas:
        reservada = LecturaCertificado.objects.filter(
            id=lectura_id, estado=LecturaCertificado.ESTADO_PENDIENTE,
        ).update(estado=LecturaCertificado.ESTADO_PROCESANDO, iniciado_en=timezone.now(),
                 intentos=F('intentos') + 1)
        if reservada:
            return LecturaCertificado.objects.select_related(
                'calibracion', 'calibracion__equipo').get(id=lectura_id)
    return None


def procesar_lectura(lectura):
    """Lee el PDF de una lectura ya reservada y guarda el resultado. Nunca lanza excepción."""
    from core.models import LecturaCertificado

    calibracion = lectura.calibracion
    try:
        if not calibracion.documento_calibracion:
            raise ErrorLectura('La calibración ya no tiene el PDF del certificado.')
        with calibracion.documento_calibracion.open('rb') as archivo:
            pdf_bytes = archivo.read()

        datos, info = leer_pdf_con_gemini(pdf_bytes)
        propuesta = construir_propuesta(datos, equipo=calibracion.equipo, calibracion=calibracion,
                                        nombres_previos=nombres_previos_equipo(calibracion))

        lectura.resultado_crudo = datos
        lectura.propuesta = propuesta
        lectura.modelo_ia = modelo_configurado()
        lectura.tokens_entrada = info['tokens_entrada']
        lectura.tokens_salida = info['tokens_salida']
        lectura.segundos = info['segundos']
        lectura.estado = LecturaCertificado.ESTADO_LISTO
        lectura.mensaje_error = ''
        lectura.terminado_en = timezone.now()
        lectura.save()
        logger.info(f"Lectura IA lista: calibración {calibracion.id}, {info['segundos']} s, "
                    f"{len(propuesta['magnitudes'])} variables")
    except ErrorLectura as exc:
        lectura.marcar_fallo(str(exc))
    except Exception as exc:  # noqa: BLE001 — una lectura que falla no debe tumbar la cola
        logger.error(f'Lectura IA falló (calibración {calibracion.id}): {exc}', exc_info=True)
        mensaje = str(exc)
        if '402' in mensaje or 'prepayment' in mensaje.lower() or 'RESOURCE_EXHAUSTED' in mensaje:
            mensaje = 'Se acabó el saldo de la cuenta de Gemini. Avísale al administrador de SAM.'
        else:
            mensaje = 'No se pudo leer el certificado. Intenta de nuevo en unos minutos.'
        lectura.marcar_fallo(mensaje)


def procesar_pendientes(maximo=None):
    """Procesa lecturas pendientes una tras otra. Devuelve cuántas procesó."""
    procesadas = 0
    while maximo is None or procesadas < maximo:
        lectura = tomar_siguiente()
        if lectura is None:
            break
        procesar_lectura(lectura)
        procesadas += 1
    return procesadas


_candado = threading.Lock()
_hilo = None


def _bucle_despachador():
    try:
        close_old_connections()
        procesar_pendientes()
    except Exception as exc:  # noqa: BLE001
        logger.error(f'Despachador de lecturas IA se detuvo: {exc}', exc_info=True)
    finally:
        close_old_connections()


def despertar_despachador():
    """
    Arranca el hilo que procesa la cola si no está corriendo en este proceso.
    Un hilo por proceso = como mucho una lectura a la vez por proceso de gunicorn.
    """
    global _hilo
    if not getattr(settings, 'LECTURA_IA_EN_SEGUNDO_PLANO', True):
        return
    with _candado:
        if _hilo is not None and _hilo.is_alive():
            return
        _hilo = threading.Thread(target=_bucle_despachador, name='lectura-certificados-ia', daemon=True)
        _hilo.start()


# =============================================================================
# 4. Lectura masiva por empresa
# =============================================================================

def candidatas_masivas(empresa):
    """
    Última calibración de cada equipo activo de la empresa que tiene el PDF del
    certificado, no tiene confirmación y no tiene una lectura en curso o lista.
    """
    from core.constants import ESTADO_DE_BAJA, ESTADO_INACTIVO
    from core.models import Calibracion, LecturaCertificado

    ultimas = {}
    calibraciones = (Calibracion.objects
                     .filter(equipo__empresa=empresa)
                     .exclude(equipo__estado__in=[ESTADO_DE_BAJA, ESTADO_INACTIVO])
                     .select_related('equipo')
                     .order_by('equipo_id', '-fecha_calibracion', '-id'))
    for cal in calibraciones:
        ultimas.setdefault(cal.equipo_id, cal)

    ocupadas = set(LecturaCertificado.objects.filter(
        calibracion__in=[c.id for c in ultimas.values()],
        estado__in=[LecturaCertificado.ESTADO_PENDIENTE, LecturaCertificado.ESTADO_PROCESANDO,
                    LecturaCertificado.ESTADO_LISTO],
    ).values_list('calibracion_id', flat=True))

    return [c for c in ultimas.values()
            if c.documento_calibracion and not calibracion_tiene_confirmacion(c) and c.id not in ocupadas]
