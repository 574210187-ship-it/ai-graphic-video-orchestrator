[CmdletBinding()]
param(
    [string]$ActorId
)

$ErrorActionPreference = "Stop"
if (-not $IsWindows -and $PSVersionTable.PSEdition -eq "Core") {
    throw "本脚本只允许在Windows上运行。"
}

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    & "$PSScriptRoot\bootstrap.ps1"
}
if (-not (Get-Command ffprobe -ErrorAction SilentlyContinue)) {
    throw "FFPROBE_NOT_FOUND：请先安装FFmpeg并确认ffprobe.exe已加入PATH。"
}
if (-not $ActorId) {
    $ActorId = Read-Host "请输入这台Windows电脑上Harness的唯一ActorID"
}
if (-not $ActorId) {
    throw "ActorID不能为空。"
}
if ($ActorId -notmatch '^[A-Za-z0-9._|:-]+$') {
    throw "ActorID只允许字母、数字、点、下划线、竖线、冒号和连字符。"
}

$ConfigTarget = Join-Path $RepoRoot "config\config.local.yaml"
if (-not (Test-Path $ConfigTarget)) {
    Copy-Item "config\jiang-lawyer-harness.windows.example.yaml" $ConfigTarget
}
$Yaml = Get-Content $ConfigTarget -Raw -Encoding UTF8
$ActorPattern = [System.Text.RegularExpressions.Regex]::new('(?m)^(\s*actor_id:\s*).+$')
$Yaml = $ActorPattern.Replace($Yaml, "`$1$ActorId", 1)
[System.IO.File]::WriteAllText($ConfigTarget, $Yaml, [System.Text.UTF8Encoding]::new($false))

if (-not ("GvflowCredentialStore" -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Text;

public static class GvflowCredentialStore
{
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    private struct CREDENTIAL
    {
        public UInt32 Flags;
        public UInt32 Type;
        public string TargetName;
        public string Comment;
        public System.Runtime.InteropServices.ComTypes.FILETIME LastWritten;
        public UInt32 CredentialBlobSize;
        public IntPtr CredentialBlob;
        public UInt32 Persist;
        public UInt32 AttributeCount;
        public IntPtr Attributes;
        public string TargetAlias;
        public string UserName;
    }

    [DllImport("Advapi32.dll", EntryPoint = "CredWriteW", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern bool CredWrite(ref CREDENTIAL credential, UInt32 flags);

    public static void Write(string target, string account, string secret)
    {
        byte[] bytes = Encoding.Unicode.GetBytes(secret);
        IntPtr blob = Marshal.AllocHGlobal(bytes.Length);
        try
        {
            Marshal.Copy(bytes, 0, blob, bytes.Length);
            CREDENTIAL credential = new CREDENTIAL
            {
                Type = 1,
                TargetName = target,
                CredentialBlobSize = (UInt32)bytes.Length,
                CredentialBlob = blob,
                Persist = 2,
                UserName = account
            };
            if (!CredWrite(ref credential, 0))
            {
                throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error());
            }
        }
        finally
        {
            for (int i = 0; i < bytes.Length; i++) bytes[i] = 0;
            Marshal.Copy(bytes, 0, blob, bytes.Length);
            Marshal.FreeHGlobal(blob);
        }
    }
}
'@
}

$SecureSecret = Read-Host "请在本机直接输入飞书应用App Secret（不会显示，也不要发到聊天）" -AsSecureString
$SecretPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureSecret)
try {
    $PlainSecret = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($SecretPointer)
    [GvflowCredentialStore]::Write("gvflow-feishu-app-secret", "cli_aafee2971478dbcf", $PlainSecret)
} finally {
    if ($SecretPointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($SecretPointer)
    }
    $PlainSecret = $null
    $SecureSecret = $null
}

$Gvflow = Join-Path $RepoRoot ".venv\Scripts\gvflow.exe"
Write-Host "开始只读认证、字段与候选检查；production.enabled仍为false。"
& $Gvflow doctor --config $ConfigTarget
if ($LASTEXITCODE -ne 0) {
    throw "FEISHU_DOCTOR_FAILED：请按上方输出核对应用scope、目标Base文档权限或字段映射。"
}
& $Gvflow discover --config $ConfigTarget
if ($LASTEXITCODE -ne 0) {
    throw "FEISHU_DISCOVER_FAILED：无法完成飞书实时只读扫描。"
}

Write-Host "Windows飞书只读准备完成。写权限必须使用专用测试记录另行验证："
Write-Host ".venv\Scripts\gvflow.exe verify-write-access --config config\config.local.yaml --record-id <专用测试record_id> --confirm-dedicated-test-record"
