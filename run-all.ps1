Set-Location -Path $PSScriptRoot

$backendCmd = "Set-Location -Path `"$PSScriptRoot`"; " +
    "if (Test-Path `"venv\Scripts\Activate.ps1`") { . `"venv\Scripts\Activate.ps1`" }; " +
    "uvicorn backend.main:app --reload --port 8000"

$frontendCmd = "Set-Location -Path `"$PSScriptRoot\frontend`"; npm run dev"

Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", $backendCmd
Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", $frontendCmd
