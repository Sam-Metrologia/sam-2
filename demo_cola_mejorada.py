#!/usr/bin/env python3
"""
DEMO del sistema de cola ZIP mejorado
Muestra los mensajes específicos y tiempos reales
"""

def demo_cola_mejorada():
    """Simula el comportamiento del sistema de cola mejorado"""

    print("=" * 80)
    print("SISTEMA DE COLA ZIP MEJORADO - DEMO")
    print("=" * 80)
    print()

    # Simulación de diferentes scenarios
    scenarios = [
        {
            "empresa": "Certificapital SAS",
            "equipos": 8,
            "status": "pending",
            "position": 1,
            "parte": 1
        },
        {
            "empresa": "MetroTech Ltda",
            "equipos": 25,
            "status": "processing",
            "position": 0,
            "parte": 1
        },
        {
            "empresa": "InstruLab SA",
            "equipos": 80,
            "status": "pending",
            "position": 3,
            "parte": 2
        },
        {
            "empresa": "CalibrarPro",
            "equipos": 12,
            "status": "completed",
            "position": 0,
            "parte": 1
        }
    ]

    for i, scenario in enumerate(scenarios, 1):
        print(f"CASO {i}: {scenario['empresa']}")
        print(f"Equipos: {scenario['equipos']}")
        print(f"Estado: {scenario['status']}")

        # Simular mensajes específicos como los nuevos métodos
        if scenario['status'] == 'pending':
            if scenario['equipos'] <= 15:
                # Fast track para empresas pequeñas
                time_est = "2 minutos"
                message = f"[RAPIDA] Generacion rapida para {scenario['empresa']} ({scenario['equipos']} equipos). Procesando en ~2 min"
            else:
                # Cola estándar
                if scenario['equipos'] <= 50:
                    time_est = f"{scenario['position'] * 4} minutos"
                else:
                    time_est = f"{scenario['position'] * 8} minutos"

                if scenario['position'] == 1:
                    message = f"[SIGUIENTE] Eres el siguiente! ZIP de {scenario['empresa']} ({scenario['equipos']} equipos). Iniciara en ~2 min"
                else:
                    message = f"[COLA] En cola posicion #{scenario['position']}: ZIP de {scenario['empresa']} ({scenario['equipos']} equipos). Tiempo estimado: ~{time_est}"

        elif scenario['status'] == 'processing':
            if scenario['equipos'] <= 15:
                time_est = "1 minuto"
                message = f"[GENERANDO] Generando ZIP de {scenario['empresa']} ({scenario['equipos']} equipos). Tiempo restante: ~{time_est}"
            elif scenario['equipos'] <= 50:
                time_est = "3 minutos"
                message = f"[PROCESANDO] Procesando ZIP de {scenario['empresa']} ({scenario['equipos']} equipos). Tiempo restante: ~{time_est}"
            else:
                time_est = "6 minutos"
                message = f"[PROCESANDO] Procesando ZIP de {scenario['empresa']} ({scenario['equipos']} equipos). Tiempo restante: ~{time_est}"

        elif scenario['status'] == 'completed':
            message = f"[LISTO] ZIP de {scenario['empresa']} completado ({scenario['equipos']} equipos). Listo para descargar!"
            time_est = "Ya esta listo!"

        print(f"Mensaje: {message}")
        print(f"Tiempo: {time_est}")
        print(f"Parte: {scenario['parte']}")
        print("-" * 60)
        print()

    print("=" * 80)
    print("MEJORAS IMPLEMENTADAS:")
    print("- Mensajes especificos con nombres de empresa")
    print("- Tiempos reales basados en numero de equipos")
    print("- Diferenciacion por tamanio de empresa")
    print("- Posicion exacta en cola")
    print("- Fast track para empresas <=15 equipos")
    print("- Cola acelerada (5 segundos vs 30 segundos)")
    print("=" * 80)

if __name__ == "__main__":
    demo_cola_mejorada()