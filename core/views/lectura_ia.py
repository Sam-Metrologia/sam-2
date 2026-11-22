# core/views/lectura_ia.py
"""
Lectura automática de certificados de calibración con IA (Gemini).

- Individual: desde la pantalla de confirmación, el técnico pide leer el
  certificado de la calibración y la pantalla se precarga cuando está lista.
- Masiva: el superusuario lee de una vez la última calibración de cada equipo
  de una empresa que tenga el PDF del certificado y no tenga confirmación.
"""
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from core import lectura_certificados as lc
from core.models import Calibracion, Empresa, LecturaCertificado
from core.monitoring import monitor_view
from .base import access_check, trial_check
from ..tenancy import get_empresa_activa

logger = logging.getLogger('core')


def _calibracion_del_usuario(request, calibracion_id):
    """La calibración, solo si pertenece a la empresa activa del usuario (404 si no)."""
    if request.user.is_superuser:
        return get_object_or_404(Calibracion.objects.select_related('equipo'), id=calibracion_id)
    return get_object_or_404(Calibracion.objects.select_related('equipo'), id=calibracion_id,
                             equipo__empresa=get_empresa_activa(request))


def estado_lectura_json(lectura):
    if lectura is None:
        return {'estado': 'ninguna'}
    return {
        'estado': lectura.estado,
        'estado_texto': lectura.get_estado_display(),
        'mensaje': lectura.mensaje_error,
        'variables': len((lectura.propuesta or {}).get('magnitudes') or []),
    }


@monitor_view
@access_check
@login_required
@trial_check
@permission_required('core.can_change_calibracion', raise_exception=True)
@require_POST
def solicitar_lectura_certificado(request, calibracion_id):
    calibracion = _calibracion_del_usuario(request, calibracion_id)
    if lc.calibracion_tiene_confirmacion(calibracion):
        return JsonResponse({'estado': 'error',
                             'mensaje': 'Esta calibración ya tiene confirmación guardada.'}, status=400)
    try:
        lectura = lc.solicitar_lectura(calibracion, usuario=request.user)
    except lc.ErrorLectura as exc:
        return JsonResponse({'estado': 'error', 'mensaje': str(exc)}, status=400)
    return JsonResponse(estado_lectura_json(lectura))


@login_required
@permission_required('core.can_view_calibracion', raise_exception=True)
@require_http_methods(['GET'])
def estado_lectura_certificado(request, calibracion_id):
    calibracion = _calibracion_del_usuario(request, calibracion_id)
    lectura = LecturaCertificado.objects.filter(calibracion=calibracion).first()
    if lectura is not None and lectura.en_curso:
        # Si el servidor se reinició, la consulta de estado vuelve a poner la cola en marcha.
        lc.despertar_despachador()
    return JsonResponse(estado_lectura_json(lectura))


@monitor_view
@access_check
@login_required
@permission_required('core.can_change_calibracion', raise_exception=True)
@require_POST
def descartar_lectura_certificado(request, calibracion_id):
    """El técnico prefiere llenar la confirmación a mano: se borra la propuesta."""
    calibracion = _calibracion_del_usuario(request, calibracion_id)
    LecturaCertificado.objects.filter(calibracion=calibracion).exclude(
        estado=LecturaCertificado.ESTADO_PROCESANDO).delete()
    return JsonResponse({'estado': 'ninguna'})


@login_required
@require_http_methods(['GET'])
def lectura_certificados_indice(request):
    """Solo superusuario: todas las empresas con lo que tienen por leer y por revisar."""
    if not request.user.is_superuser:
        return HttpResponseForbidden('Solo el administrador de SAM puede usar la lectura masiva.')

    from django.db.models import Count, Q

    lecturas = dict()
    for fila in (LecturaCertificado.objects.values('empresa_id').annotate(
            por_revisar=Count('id', filter=Q(estado=LecturaCertificado.ESTADO_LISTO,
                                             calibracion__confirmacion_metrologica_datos__isnull=True)),
            en_curso=Count('id', filter=Q(estado__in=[LecturaCertificado.ESTADO_PENDIENTE,
                                                      LecturaCertificado.ESTADO_PROCESANDO])),
            fallidas=Count('id', filter=Q(estado=LecturaCertificado.ESTADO_FALLO)))):
        lecturas[fila['empresa_id']] = fila

    # Solo empresas que tienen al menos una calibración con el PDF del certificado.
    empresas = (Empresa.objects.filter(is_deleted=False, equipos__calibraciones__documento_calibracion__gt='')
                .distinct().order_by('nombre'))
    filas = []
    for empresa in empresas:
        datos = lecturas.get(empresa.id, {})
        filas.append({
            'empresa': empresa,
            'por_leer': len(lc.candidatas_masivas(empresa)),
            'por_revisar': datos.get('por_revisar', 0),
            'en_curso': datos.get('en_curso', 0),
            'fallidas': datos.get('fallidas', 0),
        })
    filas.sort(key=lambda f: (-(f['por_leer'] + f['por_revisar'] + f['en_curso']), f['empresa'].nombre))
    return render(request, 'core/lectura_certificados_indice.html', {
        'filas': filas, 'titulo_pagina': 'Lectura de certificados con IA'})


