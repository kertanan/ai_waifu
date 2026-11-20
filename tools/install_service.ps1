# Daftarkan api_server.py sebagai Windows Service lewat NSSM.
# Jalankan di PowerShell *sebagai Administrator*:
#   powershell -ExecutionPolicy Bypass -File "E:\Pembuatan Waifu\tools\install_service.ps1"
# Opsi:
#   -NssmPath  lokasi nssm.exe (default D:\nssm\win64\nssm.exe)
#   -Uninstall hapus service
param(
    [string]$NssmPath = "D:\nssm\win64\nssm.exe",
    [string]$ServiceName = "AIWaifuBackend",
    [string]$Python = "D:\python\python.exe",
    [switch]$Uninstall
)
$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $PSScriptRoot
$LogDir = Join-Path $ProjectDir "logs"
$LogFile = Join-Path $LogDir "api_server.log"

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) { throw "Jalankan PowerShell sebagai Administrator." }
if (-not (Test-Path $NssmPath)) { throw "nssm.exe tidak ditemukan di $NssmPath. Pakai -NssmPath <lokasi>." }

function Invoke-Nssm { & $NssmPath @args; if ($LASTEXITCODE -ne 0) { throw "nssm $($args -join ' ') gagal ($LASTEXITCODE)" } }
$existing = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue

if ($Uninstall) {
    if ($existing) { & $NssmPath stop $ServiceName | Out-Null; Invoke-Nssm remove $ServiceName confirm; "Service $ServiceName dihapus." }
    else { "Service $ServiceName tidak ada." }
    return
}

if (-not (Test-Path $Python)) { throw "Python tidak ditemukan di $Python." }

# Port 8080 harus kosong (tutup dulu api_server.py yang jalan di CMD)
$busy = Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue
if ($busy -and -not $existing) {
    $p = Get-Process -Id $busy[0].OwningProcess -ErrorAction SilentlyContinue
    throw "Port 8080 sedang dipakai PID $($busy[0].OwningProcess) ($($p.ProcessName)). Tutup dulu api_server.py yang jalan di terminal."
}

if ($existing) {
    "Service $ServiceName sudah ada, konfigurasi diperbarui."
    & $NssmPath stop $ServiceName | Out-Null
} else {
    Invoke-Nssm install $ServiceName $Python "api_server.py"
}

New-Item -ItemType Directory -Force $LogDir | Out-Null
Invoke-Nssm set $ServiceName Application $Python
Invoke-Nssm set $ServiceName AppParameters "api_server.py"
Invoke-Nssm set $ServiceName AppDirectory $ProjectDir
Invoke-Nssm set $ServiceName DisplayName "AI Waifu Sakura Backend"
Invoke-Nssm set $ServiceName Description "api_server.py (FastAPI :8080) untuk Sakura"
Invoke-Nssm set $ServiceName Start SERVICE_AUTO_START
# UTF-8 supaya print balasan Jepang tidak crash; unbuffered supaya log langsung tertulis
Invoke-Nssm set $ServiceName AppEnvironmentExtra PYTHONUTF8=1 PYTHONUNBUFFERED=1
Invoke-Nssm set $ServiceName AppStdout $LogFile
Invoke-Nssm set $ServiceName AppStderr $LogFile
Invoke-Nssm set $ServiceName AppRotateFiles 1
Invoke-Nssm set $ServiceName AppRotateOnline 1
Invoke-Nssm set $ServiceName AppRotateBytes 10485760
Invoke-Nssm set $ServiceName AppExit Default Restart
Invoke-Nssm set $ServiceName AppRestartDelay 5000

# Jalan sebagai akun Anda sendiri (cache Whisper & profil user tetap sama).
# Akun Microsoft: username = .\<nama folder user> atau email, password = password akun (bukan PIN).
$cred = Get-Credential -UserName "$env:COMPUTERNAME\$env:USERNAME" -Message "Akun Windows untuk menjalankan service $ServiceName"
Invoke-Nssm set $ServiceName ObjectName $cred.UserName $cred.GetNetworkCredential().Password

Invoke-Nssm start $ServiceName
"Menunggu server siap (memuat Whisper)..."
$ok = $false
for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 2
    try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 "http://127.0.0.1:8080/docs" | Out-Null; $ok = $true; break } catch {}
}
if ($ok) { "OK: $ServiceName jalan di http://127.0.0.1:8080. Log: $LogFile" }
else { "Server belum merespons setelah 2 menit. Cek log: Get-Content `"$LogFile`" -Tail 50" }
