# core/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test, permission_required
from django.contrib import messages
from django.db.models import Q, Count
from django.db import models
from datetime import date, timedelta, datetime
import calendar
import io
import json
import os
import zipfile
from collections import defaultdict
import decimal

# IMPORTACIONES ADICIONALES PARA LA IMPORTACIÓN DE EXCEL
import openpyxl
from django.db import transaction
from django.utils.dateparse import parse_date

from django.http import HttpResponse, JsonResponse, Http404, HttpResponseRedirect

from openpyxl import Workbook
from openpyxl.styles import Font, Border, Side, Alignment, PatternFill
from openpyxl.drawing.image import Image as ExcelImage

from dateutil.relativedelta import relativedelta

from django.conf import settings
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from django.utils.html import mark_safe

# Importar para PDF
from django.template.loader import get_template
from weasyprint import HTML

# Importar los formularios de tu aplicación (asegúrate de que todos estos existan en .forms)
from .forms import (
    CalibracionForm, MantenimientoForm, ComprobacionForm, EquipoForm,
    BajaEquipoForm, EmpresaForm, CustomUserCreationForm, CustomUserChangeForm,
    UbicacionForm, ProcedimientoForm, ProveedorCalibracionForm,
    ProveedorMantenimientoForm, ProveedorComprobacionForm, ProveedorForm,
    AuthenticationForm, UserProfileForm, EmpresaFormatoForm,
    ExcelUploadForm
)

# Importar modelos
from .models import (
    Equipo, Calibracion, Mantenimiento, Comprobacion, BajaEquipo, Empresa,
    CustomUser, Ubicacion, Procedimiento, ProveedorCalibracion,
    ProveedorMantenimiento, ProveedorComprobacion, Proveedor
)

# Importar para autenticación
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash

from django.contrib.auth.forms import PasswordChangeForm # Asegúrate de que esta importación esté presente

# Importar para manejo de mensajes AJAX
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST


# --- Vistas de Autenticación y Perfil ---

def user_login(request):
    """
    Handles user login.
    """
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'¡Bienvenido, {username}!')
                return redirect('core:dashboard')
            else:
                messages.error(request, 'Nombre de usuario o contraseña incorrectos.')
        else:
            messages.error(request, 'Por favor, corrige los errores del formulario.')
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})

@login_required
def user_logout(request):
    """
    Logs out the current user.
    """
    logout(request)
    messages.info(request, 'Has cerrado sesión exitosamente.')
    return redirect('core:login')

@login_required
def cambiar_password(request):
    """
    Handles changing the current user's password.
    """
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Tu contraseña ha sido actualizada exitosamente!')
            return redirect('core:password_change_done')
        else:
            messages.error(request, 'Por favor corrige los errores a continuación.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'registration/password_change_form.html', {
        'form': form,
        'titulo_pagina': 'Cambiar Contraseña'
    })

@login_required
def password_change_done(request):
    """
    Renders the password change done page.
    """
    return render(request, 'core/password_change_done.html', {'titulo_pagina': 'Contraseña Cambiada'})


