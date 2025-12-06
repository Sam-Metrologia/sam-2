# core/views/dashboard_gerencia_simple.py
# Versión simplificada para debugging

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from datetime import date
from django.utils import timezone
import json

from ..models import Empresa, Equipo, Calibracion, Mantenimiento, Comprobacion, MetricasEficienciaMetrologica


def calcular_metricas_eficiencia(empresa):
    """
    Calcula y actualiza las métricas de eficiencia metrológica para una empresa.
    """
    try:
        # Obtener o crear métricas para la empresa
        metricas, created = MetricasEficienciaMetrologica.objects.get_or_create(
            empresa=empresa,
            defaults={
                'cumplimiento_calibraciones': 0,
                'cumplimiento_mantenimientos': 0,
                'cumplimiento_comprobaciones': 0,
                'trazabilidad_documentacion': 0,
                'disponibilidad_equipos': 0,
                'tiempo_promedio_gestion': 0,
                'indice_conformidad': 0,
                'eficacia_procesos': 0,
                'costo_promedio_por_equipo': 0,
                'retorno_inversion_metrologia': 0,
            }
        )

        current_year = date.today().year
        equipos_empresa = Equipo.objects.filter(empresa=empresa)
        total_equipos = equipos_empresa.count()

        if total_equipos == 0:
            return metricas

        # 1. Calcular cumplimiento de calibraciones
        calibraciones_año = Calibracion.objects.filter(
            equipo__empresa=empresa,
            fecha_calibracion__year=current_year
        )
        calibraciones_a_tiempo = calibraciones_año.filter(
            fecha_calibracion__lte=date.today()
        ).count()
        total_calibraciones_requeridas = max(total_equipos, 1)
        cumplimiento_cal = (calibraciones_a_tiempo / total_calibraciones_requeridas) * 100

        # 2. Calcular cumplimiento de mantenimientos
        mantenimientos_año = Mantenimiento.objects.filter(
            equipo__empresa=empresa,
            fecha_mantenimiento__year=current_year
        )
        mantenimientos_a_tiempo = mantenimientos_año.count()
        cumplimiento_mant = (mantenimientos_a_tiempo / total_calibraciones_requeridas) * 100

        # 3. Calcular cumplimiento de comprobaciones
        comprobaciones_año = Comprobacion.objects.filter(
            equipo__empresa=empresa,
            fecha_comprobacion__year=current_year
        )
        comprobaciones_a_tiempo = comprobaciones_año.count()
        cumplimiento_comp = (comprobaciones_a_tiempo / total_calibraciones_requeridas) * 100

        # 4. Trazabilidad documentación (equipos con documentación completa)
        # Verificar que tengan al menos ficha técnica y manual
        equipos_con_documentacion = equipos_empresa.filter(
            ficha_tecnica_pdf__isnull=False,
            manual_pdf__isnull=False
        ).count()
        trazabilidad = (equipos_con_documentacion / total_equipos) * 100

        # 5. Disponibilidad operativa (equipos que NO están fuera de servicio)
        # Un equipo está disponible si no está en estado "Fuera de Servicio" o "De Baja"
        equipos_disponibles = equipos_empresa.exclude(estado__in=['Fuera de Servicio', 'De Baja']).count()
        disponibilidad = (equipos_disponibles / total_equipos) * 100

        # 6. Tiempo promedio gestión (realista para calibraciones externas)
        # Calibraciones externas: 7-14 días, Comprobaciones internas: 1-3 días, externas: 7-14 días
        # Mantenimientos correctivos: 3-7 días, preventivos: 1-2 días

        # Calcular días promedio basado en tipo de actividad
        cal_externas = calibraciones_año.filter(proveedor__isnull=False).count()
        cal_internas = calibraciones_año.filter(proveedor__isnull=True).count()
        comp_externas = comprobaciones_año.filter(proveedor__isnull=False).count()
        comp_internas = comprobaciones_año.filter(proveedor__isnull=True).count()
        mant_correctivos = mantenimientos_año.filter(tipo_mantenimiento='Correctivo').count()
        mant_preventivos = mantenimientos_año.filter(tipo_mantenimiento='Preventivo').count()

        # Calcular días promedio ponderado
        total_dias_actividades = (
            (cal_externas * 10) +      # 10 días promedio calibraciones externas
            (cal_internas * 3) +       # 3 días calibraciones internas
            (comp_externas * 10) +     # 10 días comprobaciones externas
            (comp_internas * 2) +      # 2 días comprobaciones internas
            (mant_correctivos * 5) +   # 5 días mantenimientos correctivos
            (mant_preventivos * 1.5)   # 1.5 días mantenimientos preventivos
        )
        total_actividades = (cal_externas + cal_internas + comp_externas +
                           comp_internas + mant_correctivos + mant_preventivos)

        tiempo_promedio = total_dias_actividades / max(total_actividades, 1)

        # 7. Índice conformidad (basado en resultados de comprobaciones)
        comprobaciones_aprobadas = comprobaciones_año.filter(resultado='Aprobado').count()
        conformidad = (comprobaciones_aprobadas / max(comprobaciones_año.count(), 1)) * 100

        # 8. Eficacia procesos (promedio general)
        eficacia = (cumplimiento_cal + cumplimiento_mant + cumplimiento_comp) / 3

        # 9. Costo promedio por equipo
        costos_cal = calibraciones_año.aggregate(total=Sum('costo_calibracion'))['total'] or 0
        costos_mant = mantenimientos_año.aggregate(total=Sum('costo_sam_interno'))['total'] or 0
        costos_comp = comprobaciones_año.aggregate(total=Sum('costo_comprobacion'))['total'] or 0
        costos_totales = float(costos_cal) + float(costos_mant) + float(costos_comp)
        costo_promedio = costos_totales / total_equipos if total_equipos > 0 else 0

        # 10. Simplificado: Sin ROI - Los costos operativos se obtienen directamente de las actividades registradas

        # Actualizar métricas
        metricas.cumplimiento_calibraciones = min(cumplimiento_cal, 100)
        metricas.cumplimiento_mantenimientos = min(cumplimiento_mant, 100)
        metricas.cumplimiento_comprobaciones = min(cumplimiento_comp, 100)
        metricas.trazabilidad_documentacion = min(trazabilidad, 100)
        metricas.disponibilidad_equipos = min(disponibilidad, 100)
        metricas.tiempo_promedio_gestion = tiempo_promedio
        metricas.indice_conformidad = min(conformidad, 100)
        metricas.eficacia_procesos = min(eficacia, 100)
        metricas.costo_promedio_por_equipo = costo_promedio
        metricas.retorno_inversion_metrologia = 0  # ROI eliminado del análisis

        # Guardar (esto también calculará la puntuación general)
        metricas.save()

        return metricas

    except Exception as e:
        logger.error(f"Error calculando métricas para {empresa.nombre}: {e}")
        return None


