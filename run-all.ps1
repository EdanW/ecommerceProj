Set-Location -Path $PSScriptRoot

$backendScript = Join-Path $PSScriptRoot "run-backend.ps1"
$frontendScript = Join-Path $PSScriptRoot "run-frontend.ps1"

Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-File", $backendScript
Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-File", $frontendScript