# --- Función auxiliar para proyectar actividades y categorizarlas (para las gráficas de torta) ---
def get_projected_activities_for_year(equipment_queryset, activity_type, current_year, today):
    """
    Generates a list of projected activities for the current year for a given activity type.
    Each projected activity will have a 'date' and 'status' (realized, overdue, pending).
    This function is primarily for the annual summary (pie charts).
    """
    projected_activities = []
    
    # Filtrar equipos para excluir los que están "De Baja"
    equipment_queryset = equipment_queryset.exclude(estado='De Baja')

    # Fetch all realized activities for the current year for quick lookup
    realized_activities_for_year = []
    if activity_type == 'calibracion':
        realized_activities_for_year = Calibracion.objects.filter(
            equipo__in=equipment_queryset,
            fecha_calibracion__year=current_year
        ).values_list('equipo_id', 'fecha_calibracion')
        freq_attr = 'frecuencia_calibracion_meses'
        last_date_attr = 'fecha_ultima_calibracion'
    elif activity_type == 'comprobacion':
        realized_activities_for_year = Comprobacion.objects.filter(
            equipo__in=equipment_queryset,
            fecha_comprobacion__year=current_year
        ).values_list('equipo_id', 'fecha_comprobacion')
        freq_attr = 'frecuencia_comprobacion_meses'
        last_date_attr = 'fecha_ultima_comprobacion'
    else:
        return [] # Should not happen with current usage

    # Create a set of (equipo_id, year, month) for realized activities for quick lookup
    realized_set = set()
    for eq_id, date_obj in realized_activities_for_year:
        realized_set.add((eq_id, date_obj.year, date_obj.month))

    for equipo in equipment_queryset:
        freq_months = getattr(equipo, freq_attr)

        # Ensure freq_months is a positive number before proceeding
        if freq_months is None or freq_months <= 0:
            continue # Skip this equipment if frequency is not valid for projection

        plan_start_date = equipo.fecha_adquisicion if equipo.fecha_adquisicion else (equipo.fecha_registro.date() if equipo.fecha_registro else date(current_year, 1, 1))

        # Calculate the first projected date within the current year
        # We need to find the earliest 'plan_start_date' that is relevant for the current year.
        # If plan_start_date is in the past, calculate how many frequencies have passed
        # to get to a date roughly at the beginning of the current year.
        
        # Calculate difference in months from plan_start_date to beginning of current_year
        diff_months = (current_year - plan_start_date.year) * 12 + (1 - plan_start_date.month)
        
        # Calculate how many full frequency intervals have passed
        num_intervals = 0
        if freq_months > 0:
            num_intervals = max(0, (diff_months + freq_months - 1) // freq_months) # Ceiling division

        current_projection_date = plan_start_date + relativedelta(months=num_intervals * freq_months)

        # Now, project activities within the current year
        # Loop for a reasonable number of iterations to cover all possibilities within a year plus some buffer
        for _ in range(int(12 / freq_months) + 2 if freq_months > 0 else 12): 
            if current_projection_date.year == current_year:
                is_realized = (equipo.id, current_projection_date.year, current_projection_date.month) in realized_set

                status = ''
                if is_realized:
                    status = 'Realizado'
                elif current_projection_date < today:
                    status = 'No Cumplido' # Overdue and not realized
                else:
                    status = 'Pendiente/Programado' # Future and not realized

                projected_activities.append({
                    'equipo_id': equipo.id,
                    'date': current_projection_date,
                    'status': status
                })
            elif current_projection_date.year > current_year:
                break # Stop projecting if we've gone past the current year

            try:
                current_projection_date += relativedelta(months=int(freq_months))
            except OverflowError:
                break
    return projected_activities


@login_required
def dashboard(request):
    """
    Displays the dashboard with key metrics and charts.
    """
    user = request.user
    today = date.today()
    current_year = today.year
    
    # Filtrado por empresa para superusuarios
    selected_company_id = request.GET.get('empresa_id')
    empresas_disponibles = Empresa.objects.all().order_by('nombre')

    equipos_queryset = Equipo.objects.all()

    if not user.is_superuser:
        # Los usuarios normales solo ven datos de su propia empresa
        if user.empresa:
            equipos_queryset = equipos_queryset.filter(empresa=user.empresa)
            selected_company_id = str(user.empresa.id) # Asegurar que el filtro se aplique y muestre la empresa del usuario
        else:
            # Si un usuario normal no tiene empresa asignada, no ve equipos
            equipos_queryset = Equipo.objects.none()
            empresas_disponibles = Empresa.objects.none() # No hay empresas para filtrar

    if selected_company_id:
        equipos_queryset = equipos_queryset.filter(empresa_id=selected_company_id)

    # Excluir equipos "De Baja" de los cálculos del dashboard
    equipos_queryset = equipos_queryset.exclude(estado='De Baja')

    # --- Indicadores Clave ---
    total_equipos = equipos_queryset.count()
    equipos_activos = equipos_queryset.filter(estado='Activo').count()
    # Equipos de baja (para el dashboard general, no filtrados por empresa aquí, pero se puede añadir)
    equipos_de_baja = Equipo.objects.filter(estado='De Baja')
    if not user.is_superuser and user.empresa:
        equipos_de_baja = equipos_de_baja.filter(empresa=user.empresa)
    elif not user.is_superuser and not user.empresa:
        equipos_de_baja = Equipo.objects.none()
    if selected_company_id and user.is_superuser: # Si superuser selecciona una empresa, filtrar también los de baja
        equipos_de_baja = equipos_de_baja.filter(empresa_id=selected_company_id)
    equipos_de_baja = equipos_de_baja.count()


    # Detección de actividades vencidas y próximas
    # Se basan directamente en los campos proxima_X del modelo Equipo
    calibraciones_vencidas = equipos_queryset.filter(
        proxima_calibracion__isnull=False,
        proxima_calibracion__lt=today
    ).count()

    calibraciones_proximas = equipos_queryset.filter(
        proxima_calibracion__isnull=False,
        proxima_calibracion__gte=today,
        proxima_calibracion__lte=today + timedelta(days=30)
    ).count()

    mantenimientos_vencidos = equipos_queryset.filter(
        proximo_mantenimiento__isnull=False,
        proximo_mantenimiento__lt=today
    ).count()

    mantenimientos_proximas = equipos_queryset.filter(
        proximo_mantenimiento__isnull=False,
        proximo_mantenimiento__gte=today,
        proximo_mantenimiento__lte=today + timedelta(days=30)
    ).count()

    comprobaciones_vencidas = equipos_queryset.filter(
        proxima_comprobacion__isnull=False,
        proxima_comprobacion__lt=today
    ).count()

    comprobaciones_proximas = equipos_queryset.filter(
        proxima_comprobacion__isnull=False,
        proxima_comprobacion__gte=today,
        proxima_comprobacion__lte=today + timedelta(days=30)
    ).count()

    # --- Datos para Gráficas de Línea (Programadas vs Realizadas por Mes) ---
    # Rango de 6 meses antes y 6 meses después del mes actual
    line_chart_labels = []
    
    # Initialize programmed data arrays
    programmed_calibrations_line_data = [0] * 12
    programmed_mantenimientos_line_data = [0] * 12
    programmed_comprobaciones_line_data = [0] * 12

    realized_calibrations_line_data = [0] * 12
    realized_preventive_mantenimientos_line_data = [0] * 12
    realized_corrective_mantenimientos_line_data = [0] * 12
    realized_other_mantenimientos_line_data = [0] * 12
    realized_predictive_mantenimientos_line_data = [0] * 12 # Nuevo tipo
    realized_inspection_mantenimientos_line_data = [0] * 12 # Nuevo tipo
    realized_comprobaciones_line_data = [0] * 12

    # Calcular el primer mes del rango (6 meses antes del actual)
    start_date_range = today - relativedelta(months=6)
    # Ajustar al primer día del mes
    start_date_range = start_date_range.replace(day=1)

    for i in range(12):
        target_date = start_date_range + relativedelta(months=i)
        line_chart_labels.append(f"{calendar.month_abbr[target_date.month]}. {target_date.year}")

    # Datos "Realizadas" (basado en registros de actividad)
    calibraciones_realizadas_period = Calibracion.objects.filter(
        equipo__in=equipos_queryset,
        fecha_calibracion__gte=start_date_range,
        fecha_calibracion__lte=start_date_range + relativedelta(months=12, days=-1)
    )
    mantenimientos_realizados_period = Mantenimiento.objects.filter(
        equipo__in=equipos_queryset,
        fecha_mantenimiento__gte=start_date_range,
        fecha_mantenimiento__lte=start_date_range + relativedelta(months=12, days=-1)
    )
    comprobaciones_realizadas_period = Comprobacion.objects.filter(
        equipo__in=equipos_queryset,
        fecha_comprobacion__gte=start_date_range,
        fecha_comprobacion__lte=start_date_range + relativedelta(months=12, days=-1)
    )

    for cal in calibraciones_realizadas_period:
        month_index = ((cal.fecha_calibracion.year - start_date_range.year) * 12 + cal.fecha_calibracion.month - start_date_range.month)
        if 0 <= month_index < 12:
            realized_calibrations_line_data[month_index] += 1
    
    for mant in mantenimientos_realizados_period:
        month_index = ((mant.fecha_mantenimiento.year - start_date_range.year) * 12 + mant.fecha_mantenimiento.month - start_date_range.month)
        if 0 <= month_index < 12:
            if mant.tipo_mantenimiento == 'Preventivo':
                realized_preventive_mantenimientos_line_data[month_index] += 1
            elif mant.tipo_mantenimiento == 'Correctivo':
                realized_corrective_mantenimientos_line_data[month_index] += 1
            elif mant.tipo_mantenimiento == 'Predictivo':
                realized_predictive_mantenimientos_line_data[month_index] += 1
            elif mant.tipo_mantenimiento == 'Inspección':
                realized_inspection_mantenimientos_line_data[month_index] += 1
            else:
                realized_other_mantenimientos_line_data[month_index] += 1

    for comp in comprobaciones_realizadas_period:
        month_index = ((comp.fecha_comprobacion.year - start_date_range.year) * 12 + comp.fecha_comprobacion.month - start_date_range.month)
        if 0 <= month_index < 12:
            realized_comprobaciones_line_data[month_index] += 1

    # Datos "Programadas" (basado en un plan fijo anual desde la fecha de adquisición/registro)
    for equipo in equipos_queryset: # equipos_queryset ya excluye "De Baja"
        # Determinar la fecha de inicio del plan para este equipo (fecha de adquisición o registro)
        # Asegurarse de que plan_start_date sea un objeto date
        plan_start_date = equipo.fecha_adquisicion if equipo.fecha_adquisicion else \
                          (equipo.fecha_registro.date() if equipo.fecha_registro else date(current_year, 1, 1))

        # Calibraciones Programadas
        if equipo.frecuencia_calibracion_meses is not None and equipo.frecuencia_calibracion_meses > 0:
            freq = int(equipo.frecuencia_calibracion_meses)
            
            # Calcular la diferencia en meses desde plan_start_date hasta el inicio del rango de la gráfica
            diff_months = (start_date_range.year - plan_start_date.year) * 12 + (start_date_range.month - plan_start_date.month)
            
            # Calcular cuántos intervalos de frecuencia han pasado para llegar al inicio del rango
            num_intervals = 0
            if freq > 0: # Evitar división por cero
                num_intervals = max(0, (diff_months + freq - 1) // freq) # Ceiling division para asegurar que empezamos en o antes del rango

            current_plan_date = plan_start_date + relativedelta(months=num_intervals * freq)
            
            # Contar las actividades planificadas dentro del rango de 12 meses de la gráfica
            # Iterar solo por los 12 meses del rango de la gráfica más un pequeño buffer
            for _ in range(12 + freq): # Un buffer para asegurar que cubrimos todos los puntos
                if start_date_range <= current_plan_date < start_date_range + relativedelta(months=12):
                    month_index = ((current_plan_date.year - start_date_range.year) * 12 + current_plan_date.month - start_date_range.month)
                    if 0 <= month_index < 12:
                        programmed_calibrations_line_data[month_index] += 1
                
                # Si la fecha del plan ya superó el final de nuestro rango de 12 meses + buffer, podemos parar
                if current_plan_date >= start_date_range + relativedelta(months=12 + freq):
                    break
                
                try:
                    current_plan_date += relativedelta(months=freq)
                except OverflowError:
                    break


        # Mantenimientos Programados (misma lógica optimizada)
        if equipo.frecuencia_mantenimiento_meses is not None and equipo.frecuencia_mantenimiento_meses > 0:
            freq = int(equipo.frecuencia_mantenimiento_meses)
            
            diff_months = (start_date_range.year - plan_start_date.year) * 12 + (start_date_range.month - plan_start_date.month)
            num_intervals = 0
            if freq > 0:
                num_intervals = max(0, (diff_months + freq - 1) // freq)

            current_plan_date = plan_start_date + relativedelta(months=num_intervals * freq)

            for _ in range(12 + freq):
                if start_date_range <= current_plan_date < start_date_range + relativedelta(months=12):
                    month_index = ((current_plan_date.year - start_date_range.year) * 12 + current_plan_date.month - start_date_range.month)
                    if 0 <= month_index < 12:
                        programmed_mantenimientos_line_data[month_index] += 1
                
                if current_plan_date >= start_date_range + relativedelta(months=12 + freq):
                    break
                
                try:
                    current_plan_date += relativedelta(months=freq)
                except OverflowError:
                    break

        # Comprobaciones Programadas (misma lógica optimizada)
        if equipo.frecuencia_comprobacion_meses is not None and equipo.frecuencia_comprobacion_meses > 0:
            freq = int(equipo.frecuencia_comprobacion_meses)
            
            diff_months = (start_date_range.year - plan_start_date.year) * 12 + (start_date_range.month - plan_start_date.month)
            num_intervals = 0
            if freq > 0:
                num_intervals = max(0, (diff_months + freq - 1) // freq)

            current_plan_date = plan_start_date + relativedelta(months=num_intervals * freq)

            for _ in range(12 + freq):
                if start_date_range <= current_plan_date < start_date_range + relativedelta(months=12):
                    month_index = ((current_plan_date.year - start_date_range.year) * 12 + current_plan_date.month - start_date_range.month)
                    if 0 <= month_index < 12:
                        programmed_comprobaciones_line_data[month_index] += 1
                
                if current_plan_date >= start_date_range + relativedelta(months=12 + freq):
                    break
                
                try:
                    current_plan_date += relativedelta(months=freq)
                except OverflowError:
                    break

    # --- Datos para Gráficas de Torta (Cumplimiento Anual) ---
    # Colores para las gráficas de torta
    pie_chart_colors_cal = ['#28a745', '#dc3545', '#007bff'] # Verde (Realizado), Rojo (No Cumplido), Azul (Pendiente/Programado)
    pie_chart_colors_comp = ['#28a745', '#dc3545', '#007bff'] # Mismos colores para comprobaciones
    pie_chart_colors_equipos = ['#28a745', '#ffc107', '#dc3545', '#17a2b8', '#6c757d'] # Activo, En Mantenimiento, De Baja, En Calibración, En Comprobación

    # Estado de Equipos (Torta)
    estado_equipos_counts = defaultdict(int)
    for equipo in equipos_queryset.all(): # Incluir todos los estados, no solo activos
        estado_equipos_counts[equipo.estado] += 1
    
    estado_equipos_labels = list(estado_equipos_counts.keys())
    estado_equipos_data = list(estado_equipos_counts.values())

    # Calibraciones
    projected_calibraciones = get_projected_activities_for_year(equipos_queryset, 'calibracion', current_year, today)
    
    cal_total_programmed_anual_display = len(projected_calibraciones)
    cal_realized_anual_display = sum(1 for act in projected_calibraciones if act['status'] == 'Realizado')
    cal_no_cumplido_anual_display = sum(1 for act in projected_calibraciones if act['status'] == 'No Cumplido')
    cal_pendiente_anual_display = sum(1 for act in projected_calibraciones if act['status'] == 'Pendiente/Programado')

    # Handle case where no activities are programmed for the year
    if cal_total_programmed_anual_display == 0:
        calibraciones_torta_labels = ['Sin Actividades']
        calibraciones_torta_data = [1] # A small value to render the chart
        pie_chart_colors_cal = ['#cccccc']
        cal_realized_anual_percent = 0
        cal_no_cumplido_anual_percent = 0
        cal_pendiente_anual_percent = 0
    else:
        calibraciones_torta_labels = ['Realizado', 'No Cumplido', 'Pendiente/Programado']
        calibraciones_torta_data = [
            cal_realized_anual_display,
            cal_no_cumplido_anual_display,
            cal_pendiente_anual_display
        ]
        
        cal_realized_anual_percent = (cal_realized_anual_display / cal_total_programmed_anual_display * 100)
        cal_no_cumplido_anual_percent = (cal_no_cumplido_anual_display / cal_total_programmed_anual_display * 100)
        cal_pendiente_anual_percent = (cal_pendiente_anual_display / cal_total_programmed_anual_display * 100)


    # Comprobaciones (similar logic)
    projected_comprobaciones = get_projected_activities_for_year(equipos_queryset, 'comprobacion', current_year, today)

    comp_total_programmed_anual_display = len(projected_comprobaciones)
    comp_realized_anual_display = sum(1 for act in projected_comprobaciones if act['status'] == 'Realizado')
    comp_no_cumplido_anual_display = sum(1 for act in projected_comprobaciones if act['status'] == 'No Cumplido')
    comp_pendiente_anual_display = sum(1 for act in projected_comprobaciones if act['status'] == 'Pendiente/Programado')

    if comp_total_programmed_anual_display == 0:
        comprobaciones_torta_labels = ['Sin Actividades']
        comprobaciones_torta_data = [1]
        pie_chart_colors_comp = ['#cccccc']
        comp_realized_anual_percent = 0
        comp_no_cumplido_anual_percent = 0
        comp_pendiente_anual_percent = 0
    else:
        comprobaciones_torta_labels = ['Realizado', 'No Cumplido', 'Pendiente/Programado']
        comprobaciones_torta_data = [
            comp_realized_anual_display,
            comp_no_cumplido_anual_display,
            comp_pendiente_anual_display
        ]
        
        comp_realized_anual_percent = (comp_realized_anual_display / comp_total_programmed_anual_display * 100)
        comp_no_cumplido_anual_percent = (comp_no_cumplido_anual_display / comp_total_programmed_anual_display * 100)
        comp_pendiente_anual_percent = (comp_pendiente_anual_display / comp_total_programmed_anual_display * 100)

    # Mantenimientos por Tipo (Torta)
    mantenimientos_tipo_counts = defaultdict(int)
    for mant in Mantenimiento.objects.filter(equipo__in=equipos_queryset).exclude(equipo__estado='De Baja'):
        mantenimientos_tipo_counts[mant.tipo_mantenimiento] += 1
    
    mantenimientos_torta_labels = list(mantenimientos_tipo_counts.keys())
    mantenimientos_torta_data = list(mantenimientos_tipo_counts.values())
    pie_chart_colors_mant = ['#ffc107', '#dc3545', '#17a2b8', '#6c757d'] # Preventivo, Correctivo, Predictivo, Inspección


    # Obtener los códigos de equipos vencidos para mostrar en el dashboard
    # Excluir equipos "De Baja"
    vencidos_calibracion_codigos = [e.codigo_interno for e in equipos_queryset.filter(proxima_calibracion__lt=today).exclude(estado='De Baja')]
    vencidos_mantenimiento_codigos = [e.codigo_interno for e in equipos_queryset.filter(proximo_mantenimiento__lt=today).exclude(estado='De Baja')]
    vencidos_comprobacion_codigos = [e.codigo_interno for e in equipos_queryset.filter(proxima_comprobacion__lt=today).exclude(estado='De Baja')]

    # --- NUEVA LÓGICA PARA MANTENIMIENTOS CORRECTIVOS ---
    # Obtener los 5 mantenimientos correctivos más recientes para la empresa del usuario
    # o para todas las empresas si es superusuario y no hay filtro de empresa.
    latest_corrective_maintenances_query = Mantenimiento.objects.filter(tipo_mantenimiento='Correctivo').order_by('-fecha_mantenimiento')
    
    if not user.is_superuser:
        if user.empresa:
            latest_corrective_maintenances_query = latest_corrective_maintenances_query.filter(equipo__empresa=user.empresa)
        else:
            latest_corrective_maintenances_query = Mantenimiento.objects.none()
    elif selected_company_id:
        latest_corrective_maintenances_query = latest_corrective_maintenances_query.filter(equipo__empresa_id=selected_company_id)

    latest_corrective_maintenances = latest_corrective_maintenances_query[:5] # Limitar a los 5 más recientes

    # Convertir datos a JSON para pasarlos a JavaScript
    context = {
        'titulo_pagina': 'Panel de Control de Metrología',
        'today': today,
        'is_superuser': user.is_superuser,
        'empresas_disponibles': empresas_disponibles,
        'selected_company_id': selected_company_id,

        'total_equipos': total_equipos,
        'equipos_activos': equipos_activos,
        'equipos_de_baja': equipos_de_baja, # Añadido al contexto

        'calibraciones_vencidas': calibraciones_vencidas,
        'calibraciones_proximas': calibraciones_proximas,
        'mantenimientos_vencidos': mantenimientos_vencidos,
        'mantenimientos_proximas': mantenimientos_proximas,
        'comprobaciones_vencidas': comprobaciones_vencidas,
        'comprobaciones_proximas': comprobaciones_proximas,

        'vencidos_calibracion_codigos': vencidos_calibracion_codigos,
        'vencidos_mantenimiento_codigos': vencidos_mantenimiento_codigos,
        'vencidos_comprobacion_codigos': vencidos_comprobacion_codigos,

        # Datos para tablas de resumen de tortas (ya calculados)
        'cal_total_programmed_anual': cal_total_programmed_anual_display,
        'cal_realized_anual': cal_realized_anual_display,
        'cal_no_cumplido_anual': cal_no_cumplido_anual_display,
        'cal_pendiente_anual': cal_pendiente_anual_display,
        'cal_realized_anual_percent': round(cal_realized_anual_percent),
        'cal_no_cumplido_anual_percent': round(cal_no_cumplido_anual_percent),
        'cal_pendiente_anual_percent': round(cal_pendiente_anual_percent),

        'comp_total_programmed_anual': comp_total_programmed_anual_display,
        'comp_realized_anual': comp_realized_anual_display,
        'comp_no_cumplido_anual': comp_no_cumplido_anual_display,
        'comp_pendiente_anual': comp_pendiente_anual_display,
        'comp_realized_anual_percent': round(comp_realized_anual_percent),
        'comp_no_cumplido_anual_percent': round(comp_no_cumplido_anual_percent),
        'comp_pendiente_anual_percent': round(comp_pendiente_anual_percent),

        # Datos para gráficas de línea
        'line_chart_labels_json': mark_safe(json.dumps(line_chart_labels)),
        'programmed_calibrations_line_data_json': mark_safe(json.dumps(programmed_calibrations_line_data)),
        'realized_calibrations_line_data_json': mark_safe(json.dumps(realized_calibrations_line_data)),
        'programmed_mantenimientos_line_data_json': mark_safe(json.dumps(programmed_mantenimientos_line_data)),
        'realized_preventive_mantenimientos_line_data_json': mark_safe(json.dumps(realized_preventive_mantenimientos_line_data)),
        'realized_corrective_mantenimientos_line_data_json': mark_safe(json.dumps(realized_corrective_mantenimientos_line_data)),
        'realized_other_mantenimientos_line_data_json': mark_safe(json.dumps(realized_other_mantenimientos_line_data)),
        'realized_predictive_mantenimientos_line_data_json': mark_safe(json.dumps(realized_predictive_mantenimientos_line_data)), # Nuevo
        'realized_inspection_mantenimientos_line_data_json': mark_safe(json.dumps(realized_inspection_mantenimientos_line_data)), # Nuevo
        'programmed_comprobaciones_line_data_json': mark_safe(json.dumps(programmed_comprobaciones_line_data)),
        'realized_comprobaciones_line_data_json': mark_safe(json.dumps(realized_comprobaciones_line_data)),
        
        # Datos para gráficas de torta
        'estado_equipos_labels_json': mark_safe(json.dumps(estado_equipos_labels)),
        'estado_equipos_data_json': mark_safe(json.dumps(estado_equipos_data)),
        'pie_chart_colors_equipos_json': mark_safe(json.dumps(pie_chart_colors_equipos)),
        'calibraciones_torta_labels_json': mark_safe(json.dumps(calibraciones_torta_labels)),
        'calibraciones_torta_data_json': mark_safe(json.dumps(calibraciones_torta_data)),
        'pie_chart_colors_cal_json': mark_safe(json.dumps(pie_chart_colors_cal)),
        'comprobaciones_torta_labels_json': mark_safe(json.dumps(comprobaciones_torta_labels)),
        'comprobaciones_torta_data_json': mark_safe(json.dumps(comprobaciones_torta_data)),
        'pie_chart_colors_comp_json': mark_safe(json.dumps(pie_chart_colors_comp)),
        'mantenimientos_torta_labels_json': mark_safe(json.dumps(mantenimientos_torta_labels)), # Nuevo
        'mantenimientos_torta_data_json': mark_safe(json.dumps(mantenimientos_torta_data)), # Nuevo
        'pie_chart_colors_mant_json': mark_safe(json.dumps(pie_chart_colors_mant)), # Nuevo

        # Datos para el cuadro de mantenimientos correctivos
        'latest_corrective_maintenances': latest_corrective_maintenances,
    }
    return render(request, 'core/dashboard.html', context)

@login_required
def contact_us(request):
    """
    Renders the contact us page.
    """
    return render(request, 'core/contact_us.html')

@login_required
def perfil_usuario(request):
    """
    Handles user profile viewing and editing.
    """
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tu perfil ha sido actualizado exitosamente.')
            return redirect('core:perfil_usuario')
        else:
            messages.error(request, 'Error al actualizar tu perfil. Por favor, revisa los campos.')
    else:
        form = UserProfileForm(instance=request.user)
    return render(request, 'core/my_profile.html', {'form': form, 'usuario': request.user, 'titulo_pagina': 'Mi Perfil'})

@login_required
def cambiar_password(request):
    """
    Handles changing the current user's password.
    """
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Tu contraseña ha sido actualizada exitosamente.')
            return redirect('core:password_change_done')
        else:
            messages.error(request, 'Por favor corrige los errores a continuación.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'registration/password_change_form.html', {'form': form, 'titulo_pagina': 'Cambiar Contraseña'})

@login_required
def password_change_done(request):
    """
    Renders the password change done page.
    """
    return render(request, 'core/password_change_done.html', {'titulo_pagina': 'Contraseña Cambiada'})


# --- Vistas de Equipos ---

@login_required
@permission_required('core.view_equipo', raise_exception=True)
def home(request):
    """
    Lists all equipment, with filtering and pagination.
    """
    query = request.GET.get('q')
    tipo_equipo_filter = request.GET.get('tipo_equipo')
    estado_filter = request.GET.get('estado')
    
    # --- INICIO: Lógica para el filtro de empresa para superusuarios y obtener info de formato ---
    user = request.user
    selected_company_id = request.GET.get('empresa_id')
    empresas_disponibles = Empresa.objects.all().order_by('nombre')

    equipos_list = Equipo.objects.all().order_by('codigo_interno')

    current_company_format_info = None # Initialize to None

    if not user.is_superuser:
        # Los usuarios normales solo ven datos de su propia empresa
        if user.empresa:
            equipos_list = equipos_list.filter(empresa=user.empresa)
            selected_company_id = str(user.empresa.id) # Asegurar que el filtro se aplique y muestre la empresa del usuario
            current_company_format_info = user.empresa # Set company info for regular user
        else:
            # Si un usuario normal no tiene empresa asignada, no ve equipos
            equipos_list = Equipo.objects.none()
            empresas_disponibles = Empresa.objects.none() # No hay empresas para filtrar

    else: # If user is superuser
        if selected_company_id:
            try:
                # Get the selected company object for format info
                current_company_format_info = Empresa.objects.get(pk=selected_company_id)
                equipos_list = equipos_list.filter(empresa_id=selected_company_id)
            except Empresa.DoesNotExist:
                # Handle case where selected_company_id is invalid
                messages.error(request, 'La empresa seleccionada no existe.')
                equipos_list = Equipo.objects.none()
        # If superuser and no company selected, current_company_format_info remains None,
        # meaning no specific company format info will be displayed at the top.
    # --- FIN: Lógica para el filtro de empresa para superusuarios y obtener info de formato ---


    today = timezone.localdate() # Obtener la fecha actual con la zona horaria configurada

    # Filtrar por query de búsqueda
    if query:
        equipos_list = equipos_list.filter(
            Q(codigo_interno__icontains=query) |
            Q(nombre__icontains=query) |
            Q(marca__icontains=query) |
            Q(modelo__icontains=query) |
            Q(numero_serie__icontains=query) |
            Q(responsable__icontains=query) |
            Q(ubicacion__icontains=query) # Filtrar por el campo de texto libre de ubicación
        )

    # Filtrar por tipo de equipo
    if tipo_equipo_filter:
        equipos_list = equipos_list.filter(tipo_equipo=tipo_equipo_filter)

    # Filtrar por estado
    if estado_filter:
        equipos_list = equipos_list.filter(estado=estado_filter)

    # Añadir lógica para el estado de las fechas de próxima actividad
    for equipo in equipos_list:
        # Calibración
        if equipo.proxima_calibracion and equipo.estado != 'De Baja': # No proyectar si está de baja
            days_remaining = (equipo.proxima_calibracion - today).days
            if days_remaining < 0:
                equipo.proxima_calibracion_status = 'text-red-600 font-bold' # Vencido
            elif days_remaining <= 15:
                equipo.proxima_calibracion_status = 'text-yellow-600 font-bold' # Próximos 15 días
            elif days_remaining <= 30:
                equipo.proxima_calibracion_status = 'text-green-600' # Próximos 30 días
            else:
                equipo.proxima_calibracion_status = 'text-gray-900' # Más de 30 días o futuro lejano (negro)
        else:
            equipo.proxima_calibracion_status = 'text-gray-500' # N/A o sin fecha o de baja

        # Comprobación
        if equipo.proxima_comprobacion and equipo.estado != 'De Baja': # No proyectar si está de baja
            days_remaining = (equipo.proxima_comprobacion - today).days
            if days_remaining < 0:
                equipo.proxima_comprobacion_status = 'text-red-600 font-bold' # Vencido
            elif days_remaining <= 15:
                equipo.proxima_comprobacion_status = 'text-yellow-600 font-bold' # Próximos 15 días
            elif days_remaining <= 30:
                equipo.proxima_comprobacion_status = 'text-green-600' # Próximos 30 días
            else:
                equipo.proxima_comprobacion_status = 'text-gray-900' # Más de 30 días o futuro lejano (negro)
        else:
            equipo.proxima_comprobacion_status = 'text-gray-500' # N/A o sin fecha o de baja

        # Mantenimiento
        if equipo.proximo_mantenimiento and equipo.estado != 'De Baja': # No proyectar si está de baja
            days_remaining = (equipo.proximo_mantenimiento - today).days
            if days_remaining < 0:
                equipo.proximo_mantenimiento_status = 'text-red-600 font-bold' # Vencido
            elif days_remaining <= 15:
                equipo.proximo_mantenimiento_status = 'text-yellow-600 font-bold' # Próximos 15 días
            elif days_remaining <= 30:
                equipo.proximo_mantenimiento_status = 'text-green-600' # Próximos 30 días
            else:
                equipo.proximo_mantenimiento_status = 'text-gray-900' # Más de 30 días o futuro lejano (negro)
        else:
            equipo.proximo_mantenimiento_status = 'text-gray-500' # N/A o sin fecha o de baja


    paginator = Paginator(equipos_list, 10)
    page_number = request.GET.get('page')
    try:
        equipos = paginator.page(page_number)
    except PageNotAnInteger:
        equipos = paginator.page(1)
    except EmptyPage:
        equipos = paginator.page(paginator.num_pages)

    tipo_equipo_choices = Equipo.TIPO_EQUIPO_CHOICES
    estado_choices = Equipo.ESTADO_CHOICES

    context = {
        'equipos': equipos,
        'query': query, # Pasar el query de búsqueda al contexto
        'tipo_equipo_choices': tipo_equipo_choices,
        'estado_choices': estado_choices,
        'titulo_pagina': 'Listado de Equipos',
        'is_superuser': user.is_superuser, # Pasar is_superuser al contexto
        'empresas_disponibles': empresas_disponibles, # Pasar empresas_disponibles al contexto
        'selected_company_id': selected_company_id, # Pasar selected_company_id al contexto
        'current_company_format_info': current_company_format_info, # NUEVO: Información de formato de la empresa actual
    }
    return render(request, 'core/home.html', context)

@login_required
def update_empresa_formato(request):
    """
    Updates the format information for a company via AJAX.
    """
    if request.method == 'POST':
        # Determine which company to update
        company_to_update = None
        if request.user.is_superuser:
            # Superuser can update any company if 'empresa_id' is provided
            empresa_id = request.POST.get('empresa_id')
            if empresa_id:
                try:
                    company_to_update = Empresa.objects.get(pk=empresa_id)
                except Empresa.DoesNotExist:
                    return JsonResponse({'status': 'error', 'message': 'Empresa no encontrada.'}, status=404)
            else:
                return JsonResponse({'status': 'error', 'message': 'ID de empresa requerido para superusuario.'}, status=400)
        elif request.user.empresa:
            # Regular user can only update their own company
            company_to_update = request.user.empresa
        else:
            return JsonResponse({'status': 'error', 'message': 'Usuario no asociado a ninguna empresa.'}, status=403)

        form = EmpresaFormatoForm(request.POST, instance=company_to_update)
        if form.is_valid():
            form.save()
            return JsonResponse({
                'status': 'success',
                'message': 'Información de formato actualizada.',
                'version': company_to_update.formato_version_empresa,
                'fecha_version': company_to_update.formato_fecha_version_empresa.strftime('%d/%m/%Y') if company_to_update.formato_fecha_version_empresa else 'N/A',
                'codificacion': company_to_update.formato_codificacion_empresa,
            })
        else:
            # Return form errors as JSON
            errors = form.errors.as_json()
            return JsonResponse({'status': 'error', 'message': 'Errores de validación.', 'errors': errors}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Método no permitido.'}, status=405)

@login_required
@permission_required('core.add_equipo', raise_exception=True)
def añadir_equipo(request):
    """
    Handles adding a new equipment.
    """
    if request.method == 'POST':
        form = EquipoForm(request.POST, request.FILES, request=request)
        if form.is_valid():
            equipo = form.save(commit=False)
            equipo.save()
            messages.success(request, 'Equipo añadido exitosamente.')
            return redirect('core:detalle_equipo', pk=equipo.pk)
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = EquipoForm(request=request)
    
    return render(request, 'core/añadir_equipo.html', {'form': form, 'titulo_pagina': 'Añadir Nuevo Equipo'})


@login_required
@permission_required('core.add_equipo', raise_exception=True)
def importar_equipos_excel(request):
    """
    Handles importing equipment from an Excel file.
    """
    titulo_pagina = "Importar Equipos desde Excel"
    if request.method == 'POST':
        form = ExcelUploadForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES['excel_file']

            if not excel_file.name.endswith('.xlsx'):
                messages.error(request, 'El archivo debe ser un archivo Excel (.xlsx).')
                return render(request, 'core/importar_equipos.html', {'form': form, 'titulo_pagina': titulo_pagina})

            try:
                workbook = openpyxl.load_workbook(excel_file)
                sheet = workbook.active
                
                headers = [cell.value for cell in sheet[1]]
                
                column_mapping = {
                    'codigo_interno': 'codigo_interno',
                    'nombre': 'nombre',
                    'empresa_nombre': 'empresa',
                    'tipo_equipo': 'tipo_equipo',
                    'marca': 'marca',
                    'modelo': 'modelo',
                    'numero_serie': 'numero_serie',
                    'ubicacion_nombre': 'ubicacion',
                    'responsable': 'responsable',
                    'estado': 'estado',
                    'fecha_adquisicion': 'fecha_adquisicion',
                    'rango_medida': 'rango_medida',
                    'resolucion': 'resolucion',
                    'error_maximo_permisible': 'error_maximo_permisible',
                    'observaciones': 'observaciones',
                    'version_formato': 'version_formato',
                    'fecha_version_formato': 'fecha_version_formato',
                    'codificacion_formato': 'codificacion_formato',
                    'frecuencia_calibracion_meses': 'frecuencia_calibracion_meses',
                    'frecuencia_mantenimiento_meses': 'frecuencia_mantenimiento_meses',
                    'frecuencia_comprobacion_meses': 'frecuencia_comprobacion_meses',
                }

                required_headers = ['codigo_interno', 'nombre', 'empresa_nombre', 'tipo_equipo', 'marca', 'modelo', 'numero_serie', 'ubicacion_nombre', 'responsable', 'estado', 'fecha_adquisicion']
                if not all(h in headers for h in required_headers):
                    missing_headers = [h for h in required_headers if h not in headers]
                    messages.error(request, f'Faltan encabezados obligatorios en el archivo Excel: {", ".join(missing_headers)}. Por favor, usa la plantilla recomendada.')
                    return render(request, 'core/importar_equipos.html', {'form': form, 'titulo_pagina': titulo_pagina})

                created_count = 0
                errors = []
                
                with transaction.atomic():
                    for row_index, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
                        row_data = dict(zip(headers, row))
                        
                        equipo_data = {}
                        row_errors = []

                        for excel_col, model_field in column_mapping.items():
                            value = row_data.get(excel_col)
                            
                            if excel_col in required_headers and (value is None or (isinstance(value, str) and value.strip() == '')):
                                row_errors.append(f"'{excel_col}' es un campo obligatorio y está vacío.")
                                continue

                            if value is None or (isinstance(value, str) and value.strip() == ''):
                                equipo_data[model_field] = None
                                continue

                            if excel_col == 'empresa_nombre':
                                try:
                                    empresa = Empresa.objects.get(nombre=value)
                                    if not request.user.is_superuser and request.user.empresa != empresa:
                                        row_errors.append(f"No tienes permiso para añadir equipos a la empresa '{value}'.")
                                    equipo_data['empresa'] = empresa
                                except Empresa.DoesNotExist:
                                    row_errors.append(f"Empresa '{value}' no encontrada.")
                            elif excel_col == 'ubicacion_nombre':
                                equipo_data['ubicacion'] = str(value).strip() if value is not None else ''
                            elif excel_col == 'tipo_equipo':
                                valid_choices = [choice[0] for choice in Equipo.TIPO_EQUIPO_CHOICES]
                                if value not in valid_choices:
                                    row_errors.append(f"Tipo de equipo '{value}' no es válido. Opciones: {', '.join(valid_choices)}.")
                                equipo_data[model_field] = value
                            elif excel_col == 'estado':
                                valid_choices = [choice[0] for choice in Equipo.ESTADO_CHOICES]
                                if value not in valid_choices:
                                    row_errors.append(f"Estado '{value}' no es válido. Opciones: {', '.join(valid_choices)}.")
                                equipo_data[model_field] = value
                            elif excel_col in ['fecha_adquisicion', 'fecha_version_formato']:
                                parsed_date = None
                                if isinstance(value, datetime):
                                    parsed_date = value.date()
                                else:
                                    try:
                                        parsed_date = datetime.strptime(str(value), '%Y/%m/%d').date()
                                    except ValueError:
                                        try:
                                            parsed_date = datetime.strptime(str(value), '%d/%m/%Y').date()
                                        except ValueError:
                                            try:
                                                parsed_date = datetime.strptime(str(value), '%Y-%m-%d').date()
                                            except ValueError:
                                                row_errors.append(f"Formato de fecha inválido para '{excel_col}': '{value}'. Use YYYY/MM/DD, DD/MM/YYYY o YYYY-MM-DD.")
                                
                                equipo_data[model_field] = parsed_date
                            elif excel_col in ['frecuencia_calibracion_meses', 'frecuencia_mantenimiento_meses', 'frecuencia_comprobacion_meses']:
                                try:
                                    if value is not None and str(value).strip() != '':
                                        equipo_data[model_field] = decimal.Decimal(str(value)) # Guardar como Decimal
                                    else:
                                        equipo_data[model_field] = None
                                except (ValueError, TypeError, decimal.InvalidOperation):
                                    row_errors.append(f"Valor numérico inválido para '{excel_col}': '{value}'.")
                            elif excel_col == 'error_maximo_permisible':
                                equipo_data[model_field] = str(value).strip() if value is not None else ''
                            else:
                                equipo_data[model_field] = value

                        if 'empresa' in equipo_data and 'codigo_interno' in equipo_data and not row_errors:
                            if Equipo.objects.filter(empresa=equipo_data['empresa'], codigo_interno=equipo_data['codigo_interno']).exists():
                                row_errors.append(f"Ya existe un equipo con el código interno '{equipo_data['codigo_interno']}' para la empresa '{equipo_data['empresa'].nombre}'.")

                        if row_errors:
                            errors.append(f"Fila {row_index}: {'; '.join(row_errors)}")
                        else:
                            try:
                                Equipo.objects.create(**equipo_data)
                                created_count += 1
                            except Exception as e:
                                errors.append(f"Fila {row_index}: Error al crear el equipo - {e}")
                                raise

                if errors:
                    messages.warning(request, f'Importación completada con {created_count} equipos creados y {len(errors)} errores.')
                    for err in errors:
                        messages.error(request, err)
                    return render(request, 'core/importar_equipos.html', {'form': form, 'titulo_pagina': titulo_pagina})
                else:
                    messages.success(request, f'¡Importación exitosa! Se crearon {created_count} equipos.')
                    return redirect('core:home')
            
            except Exception as e:
                messages.error(request, f'Ocurrió un error inesperado al procesar el archivo: {e}')
                return render(request, 'core/importar_equipos.html', {'form': form, 'titulo_pagina': titulo_pagina})
        else:
            messages.error(request, 'Por favor, corrige los errores del formulario de subida.')
    else:
        form = ExcelUploadForm()
    
    return render(request, 'core/importar_equipos.html', {'form': form, 'titulo_pagina': titulo_pagina})


@login_required
@permission_required('core.view_equipo', raise_exception=True)
def detalle_equipo(request, pk):
    """
    Displays the details of a specific equipment.
    """
    equipo = get_object_or_404(Equipo, pk=pk)

    if not request.user.is_superuser and request.user.empresa != equipo.empresa:
        messages.error(request, 'No tienes permiso para ver este equipo.')
        return redirect('core:home')

    calibraciones = equipo.calibraciones.all().order_by('-fecha_calibracion')
    for cal in calibraciones:
        if equipo.frecuencia_calibracion_meses and cal.fecha_calibracion:
            cal.proxima_actividad_para_este_registro = cal.fecha_calibracion + relativedelta(months=int(equipo.frecuencia_calibracion_meses))
        else:
            cal.proxima_actividad_para_este_registro = None

    mantenimientos = equipo.mantenimientos.all().order_by('-fecha_mantenimiento')
    for mant in mantenimientos:
        if equipo.frecuencia_mantenimiento_meses and mant.fecha_mantenimiento:
            mant.proxima_actividad_para_este_registro = mant.fecha_mantenimiento + relativedelta(months=int(equipo.frecuencia_mantenimiento_meses))
        else:
            mant.proxima_actividad_para_este_registro = None

    comprobaciones = equipo.comprobaciones.all().order_by('-fecha_comprobacion')
    for comp in comprobaciones:
        if equipo.frecuencia_comprobacion_meses and comp.fecha_comprobacion:
            comp.proxima_actividad_para_este_registro = comp.fecha_comprobacion + relativedelta(months=int(equipo.frecuencia_comprobacion_meses))
        else:
            comp.proxima_actividad_para_este_registro = None

    baja_registro = None
    if equipo.estado == 'De Baja':
        try:
            baja_registro = BajaEquipo.objects.get(equipo=equipo)
        except BajaEquipo.DoesNotExist:
            pass

    logo_empresa_url = request.build_absolute_uri(equipo.empresa.logo_empresa.url) if equipo.empresa and equipo.empresa.logo_empresa else None
    imagen_equipo_url = request.build_absolute_uri(equipo.imagen_equipo.url) if equipo.imagen_equipo else None
    documento_baja_url = request.build_absolute_uri(baja_registro.documento_baja.url) if baja_registro and baja_registro.documento_baja else None

    for cal in calibraciones:
        cal.documento_calibracion_url = request.build_absolute_uri(cal.documento_calibracion.url) if cal.documento_calibracion else None
        cal.confirmacion_metrologica_pdf_url = request.build_absolute_uri(cal.confirmacion_metrologica_pdf.url) if cal.confirmacion_metrologica_pdf else None
        cal.intervalos_calibracion_pdf_url = request.build_absolute_uri(cal.intervalos_calibracion_pdf.url) if cal.intervalos_calibracion_pdf else None # NUEVO URL
    for mant in mantenimientos:
        mant.documento_mantenimiento_url = request.build_absolute_uri(mant.documento_mantenimiento.url) if mant.documento_mantenimiento else None
    for comp in comprobaciones:
        comp.documento_comprobacion_url = request.build_absolute_uri(comp.documento_comprobacion.url) if comp.documento_comprobacion else None

    archivo_compra_pdf_url = request.build_absolute_uri(equipo.archivo_compra_pdf.url) if equipo.archivo_compra_pdf else None
    ficha_tecnica_pdf_url = request.build_absolute_uri(equipo.ficha_tecnica_pdf.url) if equipo.ficha_tecnica_pdf else None
    manual_pdf_url = request.build_absolute_uri(equipo.manual_pdf.url) if equipo.manual_pdf else None
    otros_documentos_pdf_url = request.build_absolute_uri(equipo.otros_documentos_pdf.url) if equipo.otros_documentos_pdf else None


    return render(request, 'core/detalle_equipo.html', {
        'equipo': equipo,
        'calibraciones': calibraciones,
        'mantenimientos': mantenimientos,
        'comprobaciones': comprobaciones,
        'baja_registro': baja_registro,
        'logo_empresa_url': logo_empresa_url,
        'imagen_equipo_url': imagen_equipo_url,
        'documento_baja_url': documento_baja_url,
        'archivo_compra_pdf_url': archivo_compra_pdf_url,
        'ficha_tecnica_pdf_url': ficha_tecnica_pdf_url,
        'manual_pdf_url': manual_pdf_url,
        'otros_documentos_pdf_url': otros_documentos_pdf_url,
        'titulo_pagina': f'Detalle de {equipo.nombre}',
    })

@login_required
@permission_required('core.change_equipo', raise_exception=True)
def editar_equipo(request, pk):
    """
    Handles editing an existing equipment.
    """
    equipo = get_object_or_404(Equipo, pk=pk)

    if not request.user.is_superuser and request.user.empresa != equipo.empresa:
        messages.error(request, 'No tienes permiso para editar este equipo.')
        return redirect('core:home')

    if request.method == 'POST':
        form = EquipoForm(request.POST, request.FILES, instance=equipo, request=request)
        if form.is_valid():
            equipo = form.save(commit=False)
            equipo.save()
            messages.success(request, 'Equipo actualizado exitosamente.')
            return redirect('core:detalle_equipo', pk=equipo.pk)
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = EquipoForm(instance=equipo, request=request)

    return render(request, 'core/editar_equipo.html', {'form': form, 'equipo': equipo, 'titulo_pagina': f'Editar Equipo: {equipo.nombre}'})


@login_required
@permission_required('core.delete_equipo', raise_exception=True)
def eliminar_equipo(request, pk):
    """
    Handles deleting an equipment.
    """
    equipo = get_object_or_404(Equipo, pk=pk)

    if not request.user.is_superuser and request.user.empresa != equipo.empresa:
        messages.error(request, 'No tienes permiso para eliminar este equipo.')
        return redirect('core:home')

    if request.method == 'POST':
        try:
            equipo_nombre = equipo.nombre
            equipo.delete()
            messages.success(request, 'Equipo eliminado exitosamente.')
            return redirect('core:home')
        except Exception as e:
            messages.error(request, f'Error al eliminar el equipo: {e}')
            return redirect('core:home')
    return render(request, 'core/confirmar_eliminacion.html', {'objeto': equipo, 'tipo': 'equipo', 'titulo_pagina': f'Eliminar Equipo: {equipo.nombre}'})

# --- Vistas de Calibraciones ---

@login_required
@permission_required('core.add_calibracion', raise_exception=True)
def añadir_calibracion(request, equipo_pk):
    """
    Handles adding a new calibration for an equipment.
    """
    equipo = get_object_or_404(Equipo, pk=equipo_pk)
    if not request.user.is_superuser and request.user.empresa != equipo.empresa:
        messages.error(request, 'No tienes permiso para añadir calibraciones a este equipo.')
        return redirect('core:detalle_equipo', pk=equipo.pk)

    if request.method == 'POST':
        form = CalibracionForm(request.POST, request.FILES)
        if form.is_valid():
            calibracion = form.save(commit=False)
            calibracion.equipo = equipo
            calibracion.save()
            messages.success(request, 'Calibración añadida exitosamente.')
            return redirect('core:detalle_equipo', pk=equipo.pk)
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = CalibracionForm()
    return render(request, 'core/añadir_calibracion.html', {'form': form, 'equipo': equipo, 'titulo_pagina': f'Añadir Calibración para {equipo.nombre}'})

@login_required
@permission_required('core.change_calibracion', raise_exception=True)
def editar_calibracion(request, equipo_pk, pk):
    """
    Handles editing an existing calibration.
    """
    equipo = get_object_or_404(Equipo, pk=equipo_pk)
    calibracion = get_object_or_404(Calibracion, pk=pk, equipo=equipo)

    if not request.user.is_superuser and request.user.empresa != equipo.empresa:
        messages.error(request, 'No tienes permiso para editar esta calibración.')
        return redirect('core:detalle_equipo', pk=equipo.pk)

    if request.method == 'POST':
        form = CalibracionForm(request.POST, request.FILES, instance=calibracion)
        if form.is_valid():
            form.save()
            messages.success(request, 'Calibración actualizada exitosamente.')
            return redirect('core:detalle_equipo', pk=equipo.pk)
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = CalibracionForm(instance=calibracion)
    return render(request, 'core/editar_calibracion.html', {'form': form, 'equipo': equipo, 'calibracion': calibracion, 'titulo_pagina': f'Editar Calibración para {equipo.nombre}'})

@login_required
@permission_required('core.delete_calibracion', raise_exception=True)
def eliminar_calibracion(request, equipo_pk, pk):
    """
    Handles deleting a calibration.
    """
    equipo = get_object_or_404(Equipo, pk=equipo_pk)
    calibracion = get_object_or_404(Calibracion, pk=pk, equipo=equipo)

    if not request.user.is_superuser and request.user.empresa != equipo.empresa:
        messages.error(request, 'No tienes permiso para eliminar esta calibración.')
        return redirect('core:detalle_equipo', pk=equipo.pk)

    if request.method == 'POST':
        try:
            calibracion.delete()
            messages.success(request, 'Calibración eliminada exitosamente.')
            return redirect('core:detalle_equipo', pk=equipo.pk)
        except Exception as e:
            messages.error(request, f'Error al eliminar la calibración: {e}')
            return redirect('core:detalle_equipo', pk=equipo.pk)
    return render(request, 'core/confirmar_eliminacion.html', {'objeto': calibracion, 'tipo': 'calibración', 'titulo_pagina': f'Eliminar Calibración de {equipo.nombre}'})


# --- Vistas de Mantenimientos ---

@login_required
@permission_required('core.add_comprobacion', raise_exception=True)
def añadir_comprobacion(request, equipo_pk):
    """
    Handles adding a new verification record for an equipment.
    """
    equipo = get_object_or_404(Equipo, pk=equipo_pk)
    if not request.user.is_superuser and request.user.empresa != equipo.empresa:
        messages.error(request, 'No tienes permiso para añadir comprobaciones a este equipo.')
        return redirect('core:detalle_equipo', pk=equipo.pk)

    if request.method == 'POST':
        form = ComprobacionForm(request.POST, request.FILES)
        if form.is_valid():
            try: # Añade un bloque try-except aquí para capturar errores de S3
                comprobacion = form.save(commit=False)
                comprobacion.equipo = equipo
                comprobacion.save() # Aquí es donde se intenta guardar el archivo en S3
                
                # --- LÍNEA DE DEPURACIÓN CLAVE ---
                print(f"DEBUG: Archivo guardado para la comprobación ID: {comprobacion.id}, nombre de archivo: {comprobacion.documento_comprobacion.name if comprobacion.documento_comprobacion else 'N/A'}")
                # ---------------------------------

                messages.success(request, 'Comprobación añadida exitosamente.')
                return redirect('core:detalle_equipo', pk=equipo.pk)
            except Exception as e:
                # Si ocurre un error durante el guardado (incluyendo problemas de S3)
                print(f"ERROR al guardar comprobación o archivo en S3: {e}")
                messages.error(request, f'Hubo un error al guardar la comprobación: {e}')
                # Re-renderiza el formulario con los datos POST para que el usuario pueda ver los errores
                return render(request, 'core/añadir_comprobacion.html', {'form': form, 'equipo': equipo, 'titulo_pagina': f'Añadir Comprobación para {equipo.nombre}'})
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = ComprobacionForm()
    return render(request, 'core/añadir_comprobacion.html', {'form': form, 'equipo': equipo, 'titulo_pagina': f'Añadir Comprobación para {equipo.nombre}'})

@login_required
@permission_required('core.change_mantenimiento', raise_exception=True)
def editar_mantenimiento(request, equipo_pk, pk):
    """
    Handles editing an existing maintenance record.
    """
    equipo = get_object_or_404(Equipo, pk=equipo_pk)
    mantenimiento = get_object_or_404(Mantenimiento, pk=pk, equipo=equipo)

    if not request.user.is_superuser and request.user.empresa != equipo.empresa:
        messages.error(request, 'No tienes permiso para editar este mantenimiento.')
        return redirect('core:detalle_equipo', pk=equipo.pk)

    if request.method == 'POST':
        form = MantenimientoForm(request.POST, request.FILES, instance=mantenimiento)
        if form.is_valid():
            form.save()
            messages.success(request, 'Mantenimiento actualizado exitosamente.')
            return redirect('core:detalle_equipo', pk=equipo.pk)
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = MantenimientoForm(instance=mantenimiento)
    return render(request, 'core/editar_mantenimiento.html', {'form': form, 'equipo': equipo, 'mantenimiento': mantenimiento, 'titulo_pagina': f'Editar Mantenimiento para {equipo.nombre}'})

@login_required
@permission_required('core.delete_mantenimiento', raise_exception=True)
def eliminar_mantenimiento(request, equipo_pk, pk):
    """
    Handles deleting a maintenance record.
    """
    equipo = get_object_or_404(Equipo, pk=equipo_pk)
    mantenimiento = get_object_or_404(Mantenimiento, pk=pk, equipo=equipo)

    if not request.user.is_superuser and request.user.empresa != equipo.empresa:
        messages.error(request, 'No tienes permiso para eliminar este mantenimiento.')
        return redirect('core:detalle_equipo', pk=equipo.pk)

    if request.method == 'POST':
        try:
            mantenimiento.delete()
            messages.success(request, 'Mantenimiento eliminado exitosamente.')
            return redirect('core:detalle_equipo', pk=equipo.pk)
        except Exception as e:
            messages.error(request, f'Error al eliminar el mantenimiento: {e}')
            return redirect('core:detalle_equipo', pk=equipo.pk)
    return render(request, 'core/confirmar_eliminacion.html', {'objeto': mantenimiento, 'tipo': 'mantenimiento', 'titulo_pagina': f'Eliminar Mantenimiento de {equipo.nombre}'})

@login_required
@permission_required('core.view_mantenimiento', raise_exception=True)
def detalle_mantenimiento(request, equipo_pk, pk):
    """
    Displays the details of a specific maintenance record.
    """
    equipo = get_object_or_404(Equipo, pk=equipo_pk)
    mantenimiento = get_object_or_404(Mantenimiento, pk=pk, equipo=equipo)

    if not request.user.is_superuser and request.user.empresa != equipo.empresa:
        messages.error(request, 'No tienes permiso para ver este mantenimiento.')
        return redirect('core:detalle_equipo', pk=equipo.pk)

    context = {
        'equipo': equipo,
        'mantenimiento': mantenimiento,
        'titulo_pagina': f'Detalle de Mantenimiento: {equipo.nombre}',
    }
    return render(request, 'core/detalle_mantenimiento.html', context)


# --- Vistas de Comprobaciones ---

@login_required
@permission_required('core.add_comprobacion', raise_exception=True)
def añadir_comprobacion(request, equipo_pk):
    """
    Handles adding a new verification record for an equipment.
    """
    equipo = get_object_or_404(Equipo, pk=equipo_pk)
    if not request.user.is_superuser and request.user.empresa != equipo.empresa:
        messages.error(request, 'No tienes permiso para añadir comprobaciones a este equipo.')
        return redirect('core:detalle_equipo', pk=equipo.pk)

    if request.method == 'POST':
        form = ComprobacionForm(request.POST, request.FILES)
        if form.is_valid():
            try: # Añade un bloque try-except aquí para capturar errores de S3
                comprobacion = form.save(commit=False)
                comprobacion.equipo = equipo
                comprobacion.save() # Aquí es donde se intenta guardar el archivo en S3
                
                # --- LÍNEA DE DEPURACIÓN CLAVE ---
                print(f"DEBUG: Archivo guardado para la comprobación ID: {comprobacion.id}, nombre de archivo: {comprobacion.documento_comprobacion.name if comprobacion.documento_comprobacion else 'N/A'}")
                # ---------------------------------

                messages.success(request, 'Comprobación añadida exitosamente.')
                return redirect('core:detalle_equipo', pk=equipo.pk)
            except Exception as e:
                # Si ocurre un error durante el guardado (incluyendo problemas de S3)
                print(f"ERROR al guardar comprobación o archivo en S3: {e}")
                messages.error(request, f'Hubo un error al guardar la comprobación: {e}')
                # Re-renderiza el formulario con los datos POST para que el usuario pueda ver los errores
                return render(request, 'core/añadir_comprobacion.html', {'form': form, 'equipo': equipo, 'titulo_pagina': f'Añadir Comprobación para {equipo.nombre}'})
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = ComprobacionForm()
    return render(request, 'core/añadir_comprobacion.html', {'form': form, 'equipo': equipo, 'titulo_pagina': f'Añadir Comprobación para {equipo.nombre}'})

@login_required
@permission_required('core.change_comprobacion', raise_exception=True)
def editar_comprobacion(request, equipo_pk, pk):
    """
    Handles editing an existing verification record.
    """
    equipo = get_object_or_404(Equipo, pk=equipo_pk)
    comprobacion = get_object_or_404(Comprobacion, pk=pk, equipo=equipo)

    if not request.user.is_superuser and request.user.empresa != equipo.empresa:
        messages.error(request, 'No tienes permiso para editar esta comprobación.')
        return redirect('core:detalle_equipo', pk=equipo.pk)

    if request.method == 'POST':
        form = ComprobacionForm(request.POST, request.FILES, instance=comprobacion)
        if form.is_valid():
            form.save()
            messages.success(request, 'Comprobación actualizada exitosamente.')
            return redirect('core:detalle_equipo', pk=equipo.pk)
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = ComprobacionForm(instance=comprobacion)
    return render(request, 'core/editar_comprobacion.html', {'form': form, 'equipo': equipo, 'comprobacion': comprobacion, 'titulo_pagina': f'Editar Comprobación para {equipo.nombre}'})

@login_required
@permission_required('core.delete_comprobacion', raise_exception=True)
def eliminar_comprobacion(request, equipo_pk, pk):
    """
    Handles deleting a verification record.
    """
    equipo = get_object_or_404(Equipo, pk=equipo_pk)
    comprobacion = get_object_or_404(Comprobacion, pk=pk, equipo=equipo)

    if not request.user.is_superuser and request.user.empresa != equipo.empresa:
        messages.error(request, 'No tienes permiso para eliminar esta comprobación.')
        return redirect('core:detalle_equipo', pk=equipo.pk)

    if request.method == 'POST':
        try:
            comprobacion.delete()
            messages.success(request, 'Comprobación eliminada exitosamente.')
            return redirect('core:detalle_equipo', pk=equipo.pk)
        except Exception as e:
            messages.error(request, f'Error al eliminar la comprobación: {e}')
            return redirect('core:detalle_equipo', pk=equipo.pk)
    return render(request, 'core/confirmar_eliminacion.html', {'objeto': comprobacion, 'tipo': 'comprobación', 'titulo_pagina': f'Eliminar Comprobación de {equipo.nombre}'})


# --- Vistas de Baja de Equipo ---

@login_required
@permission_required('core.add_bajaequipo', raise_exception=True)
def dar_baja_equipo(request, equipo_pk):
    """
    Handles marking an equipment as decommissioned.
    """
    equipo = get_object_or_404(Equipo, pk=equipo_pk)

    if not request.user.is_superuser and request.user.empresa != equipo.empresa:
        messages.error(request, 'No tienes permiso para dar de baja este equipo.')
        return redirect('core:detalle_equipo', pk=equipo.pk)

    if BajaEquipo.objects.filter(equipo=equipo).exists():
        messages.warning(request, 'Este equipo ya tiene un registro de baja existente. Si desea activarlo, use la opción de activación.')
        return redirect('core:detalle_equipo', pk=equipo.pk)

    if equipo.estado == 'De Baja':
        messages.warning(request, 'Este equipo ya se encuentra dado de baja.')
        return redirect('core:detalle_equipo', pk=equipo.pk)

    if request.method == 'POST':
        form = BajaEquipoForm(request.POST, request.FILES)
        if form.is_valid():
            baja_registro = form.save(commit=False)
            baja_registro.equipo = equipo
            baja_registro.dado_de_baja_por = request.user
            baja_registro.save()
            messages.success(request, f'Equipo "{equipo.nombre}" dado de baja exitosamente.')
            return redirect('core:detalle_equipo', pk=equipo.pk)
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario de baja.')
    else:
        form = BajaEquipoForm()
    return render(request, 'core/dar_baja_equipo.html', {'form': form, 'equipo': equipo, 'titulo_pagina': f'Dar de Baja Equipo: {equipo.nombre}'})

@login_required
def activar_equipo(request, equipo_pk):
    """
    Activates a decommissioned equipment.
    """
    equipo = get_object_or_404(Equipo, pk=equipo_pk)
    if not request.user.is_superuser and request.user.empresa != equipo.empresa:
        messages.error(request, 'No tienes permiso para activar este equipo.')
        return redirect('core:detalle_equipo', pk=equipo.pk)

    if equipo.estado != 'De Baja':
        messages.warning(request, 'Este equipo no se encuentra de baja.')
        return redirect('core:detalle_equipo', pk=equipo.pk)

    if request.method == 'POST':
        try:
            BajaEquipo.objects.filter(equipo=equipo).delete()
            messages.success(request, f'Equipo "{equipo.nombre}" activado exitosamente.')
            return redirect('core:detalle_equipo', pk=equipo.pk)
        except Exception as e:
            messages.error(request, f'Error al activar el equipo: {e}')
            return redirect('core:detalle_equipo', pk=equipo.pk)
    return render(request, 'core/confirmar_activacion.html', {'equipo': equipo, 'titulo_pagina': f'Activar Equipo: {equipo.nombre}'})


# --- Vistas de Empresas ---

@login_required
@user_passes_test(lambda u: u.is_superuser, login_url='/core/access_denied/')
def listar_empresas(request):
    """
    Lists all companies, with filtering and pagination (superuser only).
    """
    query = request.GET.get('q')
    empresas_list = Empresa.objects.all()

    if query:
        empresas_list = empresas_list.filter(
            Q(nombre__icontains=query) |
            Q(nit__icontains=query) |
            Q(direccion__icontains=query) |
            Q(telefono__icontains=query) |
            Q(email__icontains=query)
        )

    paginator = Paginator(empresas_list, 10)
    page_number = request.GET.get('page')
    try:
        empresas = paginator.page(page_number)
    except PageNotAnInteger:
        empresas = paginator.page(1)
    except EmptyPage:
        empresas = paginator.page(paginator.num_pages)

    return render(request, 'core/listar_empresas.html', {'empresas': empresas, 'query': query, 'titulo_pagina': 'Listado de Empresas'})

@login_required
@user_passes_test(lambda u: u.is_superuser, login_url='/core/access_denied/')
def añadir_empresa(request):
    """
    Handles adding a new company (superuser only).
    """
    if request.method == 'POST':
        formulario = EmpresaForm(request.POST, request.FILES)
        if formulario.is_valid():
            formulario.save()
            messages.success(request, 'Empresa añadida exitosamente.')
            return redirect('core:listar_empresas')
        else:
            messages.error(request, 'Hubo un error al añadir la empresa. Por favor, revisa los datos.')
    else:
        formulario = EmpresaForm()
    return render(request, 'core/añadir_empresa.html', {'formulario': formulario, 'titulo_pagina': 'Añadir Nueva Empresa'})

@login_required
@user_passes_test(lambda u: u.is_superuser, login_url='/core/access_denied/')
def editar_empresa(request, pk):
    """
    Handles editing an existing company (superuser only).
    """
    empresa = get_object_or_404(Empresa, pk=pk)
    if request.method == 'POST':
        form = EmpresaForm(request.POST, request.FILES, instance=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Empresa actualizada exitosamente.')
            return redirect('core:detalle_empresa', pk=empresa.pk)
        else:
            messages.error(request, 'Hubo un error al actualizar la empresa. Por favor, revisa los datos.')
    else:
        form = EmpresaForm(instance=empresa)
    return render(request, 'core/editar_empresa.html', {'form': form, 'empresa': empresa, 'titulo_pagina': f'Editar Empresa: {empresa.nombre}'})

@login_required
@user_passes_test(lambda u: u.is_superuser, login_url='/core/access_denied/')
def eliminar_empresa(request, pk):
    """
    Handles deleting a company (superuser only).
    """
    empresa = get_object_or_404(Empresa, pk=pk)
    if request.method == 'POST':
        try:
            empresa.delete()
            messages.success(request, 'Empresa eliminada exitosamente.')
            return redirect('core:listar_empresas')
        except Exception as e:
            messages.error(request, f'Error al eliminar la empresa: {e}')
            return redirect('core:listar_empresas')
    return render(request, 'core/confirmar_eliminacion.html', {'objeto': empresa, 'tipo': 'empresa', 'titulo_pagina': f'Eliminar Empresa: {empresa.nombre}'})


@login_required
@user_passes_test(lambda u: u.is_superuser, login_url='/core/access_denied/')
def detalle_empresa(request, pk):
    """
    Displays the details of a specific company (superuser only).
    """
    empresa = get_object_or_404(Empresa, pk=pk)
    usuarios_empresa = CustomUser.objects.filter(empresa=empresa)
    equipos_empresa = Equipo.objects.filter(empresa=empresa)
    return render(request, 'core/detalle_empresa.html', {
        'empresa': empresa,
        'usuarios_empresa': usuarios_empresa,
        'equipos_empresa': equipos_empresa,
        'titulo_pagina': f'Detalle de Empresa: {empresa.nombre}',
    })

@login_required
@permission_required('core.change_empresa', raise_exception=True)
def añadir_usuario_a_empresa(request, empresa_pk):
    """
    Vista para añadir un usuario existente a una empresa específica.
    Solo accesible por superusuarios o usuarios con permiso para cambiar empresas.
    """
    empresa = get_object_or_404(Empresa, pk=empresa_pk)
    titulo_pagina = f"Añadir Usuario a {empresa.nombre}"

    if not request.user.is_superuser and request.user.empresa != empresa:
        messages.error(request, 'No tienes permiso para añadir usuarios a esta empresa.')
        return redirect('core:detalle_empresa', pk=empresa.pk)

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        if user_id:
            try:
                user_to_add = CustomUser.objects.get(pk=user_id)
                if user_to_add.empresa and user_to_add.empresa != empresa:
                    messages.warning(request, f"El usuario '{user_to_add.username}' ya está asociado a la empresa '{user_to_add.empresa.nombre}'. Se ha reasignado a '{empresa.nombre}'.")
                
                user_to_add.empresa = empresa
                user_to_add.save()
                messages.success(request, f"Usuario '{user_to_add.username}' añadido exitosamente a '{empresa.nombre}'.")
                return redirect('core:detalle_empresa', pk=empresa.pk)
            except CustomUser.DoesNotExist:
                messages.error(request, "El usuario seleccionado no existe.")
            except Exception as e:
                messages.error(request, f"Error al añadir usuario: {e}")
        else:
            messages.error(request, "Por favor, selecciona un usuario.")
    
    users_available = CustomUser.objects.filter(is_superuser=False).exclude(empresa=empresa)

    context = {
        'empresa': empresa,
        'users_available': users_available,
        'titulo_pagina': titulo_pagina,
    }
    return render(request, 'core/añadir_usuario_a_empresa.html', context)


# --- Vistas de Ubicación ---
@login_required
@permission_required('core.can_view_ubicacion', raise_exception=True)
def listar_ubicaciones(request):
    """
    Lists all locations.
    """
    ubicaciones = Ubicacion.objects.all()
    return render(request, 'core/listar_ubicaciones.html', {'ubicaciones': ubicaciones, 'titulo_pagina': 'Listado de Ubicaciones'})

@login_required
@permission_required('core.can_add_ubicacion', raise_exception=True)
def añadir_ubicacion(request):
    """
    Handles adding a new location.
    """
    if request.method == 'POST':
        form = UbicacionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ubicación añadida exitosamente.')
            return redirect('core:listar_ubicaciones')
        else:
            messages.error(request, 'Hubo un error al añadir la ubicación. Por favor, revisa los datos.')
    else:
        form = UbicacionForm()
    return render(request, 'core/añadir_ubicacion.html', {'form': form, 'titulo_pagina': 'Añadir Nueva Ubicación'})

@login_required
@permission_required('core.can_change_ubicacion', raise_exception=True)
def editar_ubicacion(request, pk):
    """
    Handles editing an existing location.
    """
    ubicacion = get_object_or_404(Ubicacion, pk=pk)
    if request.method == 'POST':
        form = UbicacionForm(request.POST, instance=ubicacion)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ubicación actualizada exitosamente.')
            return redirect('core:listar_ubicaciones')
        else:
            messages.error(request, 'Hubo un error al actualizar la ubicación. Por favor, revisa los datos.')
    else:
        form = UbicacionForm(instance=ubicacion)
    return render(request, 'core/editar_ubicacion.html', {'form': form, 'ubicacion': ubicacion, 'titulo_pagina': f'Editar Ubicación: {ubicacion.nombre}'})

@login_required
@permission_required('core.can_delete_ubicacion', raise_exception=True)
def eliminar_ubicacion(request, pk):
    """
    Handles deleting a location.
    """
    ubicacion = get_object_or_404(Ubicacion, pk=pk)
    if request.method == 'POST':
        ubicacion.delete()
        messages.success(request, 'Ubicación eliminada exitosamente.')
        return redirect('core:listar_ubicaciones')
    return render(request, 'core/confirmar_eliminacion.html', {'objeto': ubicacion, 'tipo': 'ubicación', 'titulo_pagina': f'Eliminar Ubicación: {ubicacion.nombre}'})

# --- Vistas de Procedimiento ---
@login_required
@permission_required('core.can_view_procedimiento', raise_exception=True)
def listar_procedimientos(request):
    """
    Lists all procedures.
    """
    procedimientos = Procedimiento.objects.all()
    return render(request, 'core/listar_procedimientos.html', {'procedimientos': procedimientos, 'titulo_pagina': 'Listado de Procedimientos'})

@login_required
@permission_required('core.can_add_procedimiento', raise_exception=True)
def añadir_procedimiento(request):
    """
    Handles adding a new procedure.
    """
    if request.method == 'POST':
        form = ProcedimientoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Procedimiento añadido exitosamente.')
            return redirect('core:listar_procedimientos')
        else:
            messages.error(request, 'Hubo un error al añadir el procedimiento. Por favor, revisa los datos.')
    else:
        form = ProcedimientoForm()
    return render(request, 'core/añadir_procedimiento.html', {'form': form, 'titulo_pagina': 'Añadir Nuevo Procedimiento'})

@login_required
@permission_required('core.can_change_procedimiento', raise_exception=True)
def editar_procedimiento(request, pk):
    """
    Handles editing an existing procedure.
    """
    procedimiento = get_object_or_404(Procedimiento, pk=pk)
    if request.method == 'POST':
        form = ProcedimientoForm(request.POST, request.FILES, instance=procedimiento)
        if form.is_valid():
            form.save()
            messages.success(request, 'Procedimiento actualizado exitosamente.')
            return redirect('core:listar_procedimientos')
        else:
            messages.error(request, 'Hubo un error al actualizar el procedimiento. Por favor, revisa los datos.')
    else:
        form = ProcedimientoForm(instance=procedimiento)
    return render(request, 'core/editar_procedimiento.html', {'form': form, 'procedimiento': procedimiento, 'titulo_pagina': f'Editar Procedimiento: {procedimiento.nombre}'})

@login_required
@permission_required('core.can_delete_procedimiento', raise_exception=True)
def eliminar_procedimiento(request, pk):
    """
    Handles deleting a procedure.
    """
    procedimiento = get_object_or_404(Procedimiento, pk=pk)
    if request.method == 'POST':
        procedimiento.delete()
        messages.success(request, 'Procedimiento eliminado exitosamente.')
        return redirect('core:listar_procedimientos')
    return render(request, 'core/confirmar_eliminacion.html', {'objeto': procedimiento, 'tipo': 'procedimiento', 'titulo_pagina': f'Eliminar Procedimiento: {procedimiento.nombre}'})

# --- Vistas de Proveedores de Calibración (EXISTENTES) ---
@login_required
@permission_required('core.can_view_proveedorcalibracion', raise_exception=True)
def listar_proveedores_calibracion(request):
    """
    Lists all calibration providers.
    """
    proveedores = ProveedorCalibracion.objects.all()
    return render(request, 'core/listar_proveedores_calibracion.html', {'proveedores': proveedores, 'titulo_pagina': 'Listado de Proveedores de Calibración'})

@login_required
@permission_required('core.can_add_proveedorcalibracion', raise_exception=True)
def añadir_proveedor_calibracion(request):
    """
    Handles adding a new calibration provider.
    """
    if request.method == 'POST':
        form = ProveedorCalibracionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Proveedor de Calibración añadido exitosamente.')
            return redirect('core:listar_proveedores_calibracion')
        else:
            messages.error(request, 'Hubo un error al añadir el proveedor. Por favor, revisa los datos.')
    else:
        form = ProveedorCalibracionForm()
    return render(request, 'core/añadir_proveedor_calibracion.html', {'form': form, 'titulo_pagina': 'Añadir Nuevo Proveedor de Calibración'})

@login_required
@permission_required('core.can_change_proveedorcalibracion', raise_exception=True)
def editar_proveedor_calibracion(request, pk):
    """
    Handles editing an existing calibration provider.
    """
    proveedor = get_object_or_404(ProveedorCalibracion, pk=pk)
    if request.method == 'POST':
        form = ProveedorCalibracionForm(request.POST, instance=proveedor)
        if form.is_valid():
            form.save()
            messages.success(request, 'Proveedor de Calibración actualizado exitosamente.')
            return redirect('core:listar_proveedores_calibracion')
        else:
            messages.error(request, 'Hubo un error al actualizar el proveedor. Por favor, revisa los datos.')
    else:
        form = ProveedorCalibracionForm(instance=proveedor)
    return render(request, 'core/editar_proveedor_calibracion.html', {'form': form, 'proveedor': proveedor, 'titulo_pagina': f'Editar Proveedor de Calibración: {proveedor.nombre}'})

@login_required
@permission_required('core.can_delete_proveedorcalibracion', raise_exception=True)
def eliminar_proveedor_calibracion(request, pk):
    """
    Handles deleting a calibration provider.
    """
    proveedor = get_object_or_404(ProveedorCalibracion, pk=pk)
    if request.method == 'POST':
        proveedor.delete()
        messages.success(request, 'Proveedor de Calibración eliminado exitosamente.')
        return redirect('core:listar_proveedores_calibracion')
    return render(request, 'core/confirmar_eliminacion.html', {'objeto': proveedor, 'tipo': 'proveedor de calibración', 'titulo_pagina': f'Eliminar Proveedor de Calibración: {proveedor.nombre}'})

@login_required
@permission_required('core.can_view_proveedormantenimiento', raise_exception=True)
def listar_proveedores_mantenimiento(request):
    """
    Lists all maintenance providers.
    """
    proveedores = ProveedorMantenimiento.objects.all()
    return render(request, 'core/listar_proveedores_mantenimiento.html', {'proveedores': proveedores, 'titulo_pagina': 'Listado de Proveedores de Mantenimiento'})

@login_required
@permission_required('core.can_add_proveedormantenimiento', raise_exception=True)
def añadir_proveedor_mantenimiento(request):
    """
    Handles adding a new maintenance provider.
    """
    if request.method == 'POST':
        form = ProveedorMantenimientoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Proveedor de Mantenimiento añadido exitosamente.')
            return redirect('core:listar_proveedores_mantenimiento')
        else:
            messages.error(request, 'Hubo un error al añadir el proveedor. Por favor, revisa los datos.')
    else:
        form = ProveedorMantenimientoForm()
    return render(request, 'core/añadir_proveedor_mantenimiento.html', {'form': form, 'titulo_pagina': 'Añadir Nuevo Proveedor de Mantenimiento'})

@login_required
@permission_required('core.can_change_proveedormantenimiento', raise_exception=True)
def editar_proveedor_mantenimiento(request, pk):
    """
    Handles editing an existing maintenance provider.
    """
    proveedor = get_object_or_404(ProveedorMantenimiento, pk=pk)
    if request.method == 'POST':
        form = ProveedorMantenimientoForm(request.POST, instance=proveedor)
        if form.is_valid():
            form.save()
            messages.success(request, 'Proveedor de Mantenimiento actualizado exitosamente.')
            return redirect('core:listar_proveedores_mantenimiento')
        else:
            messages.error(request, 'Hubo un error al actualizar el proveedor. Por favor, revisa los datos.')
    else:
        form = ProveedorMantenimientoForm(instance=proveedor)
    return render(request, 'core/editar_proveedor_mantenimiento.html', {'form': form, 'proveedor': proveedor, 'titulo_pagina': f'Editar Proveedor de Mantenimiento: {proveedor.nombre}'})

@login_required
@permission_required('core.can_delete_proveedormantenimiento', raise_exception=True)
def eliminar_proveedor_mantenimiento(request, pk):
    """
    Handles deleting a maintenance provider.
    """
    proveedor = get_object_or_404(ProveedorMantenimiento, pk=pk)
    if request.method == 'POST':
        proveedor.delete()
        messages.success(request, 'Proveedor de Mantenimiento eliminado exitosamente.')
        return redirect('core:listar_proveedores_mantenimiento')
    return render(request, 'core/confirmar_eliminacion.html', {'objeto': proveedor, 'tipo': 'proveedor de mantenimiento', 'titulo_pagina': f'Eliminar Proveedor de Mantenimiento: {proveedor.nombre}'})

@login_required
@permission_required('core.can_view_proveedorcomprobacion', raise_exception=True)
def listar_proveedores_comprobacion(request):
    """
    Lists all verification providers.
    """
    proveedores = ProveedorComprobacion.objects.all()
    return render(request, 'core/listar_proveedores_comprobacion.html', {'proveedores': proveedores, 'titulo_pagina': 'Listado de Proveedores de Comprobación'})

@login_required
@permission_required('core.can_add_proveedorcomprobacion', raise_exception=True)
def añadir_proveedor_comprobacion(request):
    """
    Handles adding a new verification provider.
    """
    if request.method == 'POST':
        form = ProveedorComprobacionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Proveedor de Comprobación añadido exitosamente.')
            return redirect('core:listar_proveedores_comprobacion')
        else:
            messages.error(request, 'Hubo un error al añadir el proveedor. Por favor, revisa los datos.')
    else:
        form = ProveedorComprobacionForm()
    return render(request, 'core/añadir_proveedor_comprobacion.html', {'form': form, 'titulo_pagina': 'Añadir Nuevo Proveedor de Comprobación'})

@login_required
@permission_required('core.can_change_proveedorcomprobacion', raise_exception=True)
def editar_proveedor_comprobacion(request, pk):
    """
    Handles editing an existing verification provider.
    """
    proveedor = get_object_or_404(ProveedorComprobacion, pk=pk)
    if request.method == 'POST':
        form = ProveedorComprobacionForm(request.POST, instance=proveedor)
        if form.is_valid():
            form.save()
            messages.success(request, 'Proveedor de Comprobación actualizado exitosamente.')
            return redirect('core:listar_proveedores_comprobacion')
        else:
            messages.error(request, 'Hubo un error al actualizar el proveedor. Por favor, revisa los datos.')
    else:
        form = ProveedorComprobacionForm(instance=proveedor)
    return render(request, 'core/editar_proveedor_comprobacion.html', {'form': form, 'proveedor': proveedor, 'titulo_pagina': f'Editar Proveedor de Comprobación: {proveedor.nombre}'})

@login_required
@permission_required('core.can_delete_proveedorcomprobacion', raise_exception=True)
def eliminar_proveedor_comprobacion(request, pk):
    """
    Handles deleting a verification provider.
    """
    proveedor = get_object_or_404(ProveedorComprobacion, pk=pk)
    if request.method == 'POST':
        proveedor.delete()
        messages.success(request, 'Proveedor de Comprobación eliminado exitosamente.')
        return redirect('core:listar_proveedores_comprobacion')
    return render(request, 'core/confirmar_eliminacion.html', {'objeto': proveedor, 'tipo': 'proveedor de comprobación', 'titulo_pagina': f'Eliminar Proveedor de Comprobación: {proveedor.nombre}'})

# --- NUEVAS VISTAS PARA EL MODELO PROVEEDOR GENERAL ---

@login_required
@permission_required('core.can_view_proveedor', raise_exception=True)
def listar_proveedores(request):
    """
    Lists all general providers, with filtering and pagination.
    """
    query = request.GET.get('q')
    tipo_servicio_filter = request.GET.get('tipo_servicio')

    proveedores_list = Proveedor.objects.all().order_by('nombre_empresa')

    if not request.user.is_superuser:
        proveedores_list = proveedores_list.filter(empresa=request.user.empresa)

    if query:
        proveedores_list = proveedores_list.filter(
            Q(nombre_empresa__icontains=query) |
            Q(nombre_contacto__icontains=query) |
            Q(correo_electronico__icontains=query) |
            Q(alcance__icontains=query) |
            Q(servicio_prestado__icontains=query)
        )
    
    if tipo_servicio_filter and tipo_servicio_filter != '': 
        proveedores_list = proveedores_list.filter(tipo_servicio=tipo_servicio_filter)


    paginator = Paginator(proveedores_list, 10)
    page_number = request.GET.get('page')
    try:
        proveedores = paginator.page(page_number)
    except PageNotAnInteger:
        proveedores = paginator.page(1)
    except EmptyPage:
        proveedores = paginator.page(paginator.num_pages)

    tipo_servicio_choices = Proveedor.TIPO_SERVICIO_CHOICES

    context = {
        'proveedores': proveedores,
        'query': query,
        'tipo_servicio_choices': tipo_servicio_choices,
        'tipo_servicio_filter': tipo_servicio_filter,
        'titulo_pagina': 'Listado de Proveedores',
    }
    return render(request, 'core/listar_proveedores.html', context)


@login_required
@permission_required('core.can_add_proveedor', raise_exception=True)
def añadir_proveedor(request):
    """
    Handles adding a new general provider.
    """
    if request.method == 'POST':
        form = ProveedorForm(request.POST, request=request)
        if form.is_valid():
            proveedor = form.save(commit=False)
            proveedor.save()
            messages.success(request, 'Proveedor añadido exitosamente.')
            return redirect('core:listar_proveedores')
        else:
            messages.error(request, 'Hubo un error al añadir el proveedor. Por favor, revisa los datos.')
    else:
        form = ProveedorForm(request=request)

    return render(request, 'core/añadir_proveedor.html', {'form': form, 'titulo_pagina': 'Añadir Nuevo Proveedor'})


@login_required
@permission_required('core.can_change_proveedor', raise_exception=True)
def editar_proveedor(request, pk):
    """
    Handles editing an existing general provider.
    """
    proveedor = get_object_or_404(Proveedor, pk=pk)

    if not request.user.is_superuser and proveedor.empresa != request.user.empresa:
        messages.error(request, 'No tienes permiso para editar este proveedor.')
        return redirect('core:listar_proveedores')

    if request.method == 'POST':
        form = ProveedorForm(request.POST, instance=proveedor, request=request)
        if form.is_valid():
            proveedor = form.save(commit=False)
            proveedor.save()
            messages.success(request, 'Proveedor actualizado exitosamente.')
            return redirect('core:listar_proveedores')
        else:
            messages.error(request, 'Hubo un error al actualizar el proveedor. Por favor, revisa los datos.')
    else:
        form = ProveedorForm(instance=proveedor, request=request)
    return render(request, 'core/editar_proveedor.html', {'form': form, 'proveedor': proveedor, 'titulo_pagina': f'Editar Proveedor: {proveedor.nombre_empresa}'})


@login_required
@permission_required('core.can_delete_proveedor', raise_exception=True)
def eliminar_proveedor(request, pk):
    """
    Handles deleting a general provider.
    """
    proveedor = get_object_or_404(Proveedor, pk=pk)

    if not request.user.is_superuser and proveedor.empresa != request.user.empresa:
        messages.error(request, 'No tienes permiso para eliminar este proveedor.')
        return redirect('core:listar_proveedores')

    if request.method == 'POST':
        try:
            proveedor.delete()
            messages.success(request, 'Proveedor eliminado exitosamente.')
            return redirect('core:listar_proveedores')
        except Exception as e:
            messages.error(request, f'Error al eliminar el proveedor: {e}')
            return redirect('core:listar_proveedores')
    return render(request, 'core/confirmar_eliminacion.html', {'objeto': proveedor, 'tipo': 'proveedor', 'titulo_pagina': f'Eliminar Proveedor: {proveedor.nombre_empresa}'})


@login_required
@permission_required('core.can_view_proveedor', raise_exception=True)
def detalle_proveedor(request, pk):
    """
    Displays the details of a specific general provider.
    """
    proveedor = get_object_or_404(Proveedor, pk=pk)

    if not request.user.is_superuser and proveedor.empresa != request.user.empresa:
        messages.error(request, 'No tienes permiso para ver este proveedor.')
        return redirect('core:listar_proveedores')

    context = {
        'proveedor': proveedor,
        'titulo_pagina': f'Detalle de Proveedor: {proveedor.nombre_empresa}',
    }
    return render(request, 'core/detalle_proveedor.html', context)


# --- Vistas de Usuarios ---

@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser, login_url='/core/access_denied/')
def listar_usuarios(request):
    """
    Lists all custom users, with filtering and pagination.
    """
    query = request.GET.get('q')
    usuarios_list = CustomUser.objects.all()

    if not request.user.is_superuser:
        usuarios_list = usuarios_list.filter(empresa=request.user.empresa)

    if query:
        usuarios_list = usuarios_list.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query) |
            Q(empresa__nombre__icontains=query)
        )

    paginator = Paginator(usuarios_list, 10)
    page_number = request.GET.get('page')
    try:
        usuarios = paginator.page(page_number)
    except PageNotAnInteger:
        usuarios = paginator.page(1)
    except EmptyPage:
        usuarios = paginator.page(paginator.num_pages)

    return render(request, 'core/listar_usuarios.html', {'usuarios': usuarios, 'query': query, 'titulo_pagina': 'Listado de Usuarios'})


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser, login_url='/core/access_denied/')
def añadir_usuario(request, empresa_pk=None):
    """
    Handles adding a new custom user.
    """
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, request=request)
        if form.is_valid():
            user = form.save(commit=False)
            user.save()
            messages.success(request, 'Usuario añadido exitosamente.')
            return redirect('core:listar_usuarios')
        else:
            messages.error(request, 'Hubo un error al añadir el usuario. Por favor, revisa los datos.')
    else:
        form = CustomUserCreationForm(request=request)
        if empresa_pk:
            form.fields['empresa'].initial = get_object_or_404(Empresa, pk=empresa_pk)

    return render(request, 'core/añadir_usuario.html', {'form': form, 'empresa_pk': empresa_pk, 'titulo_pagina': 'Añadir Nuevo Usuario'})


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser, login_url='/core/access_denied/')
def detalle_usuario(request, pk):
    """
    Displays the details of a specific custom user.
    """
    usuario = get_object_or_404(CustomUser, pk=pk)

    if not request.user.is_superuser and request.user.pk != usuario.pk:
        messages.error(request, 'No tienes permiso para ver este perfil de usuario.')
        return redirect('core:perfil_usuario')

    if request.user.is_staff and not request.user.is_superuser and usuario.empresa != request.user.empresa:
        messages.error(request, 'No tienes permiso para ver usuarios de otras empresas.')
        return redirect('core:listar_usuarios')

    return render(request, 'core/detalle_usuario.html', {
        'usuario_a_ver': usuario,
        'titulo_pagina': f'Detalle de Usuario: {usuario.username}',
    })


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser, login_url='/core/access_denied/')
def editar_usuario(request, pk):
    """
    Handles editing an existing custom user.
    """
    usuario_a_editar = get_object_or_404(CustomUser, pk=pk)

    if not request.user.is_superuser:
        if request.user.pk == usuario_a_editar.pk:
            return redirect('core:perfil_usuario')
        elif not request.user.is_staff or request.user.empresa != usuario_a_editar.empresa:
            messages.error(request, 'No tienes permiso para editar este usuario.')
            return redirect('core:listar_usuarios')

    if request.method == 'POST':
        form = CustomUserChangeForm(request.POST, instance=usuario_a_editar, request=request)
        if form.is_valid():
            user = form.save(commit=False)
            if not request.user.is_superuser:
                user.empresa = usuario_a_editar.empresa
            user.save()
            messages.success(request, f'Usuario "{user.username}" actualizado exitosamente.')
            return redirect('core:detalle_usuario', pk=usuario_a_editar.pk)
        else:
            messages.error(request, 'Hubo un error al actualizar el usuario. Por favor, revisa los datos.')
    else:
        form = CustomUserChangeForm(instance=usuario_a_editar, request=request)

    return render(request, 'core/editar_usuario.html', {'form': form, 'usuario_a_editar': usuario_a_editar, 'titulo_pagina': f'Editar Usuario: {usuario_a_editar.username}'})


