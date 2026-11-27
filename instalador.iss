; Instalador de VICTORA (Inno Setup 6). Compilar después de PyInstaller:  ISCC instalador.iss
#define AppVer "3.0"
[Setup]
AppId={{6A1F3C2E-9B7D-4E21-A8C5-3F0D1C7A9E03}
AppName=VICTORA
AppVersion={#AppVer}
AppPublisher=VICTORA
DefaultDirName={localappdata}\Programs\VICTORA
DefaultGroupName=VICTORA
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename=VICTORA_Instalador
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\VICTORA.exe
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "escritorio"; Description: "Crear acceso directo en el escritorio"; Flags: checkedonce

[Files]
Source: "dist\VICTORA\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\VICTORA"; Filename: "{app}\VICTORA.exe"
Name: "{group}\Desinstalar VICTORA"; Filename: "{uninstallexe}"
Name: "{userdesktop}\VICTORA"; Filename: "{app}\VICTORA.exe"; Tasks: escritorio

[Run]
Filename: "{app}\VICTORA.exe"; Description: "Abrir VICTORA ahora"; Flags: nowait postinstall skipifsilent
