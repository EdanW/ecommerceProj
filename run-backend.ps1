Set-Location -Path $PSScriptRoot

$venvActivate = Join-Path $PSScriptRoot "backend\.venv\Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
    . $venvActivate
}

uvicorn backend.main:app --reload --port 8000
