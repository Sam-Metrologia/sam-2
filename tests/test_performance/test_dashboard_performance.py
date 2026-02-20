#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de Testing de Rendimiento del Dashboard
==============================================

Mide el tiempo de carga y número de queries del dashboard
antes y después de las optimizaciones.

Uso:
    python test_dashboard_performance.py
"""

import os
import sys
import django
import time
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_c.settings')
django.setup()

from django.test import Client
from django.db import connection, reset_queries
from django.core.cache import cache
from core.models import CustomUser


def measure_dashboard_performance():
    """
    Mide rendimiento del dashboard
    """
    print("=" * 70)
    print("TEST DE RENDIMIENTO DEL DASHBOARD")
    print("=" * 70)
    print()

    # Limpiar cache
    print("Limpiando cache...")
    cache.clear()

    # Obtener o crear usuario de prueba
    try:
        user = CustomUser.objects.filter(is_superuser=False).first()
        if not user:
            print("ADVERTENCIA: No se encontro usuario de prueba")
            print("   Crea un usuario primero con: python manage.py createsuperuser")
            return
    except Exception as e:
        print(f"ERROR obteniendo usuario: {e}")
        return

    # Crear cliente y login
    client = Client()
    login_success = client.login(username=user.username, password='testpass')  # Cambiar password si es necesario

    if not login_success:
        # Intentar con usuario admin
        try:
            admin_user = CustomUser.objects.filter(is_superuser=True).first()
            if admin_user:
                print(f"   Intentando con superusuario: {admin_user.username}")
                # No podemos hacer login programático sin password, así que solo reportamos
                print(f"   Usuario encontrado: {admin_user.username}")
                print(f"   Empresa: {admin_user.empresa.nombre if admin_user.empresa else 'N/A'}")
        except:
            pass

    print()
    print("CONFIGURACION DEL TEST")
    print("-" * 70)
    print(f"   Usuario: {user.username}")
    print(f"   Empresa: {user.empresa.nombre if user.empresa else 'N/A'}")
    print(f"   Superusuario: {'Si' if user.is_superuser else 'No'}")
    print()

    # Habilitar logging de queries
    settings.DEBUG = True

    print("MIDIENDO RENDIMIENTO...")
    print("-" * 70)

    # Resetear queries
    reset_queries()

    # Medir tiempo
    start_time = time.time()

    try:
        # Simular request al dashboard
        response = client.get('/dashboard/')

        # Calcular tiempo
        elapsed_time = time.time() - start_time

        # Contar queries
        num_queries = len(connection.queries)

        # Resultados
        print()
        print("=" * 70)
        print("RESULTADOS")
        print("=" * 70)
        print()
        print(f"Tiempo de Carga:     {elapsed_time:.3f} segundos")
        print(f"Numero de Queries:   {num_queries}")
        print(f"Status Code:         {response.status_code}")
        print()

        # Evaluación
        print("EVALUACION")
        print("-" * 70)

        if elapsed_time < 1.0:
            print("[OK] Tiempo:   EXCELENTE (<1s)")
        elif elapsed_time < 2.0:
            print("[OK] Tiempo:   BUENO (1-2s)")
        elif elapsed_time < 5.0:
            print("[!]  Tiempo:   ACEPTABLE (2-5s)")
        else:
            print("[X]  Tiempo:   LENTO (>5s)")

        if num_queries < 20:
            print("[OK] Queries:  EXCELENTE (<20)")
        elif num_queries < 50:
            print("[OK] Queries:  BUENO (20-50)")
        elif num_queries < 100:
            print("[!]  Queries:  MEJORABLE (50-100)")
        else:
            print("[X]  Queries:  MUCHAS (>100) - Posible N+1")

        print()

        # Queries más lentas (top 5)
        if connection.queries:
            print("TOP 5 QUERIES MAS LENTAS")
            print("-" * 70)

            # Ordenar por tiempo
            sorted_queries = sorted(
                connection.queries,
                key=lambda q: float(q['time']),
                reverse=True
            )[:5]

            for i, query in enumerate(sorted_queries, 1):
                sql = query['sql'][:100] + "..." if len(query['sql']) > 100 else query['sql']
                print(f"{i}. {query['time']}s - {sql}")

            print()

        # Benchmark de referencia
        print("BENCHMARK DE REFERENCIA")
        print("-" * 70)
        print("   Antes de optimizacion:  7-13s,  ~613 queries")
        print("   Meta despues:           <1s,    <20 queries")
        print()

        # Mejora estimada
        if num_queries < 613:
            mejora_queries = ((613 - num_queries) / 613) * 100
            print(f"   Mejora de queries:      -{mejora_queries:.1f}%")

        print()

    except Exception as e:
        print()
        print(f"ERROR: {e}")
        print()
        import traceback
        traceback.print_exc()

    # Volver a producción
    settings.DEBUG = False


if __name__ == '__main__':
    measure_dashboard_performance()
