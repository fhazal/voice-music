; Voice Music for BajuBesi: friend installer (light app, speech runs on the BajuBesi server)
#define AppName "Voice Music for BajuBesi"
#define AppVer "1.4"
#define Exe "VoiceMusicLite.exe"

[Setup]
AppId={{6E2B6C0D-2C57-4B5B-9B52-7A4D1B7C3F11}
AppName={#AppName}
AppVersion={#AppVer}
AppPublisher=BajuBesi Labs
DefaultDirName={localappdata}\Programs\Voice Music
DefaultGroupName=Voice Music
UninstallDisplayIcon={app}\{#Exe}
PrivilegesRequired=lowest
OutputDir=dist-installer
OutputBaseFilename=VoiceMusic-Setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=force

[Tasks]
Name: "startup"; Description: "Start with Windows (shows the Windows permission prompt at each start-up)"; Flags: unchecked
Name: "desktopicon"; Description: "Desktop shortcut"; Flags: checkedonce

[Files]
Source: "dist-lite\VoiceMusicLite\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{userstartup}\Voice Music"; Filename: "{app}\{#Exe}"; Tasks: startup
Name: "{group}\Voice Music"; Filename: "{app}\{#Exe}"
Name: "{autodesktop}\Voice Music"; Filename: "{app}\{#Exe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#Exe}"; Description: "Start Voice Music now"; Flags: nowait postinstall skipifsilent shellexec
Filename: "{app}\{#Exe}"; Flags: nowait shellexec; Check: WizardSilent

[UninstallRun]
Filename: "taskkill.exe"; Parameters: "/F /IM {#Exe}"; Flags: runhidden; RunOnceId: "KillApp"

[UninstallDelete]
Type: files; Name: "{app}\config.json"
Type: files; Name: "{app}\run.log"

[Code]
var
  HookPage: TInputQueryWizardPage;

function Silent(): Boolean;
begin
  Result := WizardSilent;
end;

function WebhookParam(): String;
begin
  Result := ExpandConstant('{param:WEBHOOK|}');
end;

procedure InitializeWizard;
begin
  HookPage := CreateInputQueryPage(wpWelcome, 'Your webhook address',
    'The admin who invited you sent it privately.',
    'Paste it below. Keep it secret: it works like your password for the bot.');
  HookPage.Add('Webhook address:', False);
  HookPage.Values[0] := WebhookParam();
end;

function LooksLikeWebhook(S: String): Boolean;
begin
  Result := (Pos('https://discord.com/api/webhooks/', S) = 1) or (Pos('https://discordapp.com/api/webhooks/', S) = 1);
end;

function DiscordKnows(S: String): Boolean;
var
  Req: Variant;
begin
  try
    Req := CreateOleObject('WinHttp.WinHttpRequest.5.1');
    Req.Open('GET', S, False);
    Req.Send('');
    Result := Req.Status = 200;
  except
    Result := True; { offline or blocked: don't stop the install }
  end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  S: String;
begin
  Result := True;
  if CurPageID = HookPage.ID then
  begin
    S := Trim(HookPage.Values[0]);
    if not LooksLikeWebhook(S) then
    begin
      MsgBox('That does not look like a webhook address. It starts with https://discord.com/api/webhooks/', mbError, MB_OK);
      Result := False;
    end
    ;
  end;
end;

function HasOldConfig(): Boolean;
var
  T: AnsiString;
begin
  { An earlier install already holds a webhook address: an update keeps it. }
  Result := LoadStringFromFile(AddBackslash(WizardDirValue) + 'config.json', T) and (Pos('/api/webhooks/', T) > 0);
end;

function KeepOldConfig(): Boolean;
begin
  Result := (WebhookParam() = '') and HasOldConfig();
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := (PageID = HookPage.ID) and (Silent() or KeepOldConfig());
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  Hook: String;
begin
  if (CurStep = ssPostInstall) and not KeepOldConfig() then
  begin
    if Silent() then Hook := WebhookParam() else Hook := Trim(HookPage.Values[0]);
    SaveStringToFile(ExpandConstant('{app}\config.json'),
      '{' + #13#10 + '  "webhook": "' + Hook + '",' + #13#10 + '  "button": "x1"' + #13#10 + '}' + #13#10, False);
  end;
end;
