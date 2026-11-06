[Setup]
AppName=La Victoriana - Pronostico de Demanda
AppVersion=1.0
AppPublisher=La Victoriana
DefaultDirName={autopf}\LaVictoriana
DefaultGroupName=La Victoriana
OutputBaseFilename=LaVictoriana_Setup
OutputDir=instalador_output
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
DisableProgramGroupPage=yes

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el Escritorio"

[Files]
Source: "dist\LaVictoriana\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\La Victoriana"; Filename: "{app}\LaVictoriana.exe"
Name: "{group}\Desinstalar La Victoriana"; Filename: "{uninstallexe}"
Name: "{autodesktop}\La Victoriana"; Filename: "{app}\LaVictoriana.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\LaVictoriana.exe"; Description: "Abrir La Victoriana"; Flags: nowait postinstall skipifsilent