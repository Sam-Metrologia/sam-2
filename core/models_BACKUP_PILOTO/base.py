# core/models/base.py
"""
Imports comunes y funciones auxiliares para todos los modelos de SAM Metrología
"""

from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from datetime import date, timedelta, datetime
from django.utils import timezone
import decimal
import os
from django.utils.translation import gettext_lazy as _
from dateutil.relativedelta import relativedelta
from django.conf import settings
import calendar
import uuid
import json
import logging

# Configurar logger para este módulo
logger = logging.getLogger('core')


# ==============================================================================
# FUNCIONES AUXILIARES
# ==============================================================================

def meses_decimales_a_relativedelta(meses_decimal):
    """
    Convierte meses decimales a un objeto relativedelta con meses y días.

    Permite frecuencias más precisas como 1.5 meses (1 mes + 15 días)
    o 2.25 meses (2 meses + 7 días).

    Ejemplos:
        - 1.5 meses = 1 mes + 15 días
        - 2.25 meses = 2 meses + 7 días
        - 0.5 meses = 15 días
        - 6.0 meses = 6 meses exactos

    Args:
        meses_decimal (Decimal): Número de meses (puede tener decimales)

    Returns:
        relativedelta: Objeto relativedelta con meses y días calculados
    """
    if meses_decimal is None:
        return relativedelta(months=0)

    # Convertir Decimal a float
    meses_float = float(meses_decimal)

    # Separar parte entera (meses) y decimal (fracción de mes)
    meses_enteros = int(meses_float)
    fraccion_mes = meses_float - meses_enteros

    # Convertir fracción de mes a días (promedio de 30.44 días por mes)
    dias_adicionales = round(fraccion_mes * 30.44)

    return relativedelta(months=meses_enteros, days=dias_adicionales)