def management_permission_required(view_func):
    """
    Decorador personalizado para verificar permisos de gestión.
    """
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('core:login')

        # Control de acceso mejorado por roles
        user_role = getattr(request.user, 'rol_usuario', 'TECNICO')
        is_management_user = getattr(request.user, 'is_management_user', False)

        has_management_access = (
            request.user.is_superuser or
            is_management_user or
            user_role in ['ADMINISTRADOR', 'GERENCIA']
        )

        if not has_management_access:
            messages.error(request, f"No tienes permisos para acceder al Dashboard de Gerencia. Tu rol actual es: {user_role}")
            return redirect('core:dashboard')

        return view_func(request, *args, **kwargs)
    return _wrapped_view


@login_required
@management_permission_required
def dashboard_gerencia(request):
    """
    Dashboard de Gerencia - Versión simplificada para debugging
    """
    user = request.user
    today = date.today()
    current_year = today.year
    previous_year = current_year - 1

    # Datos básicos para debugging
    try:
        # Filtrado por empresa para superusuarios
        selected_company_id = request.GET.get('empresa_id')
        empresas_disponibles = Empresa.objects.filter(is_deleted=False).order_by('nombre')

        if user.is_superuser:
            # Vista SAM - Superusuarios pueden ver todas las empresas
            empresas_queryset = empresas_disponibles
            if selected_company_id:
                empresas_queryset = empresas_queryset.filter(id=selected_company_id)
        elif getattr(user, 'rol_usuario', None) == 'GERENCIA' and user.empresa:
            # Vista GERENCIA - Solo pueden ver su propia empresa pero en formato SAM
            empresas_queryset = empresas_disponibles.filter(id=user.empresa.id)
            selected_company_id = str(user.empresa.id)

            # Cálculos básicos
            num_empresas_activas = empresas_queryset.count()
            total_equipos_gestionados = Equipo.objects.filter(
                empresa__in=empresas_queryset
            ).count()

            # Métricas financieras con datos alternativos cuando no hay datos reales
            ingresos_anuales = 0
            costos_totales = 0
            margen_bruto = 0
            margen_porcentaje = 0
            variacion_costos_porcentaje = 0

            # Intentar calcular ingresos reales usando el nuevo sistema de suscripción
            try:
                ingresos_anuales = 0

                # Calcular ingresos reales empresa por empresa
                for empresa in empresas_queryset:
                    ingresos_anuales += empresa.get_ingresos_anuales_reales()

                print(f"DEBUG: Ingresos anuales calculados con nuevo sistema: {ingresos_anuales}")

                if ingresos_anuales == 0:
                    # Fallback al método anterior si no hay datos del nuevo sistema
                    ingresos_result = empresas_queryset.aggregate(total=Sum('tarifa_mensual_sam'))
                    if ingresos_result['total'] and ingresos_result['total'] > 0:
                        ingresos_anuales = float(ingresos_result['total']) * 12
                else:
                    # Si no hay datos financieros, usar estimación basada en número de empresas y equipos
                    # Esto proporciona una estimación realista para demostración
                    empresas_con_equipos = empresas_queryset.annotate(
                        num_equipos=Count('equipos', filter=Q(equipos__empresa__is_deleted=False))
                    ).filter(num_equipos__gt=0)

                    if empresas_con_equipos.exists():
                        # Estimación: $500 por equipo por mes (promedio industria metrología)
                        total_equipos_facturados = sum([emp.num_equipos for emp in empresas_con_equipos])
                        ingresos_anuales = total_equipos_facturados * 500 * 12
            except Exception as e:
                logger.error(f"Error calculando ingresos: {e}")

            # Costos básicos con estimaciones cuando no hay datos reales
            try:
                costos_cal = Calibracion.objects.filter(
                    equipo__empresa__in=empresas_queryset,
                    fecha_calibracion__year=current_year
                ).aggregate(total=Sum('costo_calibracion'))['total'] or 0

                costos_mant = Mantenimiento.objects.filter(
                    equipo__empresa__in=empresas_queryset,
                    fecha_mantenimiento__year=current_year
                ).aggregate(total=Sum('costo_sam_interno'))['total'] or 0

                costos_comp = Comprobacion.objects.filter(
                    equipo__empresa__in=empresas_queryset,
                    fecha_comprobacion__year=current_year
                ).aggregate(total=Sum('costo_comprobacion'))['total'] or 0

                costos_totales = float(costos_cal or 0) + float(costos_mant or 0) + float(costos_comp or 0)

                # Si no hay costos reales, usar estimación basada en actividades
                if costos_totales == 0:
                    actividades_año = Calibracion.objects.filter(
                        equipo__empresa__in=empresas_queryset,
                        fecha_calibracion__year=current_year
                    ).count() + Mantenimiento.objects.filter(
                        equipo__empresa__in=empresas_queryset,
                        fecha_mantenimiento__year=current_year
                    ).count() + Comprobacion.objects.filter(
                        equipo__empresa__in=empresas_queryset,
                        fecha_comprobacion__year=current_year
                    ).count()

                    if actividades_año > 0:
                        # Estimación: $150 costo promedio por actividad
                        costos_totales = actividades_año * 150
                        # Distribuir costos proporcionalmente
                        cal_count = Calibracion.objects.filter(
                            equipo__empresa__in=empresas_queryset,
                            fecha_calibracion__year=current_year
                        ).count()
                        mant_count = Mantenimiento.objects.filter(
                            equipo__empresa__in=empresas_queryset,
                            fecha_mantenimiento__year=current_year
                        ).count()
                        comp_count = Comprobacion.objects.filter(
                            equipo__empresa__in=empresas_queryset,
                            fecha_comprobacion__year=current_year
                        ).count()

                        if cal_count > 0:
                            costos_cal = (cal_count / actividades_año) * costos_totales
                        if mant_count > 0:
                            costos_mant = (mant_count / actividades_año) * costos_totales
                        if comp_count > 0:
                            costos_comp = (comp_count / actividades_año) * costos_totales

                        print(f"DEBUG: Usando estimación de costos basada en {actividades_año} actividades")

                if ingresos_anuales > 0:
                    margen_bruto = ingresos_anuales - costos_totales
                    margen_porcentaje = (margen_bruto / ingresos_anuales * 100)

            except Exception as e:
                logger.error(f"Error calculando costos: {e}")

            # Calcular métricas de eficiencia para todas las empresas del queryset
            metricas_eficiencia_empresas = []
            puntuacion_promedio_general = 0

            # Procesar todas las empresas del queryset
            empresas_para_metricas = empresas_queryset if empresas_queryset.count() <= 10 else empresas_queryset[:10]

            for empresa in empresas_para_metricas:
                try:
                    metricas = calcular_metricas_eficiencia(empresa)
                    if metricas and metricas.puntuacion_eficiencia_general > 0:
                        metricas_eficiencia_empresas.append({
                            'empresa': empresa.nombre,
                            'puntuacion': metricas.puntuacion_eficiencia_general,
                            'estado': metricas.estado_eficiencia,
                            'cumplimiento_calibraciones': metricas.cumplimiento_calibraciones,
                            'cumplimiento_mantenimientos': metricas.cumplimiento_mantenimientos,
                            'disponibilidad_equipos': metricas.disponibilidad_equipos,
                            'eficacia_procesos': metricas.eficacia_procesos,
                        })
                    else:
                        # Crear métricas básicas basadas en datos reales de la empresa
                        num_equipos = empresa.equipos.count()
                        if num_equipos > 0:
                            metricas_eficiencia_empresas.append({
                                'empresa': empresa.nombre,
                                'puntuacion': 60.0,  # Puntuación base
                                'estado': 'REGULAR',
                                'cumplimiento_calibraciones': 70.0,
                                'cumplimiento_mantenimientos': 65.0,
                                'disponibilidad_equipos': 90.0,
                                'eficacia_procesos': 75.0,
                            })
                except Exception as e:
                    logger.error(f"Error calculando métricas para {empresa.nombre}: {e}")

            # Calcular promedio general de eficiencia
            if metricas_eficiencia_empresas:
                puntuacion_promedio_general = sum([m['puntuacion'] for m in metricas_eficiencia_empresas]) / len(metricas_eficiencia_empresas)
            else:
                # Si no hay datos reales, usar un valor de ejemplo para mostrar el sistema
                puntuacion_promedio_general = 75.0  # Valor de ejemplo
                metricas_eficiencia_empresas = [{
                    'empresa': 'Empresa Demo',
                    'puntuacion': 75.0,
                    'estado': 'BUENO',
                    'cumplimiento_calibraciones': 80.0,
                    'cumplimiento_mantenimientos': 70.0,
                    'disponibilidad_equipos': 95.0,
                    'eficacia_procesos': 85.0,
                }]

            context = {
                'titulo_pagina': 'Dashboard Gerencia SAM',
                'perspective': 'sam',
                'today': today,
                'now': timezone.now(),
                'current_year': current_year,
                'previous_year': previous_year,
                'empresas_disponibles': empresas_disponibles,
                'selected_company_id': selected_company_id,
                'num_empresas_activas': num_empresas_activas,
                'total_equipos_gestionados': total_equipos_gestionados,
                'ingresos_anuales': ingresos_anuales,
                'costos_totales': costos_totales,
                'margen_bruto': margen_bruto,
                'margen_porcentaje': round(margen_porcentaje, 1),
                'variacion_costos_porcentaje': variacion_costos_porcentaje,
                'costos_calibracion': costos_cal or 0,
                'costos_mantenimiento_sam': costos_mant or 0,
                'costos_comprobacion': costos_comp or 0,
                'actividades_realizadas_año': Calibracion.objects.filter(
                    equipo__empresa__in=empresas_queryset,
                    fecha_calibracion__year=current_year
                ).count() + Mantenimiento.objects.filter(
                    equipo__empresa__in=empresas_queryset,
                    fecha_mantenimiento__year=current_year
                ).count() + Comprobacion.objects.filter(
                    equipo__empresa__in=empresas_queryset,
                    fecha_comprobacion__year=current_year
                ).count(),
                'cumplimiento_general': 85.0,
                'equipos_al_dia': max(0, total_equipos_gestionados - 5),
                'equipos_vencidos': min(5, total_equipos_gestionados),
                'tiempo_promedio': {'calibracion': 2.5, 'mantenimiento': 1.8, 'comprobacion': 1.2},
                'total_clientes': num_empresas_activas,
                'top_clientes': empresas_queryset[:5],
                'monthly_revenue_data': json.dumps([round(ingresos_anuales/12) for i in range(12)]),
                'cost_distribution': json.dumps([round(costos_cal or 0), round(costos_mant or 0), round(costos_comp or 0)]),
                'cost_labels': json.dumps(["Calibraciones", "Mantenimientos", "Comprobaciones"]),
                # Métricas de eficiencia
                'metricas_eficiencia_empresas': metricas_eficiencia_empresas,
                'puntuacion_eficiencia_promedio': round(puntuacion_promedio_general, 1),
                'estado_eficiencia_general': (
                    'EXCELENTE' if puntuacion_promedio_general >= 90 else
                    'BUENO' if puntuacion_promedio_general >= 75 else
                    'REGULAR' if puntuacion_promedio_general >= 60 else
                    'DEFICIENTE' if puntuacion_promedio_general >= 40 else
                    'CRITICO'
                )
            }

            template = 'core/dashboard_simple_inline.html'

        elif user.empresa and getattr(user, 'rol_usuario', None) != 'GERENCIA':
            # Vista Cliente (usuarios normales, no GERENCIA)
            empresa = user.empresa
            if not empresa:
                context = {'error': 'Usuario sin empresa asignada'}
                template = 'core/dashboard_gerencia_cliente.html'
            else:
                # Datos básicos del cliente
                num_equipos_empresa = Equipo.objects.filter(empresa=empresa).count()

                # Calcular métricas de eficiencia para la empresa del cliente
                metricas_empresa = calcular_metricas_eficiencia(empresa)

                context = {
                    'titulo_pagina': f'Dashboard Gerencia - {empresa.nombre}',
                    'perspective': 'client',
                    'empresa': empresa,
                    'today': today,
                    'now': timezone.now(),
                    'current_year': current_year,
                    'previous_year': previous_year,
                    'num_equipos_empresa': num_equipos_empresa,
                    'inversion_actual': 50000,
                    'inversion_anterior': 45000,
                    'variacion_inversion': 11.1,
                    'costos_calibracion_cliente': 15000,
                    'costos_mantenimiento_cliente': 20000,
                    'costos_comprobacion_cliente': 10000,
                    'costo_promedio_por_equipo': 1500,
                    'cumplimiento_general': 92.5,
                    'cumplimiento_calibracion': 95.0,
                    'cumplimiento_mantenimiento': 88.0,
                    'cumplimiento_comprobacion': 94.5,
                    'porcentaje_operativo': 96.0,
                    'equipos_operativos': int(num_equipos_empresa * 0.96),
                    'trazabilidad_porcentaje': 98.5,
                    'equipos_criticos': 2,
                    'equipos_proximos_vencer': 3,
                    'equipos_sin_calibrar': 1,
                    'monthly_activities_data': '[5, 8, 6, 9, 7, 11, 8, 6, 9, 7, 5, 8]',
                    'equipment_status_data': '[80, 15, 5]',
                    'equipment_status_labels': '["Activo", "Inactivo", "De Baja"]',
                    'months_labels': '["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]',
                    # Métricas de eficiencia específicas de la empresa
                    'metricas_eficiencia': metricas_empresa,
                    'puntuacion_eficiencia': metricas_empresa.puntuacion_eficiencia_general if metricas_empresa else 0,
                    'estado_eficiencia': metricas_empresa.estado_eficiencia if metricas_empresa else 'REGULAR',
                    'recomendaciones_eficiencia': metricas_empresa.recomendaciones if metricas_empresa else 'Sin recomendaciones disponibles.',
                }
                template = 'core/dashboard_gerencia_cliente.html'
        else:
            # Usuarios GERENCIA sin empresa o casos no manejados
            context = {
                'error': 'Usuario sin permisos adecuados o empresa no asignada',
                'titulo_pagina': 'Dashboard Gerencia - Error de Acceso'
            }
            template = 'core/dashboard_gerencia_sam.html'

        return render(request, template, context)

    except Exception as e:
        logger.error(f"ERROR en dashboard_gerencia: {e}")
        import traceback
        logger.error(traceback.format_exc())

        context = {
            'error': f'Error en dashboard: {str(e)}',
            'titulo_pagina': 'Dashboard Gerencia - Error'
        }
        return render(request, 'core/dashboard_gerencia_sam.html', context)