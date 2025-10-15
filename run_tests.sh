#!/bin/bash
# Script para ejecutar tests localmente en SAM Metrología
# Uso: ./run_tests.sh [opciones]

set -e  # Salir si algún comando falla

echo ""
echo "🧪 SAM Metrología - Sistema de Testing"
echo "======================================="
echo ""

# Función para mostrar uso
show_usage() {
    echo "Uso: ./run_tests.sh [opciones]"
    echo ""
    echo "Opciones:"
    echo "  --fast          Tests rápidos (excluir lentos)"
    echo "  --unit          Solo tests unitarios"
    echo "  --integration   Solo tests de integración"
    echo "  --services      Solo tests de servicios"
    echo "  --parallel      Ejecutar en paralelo"
    echo "  --no-cov        Sin cobertura (más rápido)"
    echo "  --html          Generar y abrir reporte HTML"
    echo "  --clean         Limpiar archivos temporales"
    echo "  --help          Mostrar esta ayuda"
    echo ""
    exit 0
}

# Parse argumentos
PYTEST_ARGS=""
MARKERS=""
PARALLEL=""
COVERAGE="--cov=core --cov-report=term-missing"
OPEN_HTML=false
CLEAN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --fast) MARKERS="-m 'not slow'"; shift ;;
        --unit) MARKERS="-m unit"; shift ;;
        --integration) MARKERS="-m integration"; shift ;;
        --services) PYTEST_ARGS="tests/test_services/"; shift ;;
        --parallel) PARALLEL="-n auto"; shift ;;
        --no-cov) COVERAGE=""; shift ;;
        --html) COVERAGE="--cov=core --cov-report=html --cov-report=term-missing"; OPEN_HTML=true; shift ;;
        --clean) CLEAN=true; shift ;;
        --help) show_usage ;;
        *) echo "❌ Opción desconocida: $1"; show_usage ;;
    esac
done

# Limpiar si se solicita
if [ "$CLEAN" = true ]; then
    echo "🧹 Limpiando archivos temporales..."
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    rm -rf htmlcov/ .coverage coverage.xml 2>/dev/null || true
    echo "✅ Limpieza completada"
    echo ""
fi

# Verificar pytest
if ! command -v pytest &> /dev/null; then
    echo "❌ pytest no está instalado"
    echo "Instalar: pip install pytest pytest-django pytest-cov"
    exit 1
fi

# Ejecutar tests
echo "🚀 Ejecutando tests..."
echo ""

CMD="pytest $PYTEST_ARGS $MARKERS $COVERAGE $PARALLEL --tb=short"

if eval $CMD; then
    echo ""
    echo "✅ Tests completados exitosamente"
    EXIT_CODE=0
else
    echo ""
    echo "❌ Algunos tests fallaron"
    EXIT_CODE=1
fi

# Abrir HTML si se solicitó
if [ "$OPEN_HTML" = true ] && [ -f "htmlcov/index.html" ]; then
    echo ""
    echo "📈 Reporte HTML: htmlcov/index.html"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        open htmlcov/index.html
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        xdg-open htmlcov/index.html 2>/dev/null || true
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        start htmlcov/index.html
    fi
fi

echo ""
exit $EXIT_CODE