@login_required
@require_POST
def detener_lectura_masiva(request, empresa_id):
    """
    Solo superusuario: cancela la lectura masiva en espera de una empresa. Las que están en
    cola vuelven a quedar "por leer"; la que se está leyendo en ese momento termina (la
    llamada a Gemini ya está hecha). No toca las lecturas individuales que pidieron los técnicos.
    """
    if not request.user.is_superuser:
        return HttpResponseForbidden('Solo el administrador de SAM puede usar la lectura masiva.')
    empresa = get_object_or_404(Empresa, id=empresa_id)
    canceladas, _ = LecturaCertificado.objects.filter(
        empresa=empresa, origen=LecturaCertificado.ORIGEN_MASIVA,
        estado=LecturaCertificado.ESTADO_PENDIENTE).delete()
    procesando = LecturaCertificado.objects.filter(
        empresa=empresa, estado=LecturaCertificado.ESTADO_PROCESANDO).count()
    mensaje = f'Lectura detenida: se cancelaron {canceladas} certificado(s) en espera.'
    if procesando:
        mensaje += f' {procesando} que ya se estaba(n) leyendo terminará(n) en unos segundos.'
    messages.success(request, mensaje)
    return redirect('core:lectura_masiva_empresa', empresa_id=empresa.id)


@login_required
@require_http_methods(['GET', 'POST'])
def lectura_masiva_empresa(request, empresa_id):
    """Solo superusuario: lee de una vez los certificados pendientes de una empresa."""
    if not request.user.is_superuser:
        return HttpResponseForbidden('Solo el administrador de SAM puede usar la lectura masiva.')

    empresa = get_object_or_404(Empresa, id=empresa_id)

    if request.method == 'POST':
        candidatas = lc.candidatas_masivas(empresa)
        encoladas = 0
        for calibracion in candidatas:
            try:
                lc.solicitar_lectura(calibracion, usuario=request.user,
                                     origen=LecturaCertificado.ORIGEN_MASIVA, despertar=False)
                encoladas += 1
            except lc.ErrorLectura as exc:
                logger.warning(f'Lectura masiva: calibración {calibracion.id} omitida: {exc}')
        if encoladas:
            lc.despertar_despachador()
            messages.success(request, f'Se pusieron en cola {encoladas} certificados de {empresa.nombre}.')
        else:
            messages.info(request, 'No hay certificados pendientes por leer en esta empresa.')
        return redirect('core:lectura_masiva_empresa', empresa_id=empresa.id)

    lecturas = (LecturaCertificado.objects.filter(empresa=empresa)
                .select_related('calibracion', 'calibracion__equipo')
                .order_by('estado', '-creado'))
    if any(l.en_curso for l in lecturas):
        lc.despertar_despachador()

    conteo = {estado: 0 for estado, _ in LecturaCertificado.ESTADOS}
    for lectura in lecturas:
        conteo[lectura.estado] += 1

    candidatas = lc.candidatas_masivas(empresa)
    context = {
        'empresa': empresa,
        'candidatas': candidatas,
        'lecturas': lecturas,
        'conteo': conteo,
        'en_curso': conteo[LecturaCertificado.ESTADO_PENDIENTE] + conteo[LecturaCertificado.ESTADO_PROCESANDO],
        'titulo_pagina': f'Lectura de certificados — {empresa.nombre}',
    }
    return render(request, 'core/lectura_masiva_empresa.html', context)
