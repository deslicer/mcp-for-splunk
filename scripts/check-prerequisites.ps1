# MCP Server for Splunk - Prerequisites Checker (Windows)
# This script verifies that all required prerequisites are installed

param(
    [switch]$Detailed,
    [switch]$Help
)

# Set strict mode for better error handling
Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

# Show help if requested
if ($Help) {
    Write-Host @"
MCP Server for Splunk - Prerequisites Checker (Windows)

Usage:
    .\scripts\check-prerequisites.ps1 [options]

Options:
    -Detailed       Show detailed version information and installation paths
    -Help           Show this help message

Examples:
    .\scripts\check-prerequisites.ps1           # Basic check
    .\scripts\check-prerequisites.ps1 -Detailed # Detailed information

"@ -ForegroundColor Cyan
    exit 0
}

Write-Host "🔍 Checking Prerequisites for MCP Server for Splunk..." -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

# Color functions
function Write-Success {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠️  $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor Red
}

function Write-Info {
    param([string]$Message)
    Write-Host "ℹ️  $Message" -ForegroundColor Blue
}

# Track installation status
$missingRequirements = @()
$optionalMissing = @()
$installationTips = @()

# Required tools check
$requiredTools = @{
    "Python" = @{
        command = "python"
        args = "--version"
        optional = $false
        installTip = "Install from Microsoft Store or run: winget install Python.Python.3.12"
    }
    "UV Package Manager" = @{
        command = "uv"
        args = "--version"
        optional = $false
        installTip = "Run: irm https://astral.sh/uv/install.ps1 | iex"
    }
    "Git" = @{
        command = "git"
        args = "--version"
        optional = $false
        installTip = "Run: winget install Git.Git"
    }
}

# Optional tools check
$optionalTools = @{
    "Node.js" = @{
        command = "node"
        args = "--version"
        optional = $true
        installTip = "Run: winget install OpenJS.NodeJS (enables MCP Inspector)"
    }
    "NPM" = @{
        command = "npm"
        args = "--version"
        optional = $true
        installTip = "Installed with Node.js"
    }
    "Docker" = @{
        command = "docker"
        args = "--version"
        optional = $true
        installTip = "Run: winget install Docker.DockerDesktop (enables full containerized stack)"
    }
    "Docker Compose" = @{
        command = "docker-compose"
        args = "--version"
        optional = $true
        installTip = "Installed with Docker Desktop"
    }
}

function Test-Command {
    param(
        [string]$Name,
        [hashtable]$Tool
    )
    
    try {
        $output = & $Tool.command $Tool.args 2>$null
        if ($LASTEXITCODE -eq 0 -and $output) {
            if ($Detailed) {
                $path = (Get-Command $Tool.command -ErrorAction SilentlyContinue).Source
                Write-Success "$Name`: $output"
                if ($path) {
                    Write-Info "    Location: $path"
                }
            } else {
                Write-Success "$Name`: $output"
            }
            return $true
        } else {
            throw "Command failed"
        }
    } catch {
        if ($Tool.optional) {
            Write-Warning "$Name`: Not installed (optional)"
            $script:optionalMissing += $Name
        } else {
            Write-Error "$Name`: Not installed (required)"
            $script:missingRequirements += $Name
        }
        $script:installationTips += "📦 $Name`: $($Tool.installTip)"
        return $false
    }
}

# Check required tools
Write-Host "🔧 Required Tools:" -ForegroundColor Yellow
Write-Host "-" * 20

foreach ($tool in $requiredTools.GetEnumerator()) {
    Test-Command -Name $tool.Key -Tool $tool.Value
}

Write-Host ""

# Check optional tools
Write-Host "🌟 Optional Tools:" -ForegroundColor Yellow
Write-Host "-" * 20

foreach ($tool in $optionalTools.GetEnumerator()) {
    Test-Command -Name $tool.Key -Tool $tool.Value
}

Write-Host ""

# Additional system checks
Write-Host "💻 System Information:" -ForegroundColor Yellow
Write-Host "-" * 20

# PowerShell version
$psVersion = $PSVersionTable.PSVersion
if ($psVersion.Major -ge 5) {
    Write-Success "PowerShell: $psVersion"
} else {
    Write-Warning "PowerShell: $psVersion (version 5.1+ recommended)"
}

# Windows version
$winVersion = [System.Environment]::OSVersion.Version
Write-Info "Windows Version: $winVersion"

# Architecture
$arch = [System.Environment]::Is64BitOperatingSystem ? "64-bit" : "32-bit"
Write-Info "Architecture: $arch"

# Available disk space (current drive)
$drive = Get-PSDrive -Name ($PWD.Drive.Name) -ErrorAction SilentlyContinue
if ($drive) {
    $freeSpaceGB = [math]::Round($drive.Free / 1GB, 2)
    if ($freeSpaceGB -gt 2) {
        Write-Success "Available Disk Space: $freeSpaceGB GB"
    } else {
        Write-Warning "Available Disk Space: $freeSpaceGB GB (low disk space)"
    }
}

Write-Host ""

# Summary
Write-Host "📊 Summary:" -ForegroundColor Yellow
Write-Host "-" * 20

if ($missingRequirements.Count -eq 0) {
    Write-Success "All required prerequisites are installed! 🎉"
    
    if ($optionalMissing.Count -eq 0) {
        Write-Success "All optional tools are also available!"
        Write-Host ""
        Write-Host "🚀 You're ready to run: .\scripts\build_and_run.ps1" -ForegroundColor Green
    } else {
        Write-Info "Some optional tools are missing, but you can still proceed."
        Write-Host ""
        Write-Host "🚀 You can run: .\scripts\build_and_run.ps1" -ForegroundColor Green
        Write-Host "   (Some features like MCP Inspector or Docker stack may not be available)"
    }
} else {
    Write-Error "Missing required prerequisites: $($missingRequirements -join ', ')"
    Write-Host ""
    Write-Host "📋 Installation Commands:" -ForegroundColor Yellow
    Write-Host "-" * 20
    
    foreach ($tip in $installationTips) {
        if ($tip -match "($($missingRequirements | ForEach-Object { [regex]::Escape($_) } | Join-String -Separator '|'))") {
            Write-Host $tip -ForegroundColor Cyan
        }
    }
    
    Write-Host ""
    Write-Host "🎯 Quick Install All (run as Administrator):" -ForegroundColor Yellow
    Write-Host "winget install Python.Python.3.12 astral-sh.uv Git.Git OpenJS.NodeJS Docker.DockerDesktop" -ForegroundColor Cyan
}

if ($optionalMissing.Count -gt 0 -and $missingRequirements.Count -eq 0) {
    Write-Host ""
    Write-Host "🌟 Optional Installation Commands:" -ForegroundColor Yellow
    Write-Host "-" * 20
    
    foreach ($tip in $installationTips) {
        if ($tip -match "($($optionalMissing | ForEach-Object { [regex]::Escape($_) } | Join-String -Separator '|'))") {
            Write-Host $tip -ForegroundColor Cyan
        }
    }
}

Write-Host ""
Write-Host "📚 For detailed installation instructions, see the Prerequisites section in README.md" -ForegroundColor Blue

# Exit with appropriate code
if ($missingRequirements.Count -gt 0) {
    exit 1
} else {
    exit 0
} 