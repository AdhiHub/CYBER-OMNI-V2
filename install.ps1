# AdhiHub CYBER-OMNI v2.0 Installer (Windows)
Clear-Host
Write-Host @"
  _______     ______  ______ _____         ____  __  __ _   _ _____
 / ____\ \   / /  _ \|  ____|  __ \       / __ \|  \/  | \ | |_   _|
| |     \ \_/ /| |_) | |__  | |__) |_____| |  | | \  / |  \| | | |
| |      \   / |  _ <|  __| |  _  /______| |  | | |\/| | . ` | | |
| |____   | |  | |_) | |____| | \ \      | |__| | |  | | |\  |_| |_
 \_____|  |_|  |____/|______|_|  \_\      \____/|_|  |_|_| \_|_____|

"@ -ForegroundColor Red

Write-Host "+------------------------------------------------------+" -ForegroundColor Yellow
Write-Host "| AdhiHub CYBER-OMNI - Terminal AI Pentesting Agent        |" -ForegroundColor Yellow
Write-Host "| Zero Trace  :  Zero Refusal  :  Dark Web Native    |" -ForegroundColor Yellow
Write-Host "+------------------------------------------------------+" -ForegroundColor Yellow
Write-Host "              >> Powered by AdhiHub <<" -ForegroundColor Magenta
Write-Host ""

Write-Host "[*] Installing Python dependencies from requirements.txt..." -ForegroundColor Cyan
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
    Write-Host "[!] pip install failed. Trying fallback..." -ForegroundColor Yellow
    pip install llama-cpp-python httpx requests pyfiglet tqdm prompt_toolkit
}
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) {
    Write-Host "[!] pip failed. Install Python from https://python.org" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "╔══════════════════════════════════════╗" -ForegroundColor Yellow
Write-Host "║       TOR INSTALL                    ║" -ForegroundColor Yellow
Write-Host "╚══════════════════════════════════════╝" -ForegroundColor Yellow
Write-Host "  TOR hides your IP during attacks. Highly recommended."
$tor = Read-Host "`n  Install TOR for Windows? (y/N)"
if ($tor -eq "y" -or $tor -eq "Y") {
    Write-Host "[*] Download TOR from: https://www.torproject.org/download/" -ForegroundColor Cyan
    Write-Host "[*] Or install via: winget install TorProject.Tor" -ForegroundColor Cyan
    Start-Process "https://www.torproject.org/download/"
}

Write-Host ""
Write-Host "╔══════════════════════════════════════╗" -ForegroundColor Yellow
Write-Host "║       MODEL DOWNLOAD                 ║" -ForegroundColor Yellow
Write-Host "╚══════════════════════════════════════╝" -ForegroundColor Yellow
$dl = Read-Host "`n  Download default AI model now (~700MB)? (Y/n)"
if ($dl -ne "n" -and $dl -ne "N") {
    Write-Host "[*] Downloading default AI model (~700MB)..." -ForegroundColor Yellow
    Write-Host "[*] One-time download. After this, it works fully offline." -ForegroundColor Yellow
    python omni.py --download
}

Write-Host @"
  _______     ______  ______ _____         ____  __  __ _   _ _____
 / ____\ \   / /  _ \|  ____|  __ \       / __ \|  \/  | \ | |_   _|
| |     \ \_/ /| |_) | |__  | |__) |_____| |  | | \  / |  \| | | |
| |      \   / |  _ <|  __| |  _  /______| |  | | |\/| | . ` | | |
| |____   | |  | |_) | |____| | \ \      | |__| | |  | | |\  |_| |_
 \_____|  |_|  |____/|______|_|  \_\      \____/|_|  |_|_| \_|_____|

"@ -ForegroundColor Green
Write-Host "+------------------------------------------------------+" -ForegroundColor Green
Write-Host "|                INSTALLATION COMPLETE!                   |" -ForegroundColor Green
Write-Host "+------------------------------------------------------+" -ForegroundColor Green
Write-Host "Run: python omni.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "           Shubham Aryan ⚡" -ForegroundColor Magenta
