#!/usr/bin/env pwsh

# Smart Prerequisites Installer for MCP Server for Splunk (Windows)
# - Installs uv (per official Windows installer)
# - Installs Node.js (for Inspector) via WinGet, fallback to Chocolatey
# - Uses uv to install Python per .python-version or pyproject.toml requires-python
# - Verifies availability

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Ok([string]$Message) { Write-Host "✔ $Message" -ForegroundColor Green }
function Write-Note([string]$Message) { Write-Host "• $Message" -ForegroundColor Yellow }
function Write-Err([string]$Message) { Write-Host "✖ $Message" -ForegroundColor Red }

Write-Host "=== MCP for Splunk: Smart Prerequisites Installer (Windows) ==="

function Test-Command([string]$Name) {
  try { $null -ne (Get-Command $Name -ErrorAction Stop) } catch { $false }
}

function Ensure-UvInstalled {
  if (Test-Command 'uv') {
    Write-Ok "uv already installed ($(uv --version))"
    return
  }

  Write-Note "Installing uv via official installer (Windows)..."
  try {
    # Per docs: irm https://astral.sh/uv/install.ps1 | iex
    # Execute the installer script in the CURRENT PowerShell session to avoid nested processes
    Invoke-Expression (Invoke-RestMethod -Uri 'https://astral.sh/uv/install.ps1') | Out-Null
  } catch {
    Write-Err "uv installation failed: $($_.Exception.Message)"
    throw
  }

  # Ensure PATH includes the default uv location for this session
  $localBin = Join-Path $env:USERPROFILE ".local\bin"
  $cargoBin = Join-Path $env:USERPROFILE ".cargo\bin"
  if (-not (Test-Command 'uv')) {
    if (Test-Path $localBin) { $env:Path = "$localBin;$env:Path" }
    if (-not (Test-Command 'uv') -and (Test-Path $cargoBin)) { $env:Path = "$cargoBin;$env:Path" }
  }

  if (Test-Command 'uv') {
    Write-Ok "uv installed ($(uv --version))"
  } else {
    Write-Err "uv not found after installation. Ensure $localBin is in your PATH."
    throw "uv not found"
  }
}

function Resolve-PythonRequest {
  $script:PythonRequest = ""
  if (Test-Path ".python-version") {
    $script:PythonRequest = (Get-Content ".python-version" -TotalCount 1).Trim()
  }
  if (-not $script:PythonRequest -and (Test-Path "pyproject.toml")) {
    $inProj = $false
    foreach ($line in Get-Content "pyproject.toml") {
      if ($line -match '^\[project\]') { $inProj = $true; continue }
      if ($line -match '^\[' -and $inProj) { break }
      if ($inProj -and ($line -match 'requires-python\s*=\s*"([^"]+)"')) { $script:PythonRequest = $Matches[1]; break }
    }
  }
  if (-not $script:PythonRequest) {
    $script:PythonRequest = "3.11"
    Write-Note "No Python requirement detected; defaulting to $script:PythonRequest"
  } else {
    Write-Note "Detected Python requirement: $script:PythonRequest"
  }
}

function Install-PythonWithUv([string]$Request) {
  Write-Note "Installing Python via uv ($Request)..."
  $proc = Start-Process -FilePath "uv" -ArgumentList @("python","install",$Request) -NoNewWindow -Wait -PassThru
  if ($proc.ExitCode -ne 0) {
    Write-Err "uv python install failed with exit code $($proc.ExitCode)"
    throw "uv python install failed"
  }

  $pyPath = & uv python find $Request 2>$null
  if (-not $pyPath) {
    Write-Err "uv could not find a compatible Python for request: $Request"
    throw "uv python find failed"
  }
  Write-Ok "Python available at: $pyPath"
}

function Ensure-NodeInstalled {
  if (Test-Command 'node') {
    Write-Ok "Node.js already installed ($(node --version))"
    return
  }

  if (Test-Command 'winget') {
    Write-Note "Installing Node.js LTS via WinGet..."
    winget install -e --id OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements | Out-Null
  } elseif (Test-Command 'choco') {
    Write-Note "Installing Node.js LTS via Chocolatey..."
    choco install nodejs-lts -y | Out-Null
  } else {
    Write-Err "Neither WinGet nor Chocolatey available to install Node.js."
    throw "Node.js installer not available"
  }

  if (Test-Command 'node') {
    Write-Ok "Node.js installed ($(node --version))"
  } else {
    Write-Err "Node.js still not found after installation."
    throw "Node.js not found"
  }
}

# Main
Ensure-UvInstalled
Ensure-NodeInstalled
Resolve-PythonRequest
Install-PythonWithUv -Request $script:PythonRequest

Write-Host
Write-Note "Verifying core dependencies..."
if (-not (Test-Command 'uv')) { Write-Err "Missing uv"; exit 1 }
if (-not (Test-Command 'node')) { Write-Err "Missing Node.js"; exit 1 }
Write-Ok "All core dependencies verified"

# Additional check: ensure a usable Python executable is discoverable by uv
$pyFound = & uv python find 2>$null
if ($pyFound) {
  Write-Ok "uv can find Python ($pyFound)"
} else {
  Write-Err "uv cannot find a Python interpreter. Please re-run this installer or install Python via uv manually."
  exit 1
}

Write-Ok "Prerequisite check/install complete"