@login_required
@user_passes_test(lambda u: u.is_superuser, login_url='/core/access_denied/')
def eliminar_usuario(request, pk):
    """
    Handles deleting a custom user (superuser only).
    """
    usuario = get_object_or_404(CustomUser, pk=pk)

    if request.user.pk == usuario.pk:
        messages.error(request, 'No puedes eliminar tu propia cuenta de superusuario.')
        return redirect('core:listar_usuarios')

    if not request.user.is_superuser and request.user.empresa != usuario.empresa:
        messages.error(request, 'No tienes permiso para eliminar usuarios de otras empresas.')
        return redirect('core:listar_usuarios')

    if request.method == 'POST':
        try:
            usuario.delete()
            messages.success(request, 'Usuario eliminado exitosamente.')
            return redirect('core:listar_usuarios')
        except Exception as e:
            messages.error(request, f'Error al eliminar el usuario: {e}')
            return redirect('core:detalle_usuario', pk=usuario.pk)
    return render(request, 'core/confirmar_eliminacion.html', {'objeto': usuario, 'tipo': 'usuario', 'titulo_pagina': f'Eliminar Usuario: {usuario.username}'})


@login_required
@permission_required('auth.change_user', raise_exception=True)
def change_user_password(request, pk):
    """
    Handles changing another user's password (admin only).
    """
    user_to_change = get_object_or_404(CustomUser, pk=pk)

    if request.user.pk == user_to_change.pk:
        messages.warning(request, "No puedes cambiar tu propia contraseña desde esta sección. Usa 'Mi Perfil' -> 'Cambiar contraseña'.")
        return redirect('core:detalle_usuario', pk=pk)

    if not request.user.is_superuser:
        messages.error(request, 'No tienes permiso para cambiar la contraseña de otros usuarios.')
        return redirect('core:detalle_usuario', pk=pk)

    if request.method == 'POST':
        form = PasswordChangeForm(user_to_change, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f'La contraseña de "{user_to_change.username}" ha sido actualizada exitosamente.')
            return redirect('core:detalle_usuario', pk=user_to_change.pk)
        else:
            messages.error(request, 'Por favor, corrige los errores a continuación.')
    else:
        form = PasswordChangeForm(user_to_change)

    context = {
        'form': form,
        'user_to_change': user_to_change,
        'titulo_pagina': f'Cambiar Contraseña de {user_to_change.username}'
    }
    return render(request, 'core/change_user_password.html', context)


