# Pengawas LM Studio untuk Sakura (dijalankan sebagai service NSSM "AIWaifuLLM").
# - Menyalakan daemon LM Studio (llmster, tanpa GUI) dan server API di port 1234
# - Memuat model dengan offload GPU sebagian supaya GPT-SoVITS tetap muat di VRAM 4 GB
# - Dicek ulang tiap $IntervalSec detik; kalau model hilang/terlepas, dimuat lagi dengan setelan yang sama
param(
    [string]$Lms = "C:\Users\user\.lmstudio\bin\lms.exe",
    [string]$Model = "qwen/qwen3-4b-2507",
    [string]$Gpu = "0.5",
    [int]$Context = 8192,
    [int]$Port = 1234,
    [int]$IntervalSec = 60,
    [int]$WaitSovitsSec = 180
)
$ErrorActionPreference = "Continue"

function Write-Log($msg) { Write-Output ("{0:yyyy-MM-dd HH:mm:ss} {1}" -f (Get-Date), $msg) }
function Invoke-Lms { & $Lms @args 2>&1 | Where-Object { $_ -notmatch "extra certs" } | ForEach-Object { "$_" } }
function Test-Port($p) { [bool](Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue) }

if (-not (Test-Path $Lms)) { Write-Log "lms tidak ditemukan: $Lms"; exit 1 }
Write-Log "Pengawas LLM mulai (model=$Model, gpu=$Gpu, ctx=$Context)"

while ($true) {
    try {
        $st = Invoke-Lms daemon status
        if (($st -join " ") -notmatch "is running") {
            Write-Log "Daemon mati, menyalakan..."
            Invoke-Lms daemon up | ForEach-Object { Write-Log "  $_" }
        }

        if (-not (Test-Port $Port)) {
            Write-Log "Server port $Port mati, menyalakan..."
            Invoke-Lms server start --port $Port | ForEach-Object { Write-Log "  $_" }
        }

        $ps = (Invoke-Lms ps) -join "`n"
        if ($ps -notmatch [regex]::Escape($Model)) {
            # Tunggu GPT-SoVITS dulu supaya VRAM-nya kebagian (maks. $WaitSovitsSec dtk)
            $t = 0
            while (-not (Test-Port 9880) -and $t -lt $WaitSovitsSec) { Start-Sleep 5; $t += 5 }
            if (-not (Test-Port 9880)) { Write-Log "GPT-SoVITS belum jalan, model tetap dimuat" }
            Write-Log "Model belum dimuat, memuat $Model (gpu $Gpu)..."
            Invoke-Lms load $Model --gpu $Gpu --context-length $Context --identifier $Model -y |
                Select-Object -Last 2 | ForEach-Object { Write-Log "  $_" }
        }
    } catch {
        Write-Log "Error: $_"
    }
    Start-Sleep -Seconds $IntervalSec
}
