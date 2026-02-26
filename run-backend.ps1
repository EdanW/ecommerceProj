Set-Location -Path $PSScriptRoot

$venvPath = Join-Path $PSScriptRoot "backend\.venv"
$venvActivate = Join-Path $venvPath "Scripts\Activate.ps1"
$requirements = Join-Path $PSScriptRoot "backend\requirements.txt"

# Ensure Python 3.12 exists
$pythonCmd = Get-Command python3.12 -ErrorAction SilentlyContinue

if (-not $pythonCmd) {
    Write-Host "Python 3.12 is required but not found." -ForegroundColor Red
    Write-Host "Please install Python 3.12 and try again."
    exit 1
}

# Create venv if it doesn't exist
if (-not (Test-Path $venvActivate)) {
    Write-Host "Creating virtual environment with Python 3.12..."
    python3.12 -m venv $venvPath
}

# Activate venv
. $venvActivate

# Install dependencies if needed
if (Test-Path $requirements) {
    Write-Host "Installing backend dependencies..."
    pip install -r $requirements
}

# Run server
uvicorn backend.main:app --reload --port 8000