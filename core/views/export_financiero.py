# core/views/export_financiero.py
# Funciones de exportación para análisis financiero

import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from datetime import date
from io import BytesIO

from ..utils.analisis_financiero import (
    calcular_analisis_financiero_empresa,
    calcular_proyeccion_costos_empresa,
    calcular_metricas_financieras_sam
)
from ..models import Empresa


@login_required
def exportar_analisis_financiero_excel(request):
    """
    Exporta el análisis financiero completo a Excel
    - Vista EMPRESA: Análisis de costos y proyección
    - Vista SAM: Métricas del negocio multi-empresa
    """
    user = request.user
    today = date.today()
    current_year = today.year

    # Crear workbook
    wb = openpyxl.Workbook()

    # Estilos
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
    subheader_font = Font(bold=True, color="1F2937")
    subheader_fill = PatternFill(start_color="E5E7EB", end_color="E5E7EB", fill_type="solid")
    currency_format = '_($* #,##0_);_($* (#,##0);_($* "-"_);_(@_)'
    percentage_format = '0.0%'
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    if user.is_superuser:
        # VISTA SAM: Exportar métricas del negocio
        ws = wb.active
        ws.title = "Análisis Financiero SAM"

        # Filtrado por empresa
        selected_company_id = request.GET.get('empresa_id')
        empresas_disponibles = Empresa.objects.filter(is_deleted=False).order_by('nombre')

        if selected_company_id:
            empresas_queryset = empresas_disponibles.filter(id=selected_company_id)
        else:
            empresas_queryset = empresas_disponibles

        # Calcular métricas SAM
        metricas_sam = calcular_metricas_financieras_sam(empresas_queryset, current_year, current_year - 1)

        # Header principal
        ws.merge_cells('A1:F1')
        ws['A1'] = f"📈 Análisis Financiero del Negocio SAM - {current_year}"
        ws['A1'].font = Font(bold=True, size=16, color="1F2937")
        ws['A1'].alignment = Alignment(horizontal='center')

        ws.merge_cells('A2:F2')
        ws['A2'] = f"Generado: {today.strftime('%d/%m/%Y')} | Empresas analizadas: {empresas_queryset.count()}"
        ws['A2'].alignment = Alignment(horizontal='center')

        # Métricas principales
        row = 4
        headers = ['Métrica', 'Valor Actual', 'Comparativo', 'Crecimiento', 'Estado', 'Observaciones']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=row, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = border
            cell.alignment = Alignment(horizontal='center')

        # Datos de métricas
        metricas_data = [
            ['Ingreso Total YTD', metricas_sam['ingreso_ytd_actual'], metricas_sam['ingreso_año_anterior'],
             f"{metricas_sam['crecimiento_ingresos_porcentaje']}%",
             'Positivo' if metricas_sam['crecimiento_ingresos_porcentaje'] >= 0 else 'Negativo',
             f"Acumulado año {current_year}"],
            ['Empresas Activas', metricas_sam['empresas_activas_actual'], metricas_sam['empresas_activas_anterior'],
             f"{metricas_sam['crecimiento_empresas_porcentaje']}%",
             'Expansión' if metricas_sam['crecimiento_empresas_porcentaje'] >= 0 else 'Contracción',
             'Base de clientes'],
            ['Proyección Fin Año', metricas_sam['proyeccion_fin_año'], metricas_sam['ingreso_ytd_actual'],
             f"{((metricas_sam['proyeccion_fin_año'] - metricas_sam['ingreso_ytd_actual']) / max(metricas_sam['ingreso_ytd_actual'], 1)) * 100:.1f}%",
             'Estimado', 'Proyección lineal'],
        ]

        for row_data in metricas_data:
            row += 1
            for col, value in enumerate(row_data, 1):
                cell = ws.cell(row=row, column=col, value=value)
                cell.border = border
                if col in [2, 3]:  # Valores monetarios
                    cell.number_format = currency_format
                elif col == 4 and '%' in str(value):  # Porcentajes
                    cell.number_format = percentage_format

        filename = f"analisis_financiero_sam_{current_year}_{today.strftime('%Y%m%d')}.xlsx"

    elif getattr(user, 'rol_usuario', None) == 'GERENCIA' and user.empresa:
        # VISTA EMPRESA: Exportar análisis de costos
        empresa = user.empresa
        ws = wb.active
        ws.title = f"Análisis {empresa.nombre}"

        # Calcular análisis financiero
        analisis_financiero = calcular_analisis_financiero_empresa(empresa, current_year, today)
        proyeccion_costos = calcular_proyeccion_costos_empresa(empresa, current_year + 1)

        # Header principal
        ws.merge_cells('A1:F1')
        ws['A1'] = f"💰 Análisis Financiero Metrológico - {empresa.nombre}"
        ws['A1'].font = Font(bold=True, size=16, color="1F2937")
        ws['A1'].alignment = Alignment(horizontal='center')

        ws.merge_cells('A2:F2')
        ws['A2'] = f"Período: {current_year} | Generado: {today.strftime('%d/%m/%Y')}"
        ws['A2'].alignment = Alignment(horizontal='center')

        # Sección 1: Gasto YTD
        row = 4
        ws.merge_cells(f'A{row}:F{row}')
        ws[f'A{row}'] = "📊 TRAZABILIDAD DE COSTOS YTD"
        ws[f'A{row}'].font = subheader_font
        ws[f'A{row}'].fill = subheader_fill
        ws[f'A{row}'].alignment = Alignment(horizontal='center')

        row += 2
        headers = ['Tipo de Actividad', 'Costo YTD', 'Porcentaje', 'Descripción']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=row, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = border

        # Datos de costos YTD
        costos_data = [
            ['Calibraciones', analisis_financiero['costos_calibracion_ytd'],
             f"{analisis_financiero['porcentaje_calibracion']}%", 'Usualmente externo'],
            ['Mantenimientos', analisis_financiero['costos_mantenimiento_ytd'],
             f"{analisis_financiero['porcentaje_mantenimiento']}%", 'Usualmente interno'],
            ['Comprobaciones', analisis_financiero['costos_comprobacion_ytd'],
             f"{analisis_financiero['porcentaje_comprobacion']}%", 'Usualmente interno'],
            ['TOTAL', analisis_financiero['gasto_ytd_total'], '100%', 'Gasto real incurrido'],
        ]

        for row_data in costos_data:
            row += 1
            for col, value in enumerate(row_data, 1):
                cell = ws.cell(row=row, column=col, value=value)
                cell.border = border
                if col == 2:  # Valores monetarios
                    cell.number_format = currency_format
                if row_data[0] == 'TOTAL':  # Fila total en negrita
                    cell.font = Font(bold=True)

        # Sección 2: Proyección
        row += 3
        ws.merge_cells(f'A{row}:F{row}')
        ws[f'A{row}'] = f"🔮 PROYECCIÓN DE COSTOS {current_year + 1}"
        ws[f'A{row}'].font = subheader_font
        ws[f'A{row}'].fill = subheader_fill
        ws[f'A{row}'].alignment = Alignment(horizontal='center')

        row += 2
        headers = ['Métrica', 'Valor Proyectado', 'Base Cálculo', 'Observaciones']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=row, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = border

        # Datos de proyección
        variacion = ((proyeccion_costos['proyeccion_gasto_proximo_año'] - analisis_financiero['gasto_ytd_total']) / max(analisis_financiero['gasto_ytd_total'], 1)) * 100

        proyeccion_data = [
            ['Gasto Estimado Total', proyeccion_costos['proyeccion_gasto_proximo_año'],
             f"{proyeccion_costos['actividades_proyectadas_total']} actividades",
             'Basado en homogeneidad equipos'],
            ['Variación vs YTD', f"{variacion:.1f}%",
             f"${analisis_financiero['gasto_ytd_total']:,.0f} actual",
             'Incremento/reducción esperado'],
        ]

        for row_data in proyeccion_data:
            row += 1
            for col, value in enumerate(row_data, 1):
                cell = ws.cell(row=row, column=col, value=value)
                cell.border = border
                if col == 2 and '$' in str(value):  # Valores monetarios
                    cell.number_format = currency_format

        # Nota importante
        row += 3
        ws.merge_cells(f'A{row}:F{row}')
        ws[f'A{row}'] = "⚠️ NOTA: Esta proyección no incluye costos por mantenimientos correctivos no programados"
        ws[f'A{row}'].font = Font(italic=True, color="D97706")
        ws[f'A{row}'].alignment = Alignment(horizontal='center')

        filename = f"analisis_financiero_{empresa.nombre.replace(' ', '_')}_{current_year}_{today.strftime('%Y%m%d')}.xlsx"
    else:
        # Usuario sin permisos
        return HttpResponse("Sin permisos para exportar análisis financiero", status=403)

    # Ajustar ancho de columnas
    for column in ws.columns:
        max_length = 0
        column_letter = get_column_letter(column[0].column)
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column_letter].width = adjusted_width

    # Preparar respuesta HTTP
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response