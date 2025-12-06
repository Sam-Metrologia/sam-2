# -*- coding: utf-8 -*-
"""
Script de Análisis de Limpieza de Código
Analiza código DEBUG, código muerto, imports incorrectos
"""
import os
import re
from pathlib import Path

# Configuración
BASE_DIR = Path(r"C:\Users\LENOVO\OneDrive\Escritorio\sam-2")
CORE_DIR = BASE_DIR / "core"

# Patrones a buscar
PATTERNS = {
    'debug_print': r'print\s*\([^)]*DEBUG',
    'debug_logger': r'logger\.debug\s*\(',
    'debug_setting': r'if\s+settings\.DEBUG',
    'import_in_function': r'^    import\s+',  # Import con indentación
    'dead_code_after_return': r'    return.*\n.*\n.*(?!def|class)',  # Código después de return
}

def analizar_archivo(filepath):
    """Analiza un archivo Python en busca de problemas"""
    resultados = {}

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            contenido = f.read()
            lineas = contenido.split('\n')

        # Buscar patrones
        for patron_nombre, patron_regex in PATTERNS.items():
            matches = []
            for num_linea, linea in enumerate(lineas, 1):
                if re.search(patron_regex, linea):
                    matches.append({
                        'linea': num_linea,
                        'contenido': linea.strip()
                    })

            if matches:
                resultados[patron_nombre] = matches

    except Exception as e:
        return {'error': str(e)}

    return resultados

def main():
    print("="*60)
    print("ANÁLISIS DE LIMPIEZA DE CÓDIGO - SAM METROLOGÍA")
    print("="*60)
    print()

    # 1. DASHBOARD GERENCIAL vs PANEL DE DECISIONES
    print("1. DASHBOARD GERENCIAL vs PANEL DE DECISIONES")
    print("-"*60)

    archivos_dashboard = list((CORE_DIR / "views").glob("dashboard_gerencia*.py"))
    print(f"\n📁 Archivos encontrados: {len(archivos_dashboard)}")
    for archivo in archivos_dashboard:
        print(f"   - {archivo.name}")

    # Verificar cuál se usa
    init_file = CORE_DIR / "views" / "__init__.py"
    with open(init_file, 'r') as f:
        init_content = f.read()

    if "dashboard_gerencia_simple" in init_content:
        print("\n✅ SE USA: dashboard_gerencia_simple.py")
        print("❌ NO SE USA: dashboard_gerencia.py")
        print("\n💡 RECOMENDACIÓN: Eliminar dashboard_gerencia.py (no se usa)")

    # Verificar template
    panel_template = CORE_DIR / "templates" / "core" / "panel_decisiones.html"
    if panel_template.exists():
        print(f"\n📄 Template: panel_decisiones.html (EXISTE)")

    # Verificar en base.html
    base_template = BASE_DIR / "templates" / "base.html"
    with open(base_template, 'r') as f:
        base_content = f.read()

    if "panel_decisiones" in base_content:
        print("✅ Sidebar usa: 'Panel de Decisiones' (panel_decisiones)")
    if "dashboard_gerencia" in base_content:
        print("⚠️ Sidebar también tiene: 'dashboard_gerencia' (verificar)")

    print("\n" + "="*60)
    print("\n2. CÓDIGO DEBUG")
    print("-"*60)

    # Analizar models.py específicamente
    models_file = CORE_DIR / "models.py"
    print(f"\n📄 Analizando: {models_file.name}")

    with open(models_file, 'r', encoding='utf-8') as f:
        lineas_models = f.readlines()

    # Buscar DEBUG específicos
    debug_encontrados = []
    for num_linea, linea in enumerate(lineas_models, 1):
        if 'DEBUG' in linea and ('print' in linea or 'logger' in linea):
            debug_encontrados.append((num_linea, linea.strip()))

    if debug_encontrados:
        print(f"\n⚠️ ENCONTRADOS {len(debug_encontrados)} casos de DEBUG:")
        for num, contenido in debug_encontrados[:5]:  # Mostrar primeros 5
            print(f"   Línea {num}: {contenido[:80]}")
    else:
        print("\n✅ No se encontraron prints DEBUG")

    print("\n" + "="*60)
    print("\n3. IMPORTS DENTRO DE FUNCIONES")
    print("-"*60)

    archivos_con_imports = []
    for archivo_py in CORE_DIR.rglob("*.py"):
        if "__pycache__" in str(archivo_py) or "migrations" in str(archivo_py):
            continue

        with open(archivo_py, 'r', encoding='utf-8') as f:
            contenido = f.read()
            lineas = contenido.split('\n')

        # Buscar imports con indentación (dentro de funciones)
        imports_funcion = []
        for num_linea, linea in enumerate(lineas, 1):
            # Import con espacios al inicio (indentado)
            if re.match(r'^    +import\s+', linea) or re.match(r'^    +from\s+', linea):
                imports_funcion.append((num_linea, linea.strip()))

        if imports_funcion:
            archivos_con_imports.append((archivo_py.name, imports_funcion))

    if archivos_con_imports:
        print(f"\n⚠️ ENCONTRADOS {len(archivos_con_imports)} archivos con imports en funciones:")
        for nombre_archivo, imports in archivos_con_imports[:5]:
            print(f"\n   📄 {nombre_archivo} ({len(imports)} imports)")
            for num, contenido in imports[:2]:
                print(f"      Línea {num}: {contenido[:60]}")
    else:
        print("\n✅ No se encontraron imports dentro de funciones")

    print("\n" + "="*60)
    print("\n4. CÓDIGO MUERTO (Unreachable Code)")
    print("-"*60)

    # Buscar específicamente el método esta_al_dia_con_pagos
    with open(models_file, 'r', encoding='utf-8') as f:
        contenido_models = f.read()

    # Buscar el método
    patron_metodo = r'def esta_al_dia_con_pagos\(self\):.*?(?=\n    def |\nclass |\Z)'
    match = re.search(patron_metodo, contenido_models, re.DOTALL)

    if match:
        metodo_completo = match.group(0)
        lineas_metodo = metodo_completo.split('\n')

        # Buscar return seguido de código
        encontro_return = False
        lineas_muertas = []

        for i, linea in enumerate(lineas_metodo):
            if 'return ' in linea and not linea.strip().startswith('#'):
                encontro_return = True
            elif encontro_return and linea.strip() and not linea.strip().startswith('#') and not linea.strip().startswith('def '):
                lineas_muertas.append(linea.strip())

        if lineas_muertas:
            print(f"\n⚠️ ENCONTRADO código muerto en esta_al_dia_con_pagos():")
            for linea in lineas_muertas[:5]:
                print(f"   {linea[:80]}")
        else:
            print("\n✅ No se encontró código muerto obvio")

    print("\n" + "="*60)
    print("\nFIN DEL ANÁLISIS")
    print("="*60)

if __name__ == "__main__":
    main()
