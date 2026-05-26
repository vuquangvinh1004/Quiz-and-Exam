; Inno Setup Script for Quiz Desktop App
; Version: 1.0.0
; Target OS: Windows 10/11 (64-bit)
;
; Prerequisites:
;   1. Build the PyInstaller distribution first:
;      cd quiz_desktop_app
;      pyinstaller quiz_app.spec
;   2. Install Inno Setup 6+ from https://jrsoftware.org/isinfo.php
;   3. Open this file in Inno Setup Compiler and press Compile (Ctrl+F9)
;
; Output: quiz_desktop_app\installer\QuizApp_Setup_1.0.0.exe

#define MyAppName      "Quiz Desktop App"
#define MyAppVersion   "1.0.0"
#define MyAppPublisher "Quiz App Team"
#define MyAppURL       ""
#define MyAppExeName   "QuizApp.exe"
#define MyBuildDir     "..\dist\QuizApp"

[Setup]
; === App identity ===
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; === Output ===
OutputDir=installer
OutputBaseFilename=QuizApp_Setup_{#MyAppVersion}
SetupIconFile=..\assets\icons\app_icon.ico

; === Installation directory ===
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes

; === Compression ===
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes

; === Windows version requirement ===
MinVersion=10.0

; === Privileges ===
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

; === Installer appearance ===
WizardStyle=modern
WizardSizePercent=120

; === Misc ===
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
ChangesAssociations=no

[Languages]
Name: "vietnamese"; MessagesFile: "compiler:Languages\Vietnamese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; === Main application bundle (from PyInstaller) ===
Source: "{#MyBuildDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Remove user-created data directory only if empty
Type: dirifempty; Name: "{app}\data"

[Code]
// Additional installer code (optional)
// Can be used to check .NET, VC++ redist, etc. if needed in the future.