# --- Funciones Auxiliares para Generación de PDF (se mantienen para Hoja de Vida y Listado General) ---

def _generate_pdf_content(request, template_path, context):
    """
    Generates PDF content (bytes) from a template and context using WeasyPrint.
    """
    from django.template.loader import get_template

    template = get_template(template_path)
    html_string = template.render(context)
    
    pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
    
    return pdf_file

def _generate_equipment_hoja_vida_pdf_content(request, equipo):
    """
    Generates the PDF content for an equipment's "Hoja de Vida".
    """
    calibraciones = equipo.calibraciones.all().order_by('-fecha_calibracion')
    mantenimientos = equipo.mantenimientos.all().order_by('-fecha_mantenimiento')
    comprobaciones = equipo.comprobaciones.all().order_by('-fecha_comprobacion')
    baja_registro = None
    try:
        baja_registro = equipo.baja_registro
    except BajaEquipo.DoesNotExist:
        pass

    # Utilizar default_storage para acceder a las URLs de los archivos
    from django.core.files.storage import default_storage

    # Helper para obtener URL segura desde default_storage
    def get_file_url(file_field):
        if file_field and default_storage.exists(file_field.name):
            return request.build_absolute_uri(file_field.url)
        return None

    logo_empresa_url = get_file_url(equipo.empresa.logo_empresa) if equipo.empresa else None
    imagen_equipo_url = get_file_url(equipo.imagen_equipo)
    documento_baja_url = get_file_url(baja_registro.documento_baja) if baja_registro else None

    for cal in calibraciones:
        cal.documento_calibracion_url = get_file_url(cal.documento_calibracion)
        cal.confirmacion_metrologica_pdf_url = get_file_url(cal.confirmacion_metrologica_pdf)
        cal.intervalos_calibracion_pdf_url = get_file_url(cal.intervalos_calibracion_pdf)

    for mant in mantenimientos:
        mant.documento_mantenimiento_url = get_file_url(mant.documento_mantenimiento)
    for comp in comprobaciones:
        comp.documento_comprobacion_url = get_file_url(comp.documento_comprobacion)

    archivo_compra_pdf_url = get_file_url(equipo.archivo_compra_pdf)
    ficha_tecnica_pdf_url = get_file_url(equipo.ficha_tecnica_pdf)
    manual_pdf_url = get_file_url(equipo.manual_pdf)
    otros_documentos_pdf_url = get_file_url(equipo.otros_documentos_pdf)

    context = {
        'equipo': equipo,
        'calibraciones': calibraciones,
        'mantenimientos': mantenimientos,
        'comprobaciones': comprobaciones,
        'baja_registro': baja_registro,
        'logo_empresa_url': logo_empresa_url,
        'imagen_equipo_url': imagen_equipo_url,
        'documento_baja_url': documento_baja_url,
        'archivo_compra_pdf_url': archivo_compra_pdf_url,
        'ficha_tecnica_pdf_url': ficha_tecnica_pdf_url,
        'manual_pdf_url': manual_pdf_url,
        'otros_documentos_pdf_url': otros_documentos_pdf_url,
        'titulo_pagina': f'Hoja de Vida de {equipo.nombre}',
    }
    return _generate_pdf_content(request, 'core/hoja_vida_pdf.html', context)


