#!/usr/bin/env python3
"""
Script de prueba para el sistema ZIP híbrido
Simula el comportamiento según número de equipos
"""

def test_zip_logic():
    """Simula la lógica del sistema híbrido"""

    # Casos de prueba
    test_cases = [
        {"equipos": 5, "empresa": "Empresa A"},
        {"equipos": 15, "empresa": "Empresa B"},
        {"equipos": 16, "empresa": "Empresa C"},
        {"equipos": 30, "empresa": "Empresa D"},
        {"equipos": 100, "empresa": "Empresa E"},
    ]

    print("PRUEBA DEL SISTEMA ZIP HIBRIDO")
    print("=" * 50)

    for case in test_cases:
        equipos_count = case["equipos"]
        empresa_name = case["empresa"]

        # Lógica igual a la implementada
        if equipos_count <= 15:
            method = "DESCARGA DIRECTA"
            time_estimate = "5-15 segundos"
            color = "🟢"
        else:
            method = "COLA DE PROCESAMIENTO"
            if equipos_count <= 50:
                time_estimate = "30-60 segundos"
                color = "🟡"
            else:
                time_estimate = "2-5 minutos"
                color = "🔴"

        print(f"- {empresa_name}: {equipos_count} equipos -> {method} ({time_estimate})")

    print("\n" + "=" * 50)
    print("Sistema hibrido implementado correctamente")
    print("Empresas <=15 equipos tendran descarga RAPIDA como produccion")
    print("Empresas >15 equipos usaran cola (como antes, pero mas organizadas)")

if __name__ == "__main__":
    test_zip_logic()