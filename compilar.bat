@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
title La Victoriana - Compilador de Instalador
echo.
echo  ============================================
echo    La Victoriana - Generador de Instalador
echo  ============================================
echo.

echo [1/4] Verificando Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no encontrado. Instale Python 3.10+
    echo con "Add Python to PATH" marcado.
    pause
    exit /b 1
)
python --version
echo.

echo [2/4] Instalando dependencias...
pip install customtkinter numpy pandas scipy matplotlib pyinstaller
echo.

echo [3/4] Generando ejecutable con PyInstaller...
echo Esto puede tardar varios minutos, por favor espere...
echo.
python -m PyInstaller --noconfirm --onedir --windowed --name "LaVictoriana" --add-data "data;data" --add-data "core;core" --add-data "gui;gui" --hidden-import customtkinter --hidden-import numpy --hidden-import pandas --hidden-import scipy --hidden-import scipy.stats --hidden-import matplotlib --hidden-import matplotlib.backends.backend_tkagg --collect-all customtkinter app.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] PyInstaller fallo. Revise los errores arriba.
    pause
    exit /b 1
)

echo.
echo  ============================================
echo    [4/4] COMPLETADO!
echo.
echo    El programa ejecutable esta en:
echo    dist\LaVictoriana\LaVictoriana.exe
echo.
echo    Puede copiar toda la carpeta
echo    dist\LaVictoriana\ y compartirla.
echo.
echo    Para un instalador profesional tipo Windows,
echo    instale Inno Setup (gratis):
echo    https://jrsoftware.org/isdl.php
echo    y abra el archivo instalador.iss
echo  ============================================
echo.
pause