def _generate_equipment_activities_excel_content(equipo):
    """
    Generates an Excel file with the activities (calibrations, maintenances, verifications) of a specific equipment.
    """
    workbook = Workbook()

    sheet_cal = workbook.active
    sheet_cal.title = "Calibraciones"
    headers_cal = ["Fecha Calibración", "Proveedor", "Resultado", "Número Certificado", "Observaciones"]
    sheet_cal.append(headers_cal)
    for cal in equipo.calibraciones.all().order_by('fecha_calibracion'):
        proveedor_nombre = cal.nombre_proveedor if cal.nombre_proveedor else ''
        sheet_cal.append([
            cal.fecha_calibracion.strftime('%Y-%m-%d') if cal.fecha_calibracion else '',
            proveedor_nombre, 
            cal.resultado,
            cal.numero_certificado,
            cal.observaciones
        ])
    for col in sheet_cal.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2)
        sheet_cal.column_dimensions[column].width = adjusted_width

    sheet_mant = workbook.create_sheet("Mantenimientos")
    headers_mant = ["Fecha Mantenimiento", "Tipo", "Proveedor", "Responsable", "Costo", "Descripción"]
    sheet_mant.append(headers_mant)
    for mant in equipo.mantenimientos.all().order_by('fecha_mantenimiento'):
        proveedor_nombre = mant.nombre_proveedor if mant.nombre_proveedor else ''
        sheet_mant.append([
            mant.fecha_mantenimiento.strftime('%Y-%m-%d') if mant.fecha_mantenimiento else '',
            mant.get_tipo_mantenimiento_display(),
            proveedor_nombre, 
            mant.responsable,
            float(mant.costo) if mant.costo is not None else '',
            mant.descripcion
        ])
    for col in sheet_mant.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2)
        sheet_mant.column_dimensions[column].width = adjusted_width

    sheet_comp = workbook.create_sheet("Comprobaciones")
    headers_comp = ["Fecha Comprobación", "Proveedor", "Responsable", "Resultado", "Observaciones"]
    sheet_comp.append(headers_comp)
    for comp in equipo.comprobaciones.all().order_by('fecha_comprobacion'):
        proveedor_nombre = comp.nombre_proveedor if comp.nombre_proveedor else ''
        sheet_comp.append([
            comp.fecha_comprobacion.strftime('%Y-%m-%d') if comp.fecha_comprobacion else '',
            proveedor_nombre, 
            comp.responsable,
            comp.resultado,
            comp.observaciones
        ])
    for col in sheet_comp.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2)
        sheet_comp.column_dimensions[column].width = adjusted_width

    excel_buffer = io.BytesIO()
    workbook.save(excel_buffer)
    excel_buffer.seek(0)
    return excel_buffer.getvalue()


