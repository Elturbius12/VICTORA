@echo off
chcp 65001 >nul 2>&1
title La Victoriana - Instalador
echo.
echo  ============================================
echo    La Victoriana - Sistema de Pronostico
echo    Instalador automatico
echo  ============================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no esta instalado.
    echo Descargue Python 3.10+ desde https://www.python.org/downloads/
    echo IMPORTANTE: Marque "Add Python to PATH" durante la instalacion.
    pause
    exit /b 1
)

echo [1/3] Python encontrado.
python --version
echo.

cd /d "%~dp0"

echo [2/3] Instalando dependencias...
pip install -r requirements.txt
echo.

echo [3/3] Creando acceso directo en el escritorio...
echo @echo off > "%USERPROFILE%\Desktop\La Victoriana.bat"
echo cd /d "%~dp0" >> "%USERPROFILE%\Desktop\La Victoriana.bat"
echo python app.py >> "%USERPROFILE%\Desktop\La Victoriana.bat"

echo.
echo  ============================================
echo    Instalacion completada!
echo.
echo    Para iniciar: doble clic en
echo    "La Victoriana" en el escritorio
echo    O ejecute: python app.py
echo  ============================================
echo.
pause
