; Установщик Flagship Converter.
; Компилируется из release.py:  ISCC /DAppVersion=<версия> packaging\installer.iss
; AppId фиксированный — новые версии ставятся поверх старой установки.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{8A7C0D2E-4B1F-4E9A-9C3D-6F5E2A718B4C}
AppName=Flagship Converter
AppVersion={#AppVersion}
AppPublisher=PASII11
AppPublisherURL=https://github.com/PASII11/flagship_converter
AppSupportURL=https://github.com/PASII11/flagship_converter/issues
DefaultDirName={autopf}\Flagship Converter
DefaultGroupName=Flagship Converter
UninstallDisplayIcon={app}\FlagshipConverter.exe
Compression=lzma2
SolidCompression=yes
OutputDir=..\release
OutputBaseFilename=FlagshipConverter-Setup-{#AppVersion}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
DisableProgramGroupPage=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

; При обновлении поверх старой версии вычищаем прежний рантайм,
; чтобы не оставались устаревшие DLL.
[InstallDelete]
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "..\dist\FlagshipConverter\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Flagship Converter"; Filename: "{app}\FlagshipConverter.exe"
Name: "{autodesktop}\Flagship Converter"; Filename: "{app}\FlagshipConverter.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\FlagshipConverter.exe"; Description: "{cm:LaunchProgram,Flagship Converter}"; Flags: nowait postinstall skipifsilent