def _generate_equipment_general_info_excel_content(equipo):
    """
    Generates an Excel file with the general information of a specific equipment.
    """
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Información General"

    headers = [
        "Campo", "Valor"
    ]
    sheet.append(headers)

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")
    header_border = Border(left=Side(style='thin'),
                           right=Side(style='thin'),
                           top=Side(style='thin'),
                           bottom=Side(style='thin'))

    for col_num, header_text in enumerate(headers, 1):
        cell = sheet.cell(row=1, column=col_num, value=header_text)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = header_border
        sheet.column_dimensions[cell.column_letter].width = 30

    general_info = [
        ("Código Interno", equipo.codigo_interno),
        ("Nombre", equipo.nombre),
        ("Empresa", equipo.empresa.nombre if equipo.empresa else "N/A"),
        ("Tipo de Equipo", equipo.get_tipo_equipo_display()),
        ("Marca", equipo.marca),
        ("Modelo", equipo.modelo),
        ("Número de Serie", equipo.numero_serie),
        ("Ubicación", equipo.ubicacion),
        ("Responsable", equipo.responsable),
        ("Estado", equipo.estado),
        ("Fecha de Adquisición", equipo.fecha_adquisicion.strftime('%Y-%m-%d') if equipo.fecha_adquisicion else ''),
        ("Rango de Medida", equipo.rango_medida),
        ("Resolución", equipo.resolucion),
        ("Error Máximo Permisible", equipo.error_maximo_permisible if equipo.error_maximo_permisible is not None else ''),
        ("Fecha de Registro", equipo.fecha_registro.strftime('%Y-%m-%d %H:%M:%S') if equipo.fecha_registro else ''),
        ("Observaciones", equipo.observaciones),
        ("Versión Formato Equipo", equipo.version_formato),
        ("Fecha Versión Formato Equipo", equipo.fecha_version_formato.strftime('%Y-%m-%d') if equipo.fecha_version_formato else ''),
        ("Codificación Formato Equipo", equipo.codificacion_formato),
        ("Fecha Última Calibración", equipo.fecha_ultima_calibracion.strftime('%Y-%m-%d') if equipo.fecha_ultima_calibracion else ''),
        ("Próxima Calibración", equipo.proxima_calibracion.strftime('%Y-%m-%d') if equipo.proxima_calibracion else ''),
        ("Frecuencia Calibración (meses)", float(equipo.frecuencia_calibracion_meses) if equipo.frecuencia_calibracion_meses is not None else ''),
        ("Fecha Último Mantenimiento", equipo.fecha_ultimo_mantenimiento.strftime('%Y-%m-%d') if equipo.fecha_ultimo_mantenimiento else ''),
        ("Próximo Mantenimiento", equipo.proximo_mantenimiento.strftime('%Y-%m-%d') if equipo.proximo_mantenimiento else ''),
        ("Frecuencia Mantenimiento (meses)", float(equipo.frecuencia_mantenimiento_meses) if equipo.frecuencia_mantenimiento_meses is not None else ''),
        ("Fecha Última Comprobación", equipo.fecha_ultima_comprobacion.strftime('%Y-%m-%d') if equipo.fecha_ultima_comprobacion else ''),
        ("Próxima Comprobación", equipo.proxima_comprobacion.strftime('%Y-%m-%d') if equipo.proxima_comprobacion else ''),
        ("Frecuencia Comprobación (meses)", float(equipo.frecuencia_comprobacion_meses) if equipo.frecuencia_comprobacion_meses is not None else ''),
    ]

    for label, value in general_info:
        sheet.append([label, value])

    for col in sheet.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2)
        sheet.column_dimensions[column].width = adjusted_width

    excel_buffer = io.BytesIO()
    workbook.save(excel_buffer)
    excel_buffer.seek(0)
    return excel_buffer.getvalue()


