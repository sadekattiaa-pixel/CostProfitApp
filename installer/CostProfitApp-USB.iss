#define MyAppName "Invoice Portable"
#define MyAppVersion "1.1.0"
#ifndef MyAppSource
  #define MyAppSource "..\dist\Invoice"
#endif

#define MyAppPublisher "Alintilqa Programming & Digital Solutions"

[Setup]
AppId={{68D77A2A-9347-4A91-B32B-3AD4BF77C7E5}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\InvoicePortable
DisableProgramGroupPage=yes
DisableReadyMemo=no
OutputDir=..\dist\installer
OutputBaseFilename=Invoice-Portable-Installer-{#MyAppVersion}
SetupIconFile=..\assets\app_icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
Uninstallable=no
UsePreviousAppDir=no
CreateAppDir=yes
DirExistsWarning=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "arabic"; MessagesFile: "compiler:Languages\Arabic.isl"

[Dirs]
Name: "{app}\App\License"

[Files]
Source: "{#MyAppSource}\*"; DestDir: "{app}\App"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "portable-config.json"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist

[Icons]
Name: "{app}\Start Invoice"; Filename: "{app}\App\Invoice.exe"; WorkingDir: "{app}\App"; IconFilename: "{app}\App\Invoice.exe"

