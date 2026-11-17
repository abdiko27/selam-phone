; Inno Setup 6 script for the branded phone app.
; Do not edit names here: tools/package.py passes them in from brand/brand.json.
; SPDX-License-Identifier: GPL-2.0-or-later

#ifndef AppName
  #define AppName "Selam Phone"
#endif
#ifndef ExeName
  #define ExeName "SelamPhone"
#endif
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#ifndef Company
  #define Company "Selam Communications"
#endif
#ifndef AppGuid
  #define AppGuid "{{00000000-0000-0000-0000-000000000000}"
#endif
#ifndef Website
  #define Website "https://example.com"
#endif
#ifndef SupportUrl
  #define SupportUrl "https://example.com/support"
#endif
#ifndef Server
  #define Server "192.168.26.10"
#endif
#ifndef Transport
  #define Transport "udp"
#endif
#ifndef Voicemail
  #define Voicemail "*97"
#endif
#ifndef Label
  #define Label "Office"
#endif
#ifndef UpdatesNever
  #define UpdatesNever "1"
#endif
#ifndef SourceDir
  #define SourceDir "..\build\stage\app"
#endif
#ifndef OutputDir
  #define OutputDir "..\dist"
#endif
#ifndef IconFile
  #define IconFile "..\brand\icons\app.ico"
#endif
#ifndef LicenseFile
  #define LicenseFile SourceDir + "\licenses\COPYING"
#endif

[Setup]
AppId={#AppGuid}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#Company}
AppPublisherURL={#Website}
AppSupportURL={#SupportUrl}
VersionInfoVersion={#AppVersion}
VersionInfoCompany={#Company}
VersionInfoProductName={#AppName}
; Per-user install: no admin rights needed, works on locked-down office PCs
PrivilegesRequired=lowest
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#ExeName}.exe
SetupIconFile={#IconFile}
LicenseFile={#LicenseFile}
OutputDir={#OutputDir}
OutputBaseFilename={#ExeName}-{#AppVersion}-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
ArchitecturesAllowed=x86compatible

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "autostart"; Description: "Start {#AppName} when I sign in to Windows"; GroupDescription: "Startup:"

[Files]
; Empty settings file holding only the UTF-16 marker (see WriteSettings)
Source: "blank.ini"; Flags: dontcopy
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#ExeName}.exe"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#ExeName}.exe"; Tasks: desktopicon

[Registry]
; The app looks for this key. When its default value equals the install folder the app
; keeps its settings in %APPDATA%\{#AppName}\ instead of next to the program (installer mode).
Root: HKA; Subkey: "Software\{#AppName}"; ValueType: string; ValueName: ""; ValueData: "{app}"; Flags: uninsdeletekey
; Also read by the app if its settings are ever reset (/reset).
Root: HKA; Subkey: "Software\{#AppName}"; ValueType: dword; ValueName: "RunAtSystemStartup"; ValueData: "1"; Tasks: autostart
Root: HKA; Subkey: "Software\{#AppName}"; ValueType: dword; ValueName: "RunAtSystemStartup"; ValueData: "0"; Tasks: not autostart
; The app only reads RunAtSystemStartup when it creates its settings itself, and the installer
; creates them, so the startup entry is written here (same name and form the app uses).
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#AppName}"; ValueData: """{app}\{#ExeName}.exe"" /minimized"; Flags: uninsdeletevalue; Tasks: autostart
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; ValueName: "{#AppName}"; Flags: deletevalue uninsdeletevalue dontcreatekey; Tasks: not autostart

[Run]
Filename: "{app}\{#ExeName}.exe"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[Code]
var
  AccountPage: TInputQueryWizardPage;

function IniPath(): String;
begin
  Result := ExpandConstant('{userappdata}\{#AppName}\{#ExeName}.ini');
end;

function ParamOrEmpty(const Name: String): String;
begin
  { Silent installs: setup.exe /SILENT /EXT=1005 /SIPPASS=secret /NAME="Front desk" }
  Result := ExpandConstant('{param:' + Name + '|}');
end;

procedure InitializeWizard();
begin
  AccountPage := CreateInputQueryPage(wpSelectTasks,
    'Phone account',
    'Enter the extension details your administrator gave you.',
    'You can leave this empty and fill it in later from the app''s Account menu. ' +
    'Phone system: {#Server}');
  AccountPage.Add('Extension number:', False);
  AccountPage.Add('Password (SIP secret):', True);
  AccountPage.Add('Your name (shown to people you call):', False);
  AccountPage.Values[0] := ParamOrEmpty('EXT');
  AccountPage.Values[1] := ParamOrEmpty('SIPPASS');
  AccountPage.Values[2] := ParamOrEmpty('NAME');
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  { Upgrades keep the existing account, so don't ask again }
  Result := (PageID = AccountPage.ID) and FileExists(IniPath());
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  i: Integer;
  s: String;
begin
  Result := True;
  if CurPageID = AccountPage.ID then begin
    s := Trim(AccountPage.Values[0]);
    for i := 1 to Length(s) do
      if (s[i] < '0') or (s[i] > '9') then begin
        MsgBox('The extension should be a number, for example 1005.', mbError, MB_OK);
        Result := False;
        exit;
      end;
    if (s <> '') and (AccountPage.Values[1] = '') then begin
      MsgBox('Please enter the password for extension ' + s + '.', mbError, MB_OK);
      Result := False;
    end;
  end;
end;

procedure Put(const Section, Key, Value: String);
begin
  SetIniString(Section, Key, Value, IniPath());
end;

procedure WriteSettings();
var
  ext, pass, name: String;
begin
  ForceDirectories(ExtractFileDir(IniPath()));
  { A file that starts with the UTF-16 marker makes Windows store the settings in Unicode,
    so names in Amharic or any other script are kept correctly. }
  ExtractTemporaryFile('blank.ini');
  FileCopy(ExpandConstant('{tmp}\blank.ini'), IniPath(), False);

  Put('Settings', 'accountId', '1');
  if '{#UpdatesNever}' = '1' then
    Put('Settings', 'updatesInterval', 'never');

  ext := Trim(AccountPage.Values[0]);
  pass := AccountPage.Values[1];
  name := Trim(AccountPage.Values[2]);

  Put('Account1', 'label', '{#Label}');
  Put('Account1', 'server', '{#Server}');
  Put('Account1', 'domain', '{#Server}');
  Put('Account1', 'transport', '{#Transport}');
  Put('Account1', 'voicemailNumber', '{#Voicemail}');
  Put('Account1', 'username', ext);
  Put('Account1', 'authID', ext);
  { Stored in plain text only until the app's first start, which encrypts it. }
  Put('Account1', 'password', pass);
  Put('Account1', 'displayName', name);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssPostInstall) and not FileExists(IniPath()) then
    WriteSettings();
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
    if MsgBox('Also remove your {#AppName} settings, contacts and call history?',
              mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then begin
      DelTree(ExpandConstant('{userappdata}\{#AppName}'), True, True, True);
      DelTree(ExpandConstant('{localappdata}\{#AppName}'), True, True, True);
    end;
end;