def _generate_general_equipment_list_excel_content(equipos_queryset):
    """
    Generates an Excel file with the general list of equipment.
    """
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Listado de Equipos"

    headers = [
        "Código Interno", "Nombre", "Empresa", "Tipo de Equipo", "Ubicación",
        "Responsable", "Marca", "Modelo", "Número de Serie", "Rango de Medida",
        "Resolución", "Error Máximo Permisible", "Estado", "Fecha de Adquisición", "Fecha de Registro",
        "Observaciones",
        "Versión Formato Equipo", "Fecha Versión Formato Equipo", "Codificación Formato Equipo",
        "Fecha Última Calibración", "Próxima Calibración", "Frecuencia Calibración (meses)",
        "Fecha Último Mantenimiento", "Próximo Mantenimiento", "Frecuencia Mantenimiento (meses)",
        "Fecha Última Comprobación", "Próxima Comprobación", "Frecuencia Comprobación (meses)"
    ]
    sheet.append(headers)

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")
    header_border = Border(left=Side(style='thin'),
                           right=Side(style='thin'),
                           top=Side(style='thin'),
                           bottom=Side(style='thin'))

    for col_num, header_text in enumerate(headers, 1):
        cell = sheet.cell(row=1, column=col_num, value=header_text)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = header_border
        sheet.column_dimensions[cell.column_letter].width = 20

    for equipo in equipos_queryset:
        row_data = [
            equipo.codigo_interno,
            equipo.nombre,
            equipo.empresa.nombre if equipo.empresa else "N/A",
            equipo.get_tipo_equipo_display(),
            equipo.ubicacion,
            equipo.responsable,
            equipo.marca,
            equipo.modelo,
            equipo.numero_serie,
            equipo.rango_medida,
            equipo.resolucion,
            equipo.error_maximo_permisible if equipo.error_maximo_permisible is not None else '',
            equipo.estado,
            equipo.fecha_adquisicion.strftime('%Y-%m-%d') if equipo.fecha_adquisicion else '',
            equipo.fecha_registro.strftime('%Y-%m-%d %H:%M:%S') if equipo.fecha_registro else '',
            equipo.observaciones,
            equipo.version_formato,
            equipo.fecha_version_formato.strftime('%Y-%m-%d') if equipo.fecha_version_formato else '',
            equipo.codificacion_formato,
            equipo.fecha_ultima_calibracion.strftime('%Y-%m-%d') if equipo.fecha_ultima_calibracion else '',
            equipo.proxima_calibracion.strftime('%Y-%m-%d') if equipo.proxima_calibracion else '',
            float(equipo.frecuencia_calibracion_meses) if equipo.frecuencia_calibracion_meses is not None else '',
            equipo.fecha_ultimo_mantenimiento.strftime('%Y-%m-%d') if equipo.fecha_ultimo_mantenimiento else '',
            equipo.proximo_mantenimiento.strftime('%Y-%m-%d') if equipo.proximo_mantenimiento else '',
            float(equipo.frecuencia_mantenimiento_meses) if equipo.frecuencia_mantenimiento_meses is not None else '',
            equipo.fecha_ultima_comprobacion.strftime('%Y-%m-%d') if equipo.fecha_ultima_comprobacion else '',
            equipo.proxima_comprobacion.strftime('%Y-%m-%d') if equipo.proxima_comprobacion else '',
            float(equipo.frecuencia_comprobacion_meses) if equipo.frecuencia_comprobacion_meses is not None else '',
        ]
        sheet.append(row_data)

    for col in sheet.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2)
        sheet.column_dimensions[column].width = adjusted_width

    excel_buffer = io.BytesIO()
    workbook.save(excel_buffer)
    excel_buffer.seek(0)
    return excel_buffer.getvalue()


def _generate_general_proveedor_list_excel_content(proveedores_queryset):
    """
    Generates an Excel file with the general list of providers.
    """
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Listado de Proveedores"

    headers = [
        "Nombre de la Empresa Proveedora", "Empresa Cliente", "Tipo de Servicio", "Nombre de Contacto",
        "Número de Contacto", "Correo Electrónico", "Página Web",
        "Alcance", "Servicio Prestado"
    ]
    sheet.append(headers)

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")
    header_border = Border(left=Side(style='thin'),
                           right=Side(style='thin'),
                           top=Side(style='thin'),
                           bottom=Side(style='thin'))

    for col_num, header_text in enumerate(headers, 1):
        cell = sheet.cell(row=1, column=col_num, value=header_text)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = header_border
        sheet.column_dimensions[cell.column_letter].width = 25

    for proveedor in proveedores_queryset:
        row_data = [
            proveedor.nombre_empresa,
            proveedor.empresa.nombre if proveedor.empresa else "N/A",
            proveedor.get_tipo_servicio_display(),
            proveedor.nombre_contacto,
            proveedor.numero_contacto,
            proveedor.correo_electronico,
            proveedor.pagina_web,
            proveedor.alcance,
            proveedor.servicio_prestado,
        ]
        sheet.append(row_data)

    for col in sheet.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2)
        sheet.column_dimensions[column].width = adjusted_width

    excel_buffer = io.BytesIO()
    workbook.save(excel_buffer)
    excel_buffer.seek(0)
    return excel_buffer.getvalue()


# --- Vistas de Informes ---

