@echo off
REM 1) dist\VICTORA\VICTORA.exe  2) dist\VICTORA_Windows.zip (portable)  3) dist\VICTORA_Instalador.exe
python -m pip install -r requirements.txt pyinstaller || exit /b 1
python -m PyInstaller --noconfirm --clean VICTORA.spec || exit /b 1
copy /Y LEEME_USUARIOS.txt dist\VICTORA\ >nul
dist\VICTORA\VICTORA.exe --autotest || (echo AUTOTEST FALLO & exit /b 1)
pushd dist && tar.exe -a -c -f VICTORA_Windows.zip VICTORA && popd
set ISCC="%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not exist %ISCC% set ISCC="%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist %ISCC% (%ISCC% /Q instalador.iss) else (echo Instale Inno Setup 6 para generar el instalador.)
echo Listo. Comparta dist\VICTORA_Instalador.exe  (o el ZIP portable).
