@echo off
echo ========================================================
echo   PayrollFlow - Iniciando con Docker Compose
echo ========================================================
echo Levantando base de datos PostgreSQL y servicio web...
docker compose up -d --build
echo.
echo ========================================================
echo PayrollFlow levantado exitosamente en contenedores!
echo   * Web App: http://localhost:8000
echo   * Swagger: http://localhost:8000/docs
echo ========================================================
pause
