@echo off
echo ================================================================
echo VERIFICACION DE SERVIDOR DJANGO
echo ================================================================
echo.

echo Buscando procesos de Python/Django...
tasklist | findstr /i "python"

echo.
echo ================================================================
echo INSTRUCCIONES:
echo ================================================================
echo.
echo Si ves MULTIPLES procesos de python.exe, necesitas:
echo   1. Cerrar TODOS los procesos de Django
echo   2. Abrir Task Manager (Ctrl+Shift+Esc)
echo   3. Buscar "python.exe" y terminar TODOS
echo   4. Iniciar servidor de nuevo
echo.
echo Si solo ves UN proceso, reinicialo:
echo   1. Presiona Ctrl+C en la terminal donde corre
echo   2. Ejecuta: python manage.py runserver
echo.
pause
