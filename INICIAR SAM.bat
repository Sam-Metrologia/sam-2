@echo off
title SAM Metrologia SAS
cd /d "%~dp0"

echo.
echo  ==========================================
echo   SAM Metrologia SAS - Iniciando servidor
echo  ==========================================
echo.

REM Activar entorno virtual
call venv\Scripts\activate.bat

REM Aplicar migraciones pendientes (si las hay)
echo Verificando base de datos...
python manage.py migrate --noinput >nul 2>&1

REM Iniciar servidor en background
echo Iniciando servidor...
start /B python manage.py runserver 8000 >logs\servidor.log 2>&1

REM Esperar 2 segundos y abrir en Google Chrome
timeout /t 2 /nobreak >nul
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" http://localhost:8000

echo.
echo  Servidor corriendo en http://localhost:8000
echo  Cierra esta ventana para detener SAM.
echo.
pause
