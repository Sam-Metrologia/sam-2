#!/bin/bash

# Script para detener el procesador de cola ZIP
# Uso: ./stop_zip_processor.sh

echo "🛑 Deteniendo procesador de cola ZIP..."

if [ -f logs/zip_processor.pid ]; then
    PID=$(cat logs/zip_processor.pid)

    if kill -0 $PID 2>/dev/null; then
        echo "📋 Deteniendo proceso PID: $PID"
        kill $PID

        # Esperar a que termine
        for i in {1..10}; do
            if ! kill -0 $PID 2>/dev/null; then
                echo "✅ Procesador detenido exitosamente"
                rm logs/zip_processor.pid
                exit 0
            fi
            sleep 1
        done

        # Forzar terminación si no responde
        echo "⚠️  Forzando terminación..."
        kill -9 $PID 2>/dev/null
        rm logs/zip_processor.pid
        echo "✅ Procesador terminado forzosamente"
    else
        echo "⚠️  El proceso ya no está ejecutándose"
        rm logs/zip_processor.pid
    fi
else
    echo "⚠️  No se encontró archivo PID. El procesador puede no estar ejecutándose."
fi