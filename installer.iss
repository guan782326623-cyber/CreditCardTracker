; Inno Setup 安装脚本
; 生成: CardTrackerSetup.exe

[Setup]
AppName=Credit Card Tracker
AppVersion=1.0
AppPublisher=Yu Guan
AppPublisherURL=
DefaultDirName={autopf}\CardTracker
DefaultGroupName=Card Tracker
OutputDir=.
OutputBaseFilename=CardTrackerSetup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
; 需要管理员权限安装到 Program Files
PrivilegesRequired=admin
; 安装后自动启动
; UninstallDisplayIcon={app}\CardTracker.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "在桌面创建快捷方式"; GroupDescription: "附加选项:"

[Files]
; 把 PyInstaller 生成的整个 dist\CardTracker 目录复制进去
Source: "dist\CardTracker\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; 开始菜单
Name: "{group}\Credit Card Tracker"; Filename: "{app}\CardTracker.exe"
Name: "{group}\卸载 Card Tracker"; Filename: "{uninstallexe}"
; 桌面快捷方式
Name: "{commondesktop}\Credit Card Tracker"; Filename: "{app}\CardTracker.exe"; Tasks: desktopicon

[Run]
; 安装完成后询问是否立即启动
Filename: "{app}\CardTracker.exe"; Description: "立即启动 Card Tracker"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; 卸载时删除程序目录
Type: filesandordirs; Name: "{app}"