@login_required
def informes(request):
    """
    Displays the reports and activities page.
    """
    user = request.user
    today = date.today()
    
    selected_company_id = request.GET.get('empresa_id')
    empresas_disponibles = Empresa.objects.all().order_by('nombre')
    
    equipos_queryset = Equipo.objects.all().select_related('empresa')

    if not user.is_superuser:
        if user.empresa:
            equipos_queryset = equipos_queryset.filter(empresa=user.empresa)
            selected_company_id = str(user.empresa.id)
        else:
            equipos_queryset = Equipo.objects.none()
            empresas_disponibles = Empresa.objects.none()

    if selected_company_id:
        equipos_queryset = equipos_queryset.filter(empresa_id=selected_company_id)

    # --- Actividades a Realizar (Listados Detallados) ---
    # Filtrar solo equipos activos y no de baja
    equipos_activos_para_actividades = equipos_queryset.exclude(estado='De Baja')

    scheduled_activities = []

    for equipo in equipos_activos_para_actividades.filter(proxima_calibracion__isnull=False).order_by('proxima_calibracion'):
        if equipo.proxima_calibracion:
            days_remaining = (equipo.proxima_calibracion - today).days
            estado_vencimiento = 'Vencida' if days_remaining < 0 else 'Próxima'
            scheduled_activities.append({
                'tipo': 'Calibración',
                'equipo': equipo,
                'fecha_programada': equipo.proxima_calibracion,
                'dias_restantes': days_remaining,
                'estado_vencimiento': estado_vencimiento
            })

    for equipo in equipos_activos_para_actividades.filter(proximo_mantenimiento__isnull=False).order_by('proximo_mantenimiento'):
        if equipo.proximo_mantenimiento:
            days_remaining = (equipo.proximo_mantenimiento - today).days
            estado_vencimiento = 'Vencida' if days_remaining < 0 else 'Próxima'
            scheduled_activities.append({
                'tipo': 'Mantenimiento',
                'equipo': equipo,
                'fecha_programada': equipo.proximo_mantenimiento,
                'dias_restantes': days_remaining,
                'estado_vencimiento': estado_vencimiento
            })

    for equipo in equipos_activos_para_actividades.filter(proxima_comprobacion__isnull=False).order_by('proxima_comprobacion'):
        if equipo.proxima_comprobacion:
            days_remaining = (equipo.proxima_comprobacion - today).days
            estado_vencimiento = 'Vencida' if days_remaining < 0 else 'Próxima'
            scheduled_activities.append({
                'tipo': 'Comprobación',
                'equipo': equipo,
                'fecha_programada': equipo.proxima_comprobacion,
                'dias_restantes': days_remaining,
                'estado_vencimiento': estado_vencimiento
            })

    scheduled_activities.sort(key=lambda x: x['fecha_programada'] if x['fecha_programada'] else date.max)

    calibraciones_proximas_30 = [act for act in scheduled_activities if act['tipo'] == 'Calibración' and act['estado_vencimiento'] == 'Próxima' and act['dias_restantes'] <= 30 and act['dias_restantes'] > 15]
    calibraciones_proximas_15 = [act for act in scheduled_activities if act['tipo'] == 'Calibración' and act['estado_vencimiento'] == 'Próxima' and act['dias_restantes'] <= 15 and act['dias_restantes'] >= 0]
    calibraciones_vencidas = [act for act in scheduled_activities if act['tipo'] == 'Calibración' and act['estado_vencimiento'] == 'Vencida']

    mantenimientos_proximos_30 = [act for act in scheduled_activities if act['tipo'] == 'Mantenimiento' and act['estado_vencimiento'] == 'Próxima' and act['dias_restantes'] <= 30 and act['dias_restantes'] > 15]
    mantenimientos_proximos_15 = [act for act in scheduled_activities if act['tipo'] == 'Mantenimiento' and act['estado_vencimiento'] == 'Próxima' and act['dias_restantes'] <= 15 and act['dias_restantes'] >= 0]
    mantenimientos_vencidos = [act for act in scheduled_activities if act['tipo'] == 'Mantenimiento' and act['estado_vencimiento'] == 'Vencida']

    comprobaciones_proximos_30 = [act for act in scheduled_activities if act['tipo'] == 'Comprobación' and act['estado_vencimiento'] == 'Próxima' and act['dias_restantes'] <= 30 and act['dias_restantes'] > 15]
    comprobaciones_proximos_15 = [act for act in scheduled_activities if act['tipo'] == 'Comprobación' and act['estado_vencimiento'] == 'Próxima' and act['dias_restantes'] <= 15 and act['dias_restantes'] >= 0]
    comprobaciones_vencidas = [act for act in scheduled_activities if act['tipo'] == 'Comprobación' and act['estado_vencimiento'] == 'Vencida']


    context = {
        'titulo_pagina': 'Informes y Actividades',
        'is_superuser': user.is_superuser,
        'empresas_disponibles': empresas_disponibles,
        'selected_company_id': selected_company_id,
        'today': today,

        'calibraciones_proximas_30': calibraciones_proximas_30,
        'calibraciones_proximas_15': calibraciones_proximas_15,
        'calibraciones_vencidas': calibraciones_vencidas,

        'mantenimientos_proximos_30': mantenimientos_proximos_30,
        'mantenimientos_proximos_15': mantenimientos_proximos_15,
        'mantenimientos_vencidos': mantenimientos_vencidos,

        'comprobaciones_proximos_30': comprobaciones_proximos_30,
        'comprobaciones_proximos_15': comprobaciones_proximos_15,
        'comprobaciones_vencidas': comprobaciones_vencidas,
    }
    return render(request, 'core/informes.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.has_perm('core.can_export_reports'), login_url='/core/access_denied/')
def generar_informe_zip(request):
    """
    Generates a ZIP file containing equipment reports and associated documents.
    The ZIP structure includes:
    [Company Name]/
    ├── Equipos/
    │   ├── [Equipment Internal Code 1]/
    │   │   ├── Calibraciones/
    │   │   │   ├── Certificados/ (Certificado de Calibración)
    │   │   │   ├── Confirmaciones/ (Confirmación Metrológica)
    │   │   │   └── Intervalos/ (Intervalos de Calibración - NUEVA CARPETA)
    │   │   ├── Comprobaciones/
    │   │   │   └── (Verification PDFs)
    │   │   ├── Mantenimientos/
    │   │   │   └── (Maintenance PDFs)
    │   │   ├── Hoja_de_vida_PDF.pdf
    │   │   ├── Hoja_de_vida_General_Excel.xlsx (NEW: General Info)
    │   │   └── Hoja_de_vida_Actividades_Excel.xlsx (Existing: Activities History)
    │   └── [Equipment Internal Code 2]/
    │       └── ...
    ├── Listado_de_equipos.xlsx
    └── Listado_de_proveedores.xlsx
    """
    selected_company_id = request.GET.get('empresa_id')
    
    if not selected_company_id:
        messages.error(request, "Por favor, selecciona una empresa para generar el informe ZIP.")
        return redirect('core:informes')

    empresa = get_object_or_404(Empresa, pk=selected_company_id)
    equipos_empresa = Equipo.objects.filter(empresa=empresa).order_by('codigo_interno')
    proveedores_empresa = Proveedor.objects.filter(empresa=empresa).order_by('nombre_empresa')

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 1. Add Listado_de_equipos.xlsx (General equipment report for that company)
        excel_buffer_general_equipos = _generate_general_equipment_list_excel_content(equipos_empresa)
        zf.writestr(f"{empresa.nombre}/Listado_de_equipos.xlsx", excel_buffer_general_equipos)

        # 2. Add Listado_de_proveedores.xlsx
        excel_buffer_general_proveedores = _generate_general_proveedor_list_excel_content(proveedores_empresa)
        zf.writestr(f"{empresa.nombre}/Listado_de_Proveedores.xlsx", excel_buffer_general_proveedores)

        # 3. For each equipment, add its "Hoja de Vida" (PDF and Excel) and existing activity PDFs
        for equipo in equipos_empresa:
            safe_equipo_codigo = equipo.codigo_interno.replace('/', '_').replace('\\', '_')
            equipo_folder = f"{empresa.nombre}/Equipos/{safe_equipo_codigo}"

            try:
                hoja_vida_pdf_content = _generate_equipment_hoja_vida_pdf_content(request, equipo)
                zf.writestr(f"{equipo_folder}/Hoja_de_vida.pdf", hoja_vida_pdf_content)
            except Exception as e:
                print(f"Error generating Hoja de Vida PDF for {equipo.codigo_interno}: {e}")
                zf.writestr(f"{equipo_folder}/Hoja_de_vida_PDF_ERROR.txt", f"Error generating Hoja de Vida PDF: {e}")

            try:
                hoja_vida_general_excel_content = _generate_equipment_general_info_excel_content(equipo)
                zf.writestr(f"{equipo_folder}/Hoja_de_vida_General_Excel.xlsx", hoja_vida_general_excel_content)
            except Exception as e:
                print(f"Error generating Hoja de Vida General Excel for {equipo.codigo_interno}: {e}")
                zf.writestr(f"{equipo_folder}/Hoja_de_vida_General_EXCEL_ERROR.txt", f"Error generating Hoja de Vida General Excel: {e}")

            try:
                hoja_vida_activities_excel_content = _generate_equipment_activities_excel_content(equipo)
                zf.writestr(f"{equipo_folder}/Hoja_de_vida_Actividades_Excel.xlsx", hoja_vida_activities_excel_content)
            except Exception as e:
                print(f"Error generating Hoja de Vida Activities Excel for {equipo.codigo_interno}: {e}")
                zf.writestr(f"{equipo_folder}/Hoja_de_vida_Actividades_EXCEL_ERROR.txt", f"Error generating Hoja de Vida Activities Excel: {e}")


            # --- IMPORTANT NOTE FOR RENDER DEPLOYMENT ---
            # The following section attempts to read files from the local filesystem using .path.
            # On Render, files uploaded via Django's FileField are typically stored in a cloud storage
            # service (like AWS S3, Google Cloud Storage, etc.) and not directly on the local filesystem
            # of the ephemeral Render instance.
            #
            # To make this work, you MUST configure Django to use a cloud storage backend (e.g., django-storages
            # with S3). If you have django-storages configured, you would access the file content
            # using `file_field.open()` or `file_field.read()` which handles fetching from cloud storage.
            #
            # Example for cloud storage:
            # from django.core.files.storage import default_storage
            # if default_storage.exists(cal.documento_calibracion.name):
            #     with default_storage.open(cal.documento_calibracion.name, 'rb') as f:
            #         zf.writestr(..., f.read())
            #
            # The current `os.path.exists` and `open(..., 'rb')` will only work if files are
            # stored locally on the Render instance, which is generally not the case for user-uploaded
            # media files in a production PaaS environment.
            #
            # If you haven't set up cloud storage, this part will likely fail silently or with errors
            # in Render's logs because `os.path.exists` will return False or the path will be invalid.

            # Add existing Calibration PDFs (Certificado, Confirmación, Intervalos)
            calibraciones = Calibracion.objects.filter(equipo=equipo)
            from django.core.files.storage import default_storage # Asegurarse de que esté importado

            for cal in calibraciones:
                # Certificado de Calibración
                if cal.documento_calibracion:
                    try:
                        # Usar default_storage para leer desde S3
                        if default_storage.exists(cal.documento_calibracion.name):
                            with default_storage.open(cal.documento_calibracion.name, 'rb') as f:
                                zf.writestr(f"{equipo_folder}/Calibraciones/Certificados/{os.path.basename(cal.documento_calibracion.name)}", f.read())
                        else:
                            print(f"DEBUG: Archivo no encontrado en S3 (certificado): {cal.documento_calibracion.name}")
                    except Exception as e:
                        print(f"Error adding calibration certificate {cal.documento_calibracion.name} to zip: {e}")

                # Confirmación Metrológica
                if cal.confirmacion_metrologica_pdf:
                    try:
                        if default_storage.exists(cal.confirmacion_metrologica_pdf.name):
                            with default_storage.open(cal.confirmacion_metrologica_pdf.name, 'rb') as f:
                                zf.writestr(f"{equipo_folder}/Calibraciones/Confirmaciones/{os.path.basename(cal.confirmacion_metrologica_pdf.name)}", f.read())
                        else:
                            print(f"DEBUG: Archivo no encontrado en S3 (confirmación): {cal.confirmacion_metrologica_pdf.name}")
                    except Exception as e:
                        print(f"Error adding confirmation document {cal.confirmacion_metrologica_pdf.name} to zip: {e}")

                # Intervalos de Calibración (NUEVO)
                if cal.intervalos_calibracion_pdf:
                    try:
                        if default_storage.exists(cal.intervalos_calibracion_pdf.name):
                            with default_storage.open(cal.intervalos_calibracion_pdf.name, 'rb') as f:
                                zf.writestr(f"{equipo_folder}/Calibraciones/Intervalos/{os.path.basename(cal.intervalos_calibracion_pdf.name)}", f.read())
                        else:
                            print(f"DEBUG: Archivo no encontrado en S3 (intervalos): {cal.intervalos_calibracion_pdf.name}")
                    except Exception as e:
                        print(f"Error adding intervals document {cal.intervalos_calibracion_pdf.name} to zip: {e}")

            # Add existing Maintenance PDFs
            mantenimientos = Mantenimiento.objects.filter(equipo=equipo)
            for mant in mantenimientos:
                if mant.documento_mantenimiento:
                    try:
                        if default_storage.exists(mant.documento_mantenimiento.name):
                            with default_storage.open(mant.documento_mantenimiento.name, 'rb') as f:
                                zf.writestr(f"{equipo_folder}/Mantenimientos/{os.path.basename(mant.documento_mantenimiento.name)}", f.read())
                        else:
                            print(f"DEBUG: Archivo no encontrado en S3 (mantenimiento): {mant.documento_mantenimiento.name}")
                    except Exception as e:
                        print(f"Error adding maintenance document {mant.documento_mantenimiento.name} to zip: {e}")

            # Add existing Verification PDFs
            comprobaciones = Comprobacion.objects.filter(equipo=equipo)
            for comp in comprobaciones:
                if comp.documento_comprobacion:
                    try:
                        if default_storage.exists(comp.documento_comprobacion.name):
                            with default_storage.open(comp.documento_comprobacion.name, 'rb') as f:
                                zf.writestr(f"{equipo_folder}/Comprobaciones/{os.path.basename(comp.documento_comprobacion.name)}", f.read())
                        else:
                            print(f"DEBUG: Archivo no encontrado en S3 (comprobación): {comp.documento_comprobacion.name}")
                    except Exception as e:
                        print(f"Error adding comprobacion document {comp.documento_comprobacion.name} to zip: {e}")
            
            # Add other equipment documents (if they exist and are PDF)
            equipment_docs = [
                equipo.archivo_compra_pdf,
                equipo.ficha_tecnica_pdf,
                equipo.manual_pdf,
                equipo.otros_documentos_pdf
            ]
            for doc_field in equipment_docs:
                if doc_field:
                    try:
                        if default_storage.exists(doc_field.name) and doc_field.name.lower().endswith('.pdf'):
                            with default_storage.open(doc_field.name, 'rb') as f:
                                zf.writestr(f"{equipo_folder}/{os.path.basename(doc_field.name)}", f.read())
                        else:
                             print(f"DEBUG: Archivo no encontrado en S3 (doc. equipo): {doc_field.name}")
                    except Exception as e:
                        print(f"Error adding equipment document {doc_field.name} to zip: {e}")


    zip_buffer.seek(0)
    response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="Informes_{empresa.nombre}.zip"'
    return response


@login_required
def informe_vencimientos_pdf(request):
    """
    Generates a PDF report of upcoming and overdue activities.
    """
    today = timezone.localdate()
    upcoming_threshold = today + timedelta(days=30)

    scheduled_activities = []

    equipos_base_query = Equipo.objects.all()
    if not request.user.is_superuser and request.user.empresa:
        equipos_base_query = equipos_base_query.filter(empresa=request.user.empresa)
    elif not request.user.is_superuser and not request.user.empresa:
        equipos_base_query = Equipo.objects.none()

    equipos_base_query = equipos_base_query.exclude(estado='De Baja')

    calibraciones_query = equipos_base_query.filter(
        proxima_calibracion__isnull=False
    ).order_by('proxima_calibracion')

    for equipo in calibraciones_query:
        if equipo.proxima_calibracion:
            days_remaining = (equipo.proxima_calibracion - today).days
            estado_vencimiento = 'Vencida' if days_remaining < 0 else 'Próxima'
            scheduled_activities.append({
                'tipo': 'Calibración',
                'equipo': equipo,
                'fecha_programada': equipo.proxima_calibracion,
                'dias_restantes': days_remaining,
                'estado_vencimiento': estado_vencimiento
            })

    mantenimientos_query = equipos_base_query.filter(
        proximo_mantenimiento__isnull=False
    ).order_by('proximo_mantenimiento')

    for equipo in mantenimientos_query:
        if equipo.proximo_mantenimiento:
            days_remaining = (equipo.proximo_mantenimiento - today).days
            estado_vencimiento = 'Vencida' if days_remaining < 0 else 'Próxima'
            scheduled_activities.append({
                'tipo': 'Mantenimiento',
                'equipo': equipo,
                'fecha_programada': equipo.proximo_mantenimiento,
                'dias_restantes': days_remaining,
                'estado_vencimiento': estado_vencimiento
            })

    comprobaciones_query = equipos_base_query.filter(
        proxima_comprobacion__isnull=False
    ).order_by('proxima_comprobacion')

    for equipo in comprobaciones_query:
        if equipo.proxima_comprobacion:
            days_remaining = (equipo.proxima_comprobacion - today).days
            estado_vencimiento = 'Vencida' if days_remaining < 0 else 'Próxima'
            scheduled_activities.append({
                'tipo': 'Comprobación',
                'equipo': equipo,
                'fecha_programada': equipo.proxima_comprobacion,
                'dias_restantes': days_remaining,
                'estado_vencimiento': estado_vencimiento
            })

    scheduled_activities.sort(key=lambda x: x['fecha_programada'] if x['fecha_programada'] else date.max)

    context = {
        'scheduled_activities': scheduled_activities,
        'today': today,
        'titulo_pagina': 'Informe de Vencimientos',
    }

    template_path = 'core/informe_vencimientos_pdf.html'
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="informe_vencimientos.pdf"'

    pdf_file = _generate_pdf_content(request, template_path, context)
    response.write(pdf_file)
    return response

@login_required
def programmed_activities_list(request):
    """
    Lists all programmed activities.
    """
    today = timezone.localdate()
    scheduled_activities = []

    equipos_base_query = Equipo.objects.all()
    if not request.user.is_superuser and request.user.empresa:
        equipos_base_query = equipos_base_query.filter(empresa=request.user.empresa)
    elif not request.user.is_superuser and not request.user.empresa:
        equipos_base_query = Equipo.objects.none()

    equipos_base_query = equipos_base_query.exclude(estado='De Baja')

    calibraciones_query = equipos_base_query.filter(
        proxima_calibracion__isnull=False
    ).order_by('proxima_calibracion')

    for equipo in calibraciones_query:
        if equipo.proxima_calibracion:
            days_remaining = (equipo.proxima_calibracion - today).days
            estado_vencimiento = 'Vencida' if days_remaining < 0 else 'Próxima'
            scheduled_activities.append({
                'tipo': 'Calibración',
                'equipo': equipo,
                'fecha_programada': equipo.proxima_calibracion,
                'dias_restantes': days_remaining,
                'estado_vencimiento': estado_vencimiento
            })

    mantenimientos_query = equipos_base_query.filter(
        proximo_mantenimiento__isnull=False
    ).order_by('proximo_mantenimiento')

    for equipo in mantenimientos_query:
        if equipo.proximo_mantenimiento:
            days_remaining = (equipo.proximo_mantenimiento - today).days
            estado_vencimiento = 'Vencida' if days_remaining < 0 else 'Próxima'
            scheduled_activities.append({
                'tipo': 'Mantenimiento',
                'equipo': equipo,
                'fecha_programada': equipo.proximo_mantenimiento,
                'dias_restantes': days_remaining,
                'estado_vencimiento': estado_vencimiento
            })

    comprobaciones_query = equipos_base_query.filter(
        proxima_comprobacion__isnull=False
    ).order_by('proxima_comprobacion')

    for equipo in comprobaciones_query:
        if equipo.proxima_comprobacion:
            days_remaining = (equipo.proxima_comprobacion - today).days
            estado_vencimiento = 'Vencida' if days_remaining < 0 else 'Próxima'
            scheduled_activities.append({
                'tipo': 'Comprobación',
                'equipo': equipo,
                'fecha_programada': equipo.proxima_comprobacion,
                'dias_restantes': days_remaining,
                'estado_vencimiento': estado_vencimiento
            })

    scheduled_activities.sort(key=lambda x: x['fecha_programada'] if x['fecha_programada'] else date.max)

    paginator = Paginator(scheduled_activities, 10)
    page_number = request.GET.get('page')
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    return render(request, 'core/programmed_activities_list.html', {'page_obj': page_obj, 'titulo_pagina': 'Actividades Programadas'})


@login_required
@permission_required('core.can_export_reports', raise_exception=True)
def exportar_equipos_excel(request):
    """
    Exports a general list of equipment to an Excel file.
    """
    equipos = Equipo.objects.all().select_related('empresa')
    if not request.user.is_superuser and request.user.empresa:
        equipos = equipos.filter(empresa=request.user.empresa)
    elif not request.user.is_superuser and not request.user.empresa:
        equipos = Equipo.objects.none()

    excel_content = _generate_general_equipment_list_excel_content(equipos)

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="listado_equipos.xlsx"'
    response.write(excel_content)
    return response

@login_required
def generar_hoja_vida_pdf(request, pk):
    """
    Generates the "Hoja de Vida" (Life Sheet) PDF for a specific equipment.
    """
    equipo = get_object_or_404(Equipo, pk=pk)
    if not request.user.is_superuser and request.user.empresa != equipo.empresa:
        messages.error(request, 'No tienes permiso para generar la hoja de vida de este equipo.')
        return redirect('core:home')

    try:
        pdf_content = _generate_equipment_hoja_vida_pdf_content(request, equipo)
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="hoja_vida_{equipo.codigo_interno}.pdf"'
        return response
    except Exception as e:
        return HttpResponse(f'Tuvimos algunos errores al generar el PDF: <pre>{e}</pre>')


@require_POST
@csrf_exempt
def add_message(request):
    """
    Adds a Django message via an AJAX POST request.
    Expected JSON body: {"message": "Your message here", "tags": "success|info|warning|error"}
    """
    try:
        data = json.loads(request.body)
        message_text = data.get('message', 'Mensaje genérico.')
        message_tags = data.get('tags', 'info')

        if message_tags == 'success':
            messages.success(request, message_text)
        elif message_tags == 'error':
            messages.error(request, message_text)
        elif message_tags == 'warning':
            messages.warning(request, message_text)
        else:
            messages.info(request, message_text)
        
        return JsonResponse({'status': 'success', 'message': 'Mensaje añadido.'})
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON.'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def access_denied(request):
    """
    Renders the access denied page.
    """
    return render(request, 'core/access_denied.html', {'titulo_pagina': 'Acceso Denegado'})