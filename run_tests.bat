@echo off
REM Script para ejecutar tests en Windows - SAM Metrología
REM Uso: run_tests.bat [opciones]

echo.
echo SAM Metrología - Sistema de Testing
echo =======================================
echo.

REM Ejecutar tests con pytest
echo Ejecutando tests...
echo.

pytest --cov=core --cov-report=html --cov-report=term-missing --tb=short %*

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Tests completados exitosamente
) else (
    echo.
    echo Algunos tests fallaron
)

REM Verificar reporte HTML
if exist "htmlcov\index.html" (
    echo.
    echo Reporte HTML generado: htmlcov\index.html
    echo Para abrir: start htmlcov\index.html
)

echo.
pause
