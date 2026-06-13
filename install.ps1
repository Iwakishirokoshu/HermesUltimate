param(
    [ValidateSet("local", "vps")]
    [string]$Mode = "vps",

    [ValidateSet("slim", "full", "ultra-slim")]
    [string]$Profile = "slim",

    [string]$VncPassword = $env:VNC_PASSWORD,
    [switch]$WithSecondBot,
    [string]$VaultPath = $(Join-Path $HOME "HermesVault"),
    [string]$RepoUrl = $env:HERMES_REPO_URL,
    [string]$Branch = $(if ($env:HERMES_BRANCH) { $env:HERMES_BRANCH } else { "main" }),
    [switch]$NonInteractive,
    [switch]$Help
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$InstallDir = if ($env:HERMES_INSTALL_DIR) {
    $env:HERMES_INSTALL_DIR
} else {
    Join-Path $env:ProgramData "HermesUltimate\repo"
}

function Write-Usage {
    @"
Hermes Ultimate Windows installer

Usage:
  powershell -ExecutionPolicy Bypass -File install.ps1 [options]

Options:
  -Mode local|vps
  -Profile slim|full|ultra-slim
  -VncPassword <pw>
  -WithSecondBot
  -VaultPath <path>
  -RepoUrl <url>
  -Branch <name>
  -NonInteractive
  -Help
"@ | Write-Host
}

function Write-Step {
    param([string]$Message)
    Write-Host "[hermes-install] $Message"
}

function Write-Warn {
    param([string]$Message)
    Write-Warning "[hermes-install] $Message"
}

function Assert-Command {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Install-WingetPackage {
    param(
        [string]$Id,
        [string]$CommandName
    )
    if ($CommandName -and (Assert-Command $CommandName)) {
        return
    }
    if (-not (Assert-Command "winget")) {
        throw "winget is required to install $Id"
    }
    Write-Step "installing $Id via winget"
    winget install --id $Id -e --accept-package-agreements --accept-source-agreements
}

function Add-CommonPathEntries {
    $paths = @(
        "$env:USERPROFILE\.cargo\bin",
        "$env:USERPROFILE\.local\bin",
        "$env:ProgramFiles\Git\cmd",
        "$env:ProgramFiles\Git\bin",
        "$env:ProgramFiles\Docker\Docker\resources\bin",
        "$env:ProgramFiles\nodejs",
        "$env:LOCALAPPDATA\Programs\Python\Python311",
        "$env:LOCALAPPDATA\Programs\Python\Python311\Scripts"
    )
    foreach ($path in $paths) {
        if ((Test-Path $path) -and ($env:Path -notlike "*$path*")) {
            $env:Path = "$path;$env:Path"
        }
    }
}

function Install-Uv {
    if (Assert-Command "uv") {
        return
    }
    Write-Step "installing uv"
    powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    Add-CommonPathEntries
    if (-not (Assert-Command "uv")) {
        throw "uv is not available after install"
    }
}

function Install-Dependencies {
    Install-WingetPackage -Id "Git.Git" -CommandName "git"
    Install-WingetPackage -Id "Python.Python.3.11" -CommandName "python"
    Install-WingetPackage -Id "OpenJS.NodeJS.LTS" -CommandName "node"
    Install-WingetPackage -Id "Docker.DockerDesktop" -CommandName "docker"
    Install-WingetPackage -Id "BurntSushi.ripgrep.MSVC" -CommandName "rg"
    Install-WingetPackage -Id "Gyan.FFmpeg" -CommandName "ffmpeg"
    Install-WingetPackage -Id "jqlang.jq" -CommandName "jq"
    Add-CommonPathEntries
    Install-Uv
    if (-not (Assert-Command "docker")) {
        throw "Docker Desktop is not available. Install/start Docker Desktop and rerun."
    }
    docker compose version | Out-Null
}

function Find-GitBash {
    $candidates = @(
        "$env:ProgramFiles\Git\bin\bash.exe",
        "$env:ProgramFiles\Git\usr\bin\bash.exe",
        "${env:ProgramFiles(x86)}\Git\bin\bash.exe"
    )
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            return $candidate
        }
    }
    $cmd = Get-Command "bash.exe" -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }
    throw "Git Bash was not found"
}

function Convert-ToBashPath {
    param(
        [string]$Path,
        [string]$Bash
    )
    $escaped = $Path.Replace("'", "'\''")
    (& $Bash -lc "cygpath -u '$escaped'").Trim()
}

function Quote-Bash {
    param([string]$Value)
    "'" + $Value.Replace("'", "'\''") + "'"
}

function Invoke-BashInRepo {
    param(
        [string]$Command
    )
    $bash = Find-GitBash
    $repoPath = Convert-ToBashPath -Path $script:RepoRoot -Bash $bash
    & $bash -lc "cd $(Quote-Bash $repoPath) && $Command"
}

function Resolve-RepoRoot {
    $current = (Get-Location).Path
    if ($Mode -eq "local" -and (Test-Path (Join-Path $current "pyproject.toml")) -and (Test-Path (Join-Path $current "stack"))) {
        return $current
    }
    if ($Mode -eq "local" -and (Test-Path (Join-Path $PSScriptRoot "pyproject.toml")) -and (Test-Path (Join-Path $PSScriptRoot "stack"))) {
        return $PSScriptRoot
    }
    if (-not $RepoUrl -and (Test-Path (Join-Path $PSScriptRoot ".git"))) {
        $detected = git -C $PSScriptRoot config --get remote.origin.url
        if ($detected) {
            $script:RepoUrl = $detected
        }
    }
    if (-not $script:RepoUrl) {
        throw "RepoUrl is required for vps mode. Pass -RepoUrl or set HERMES_REPO_URL."
    }

    if (Test-Path (Join-Path $InstallDir ".git")) {
        Write-Step "updating existing checkout: $InstallDir"
        git -C $InstallDir fetch origin $Branch
        git -C $InstallDir checkout $Branch
        git -C $InstallDir pull --ff-only origin $Branch
        return $InstallDir
    }

    if (Test-Path $InstallDir) {
        throw "$InstallDir exists but is not a git checkout"
    }

    Write-Step "cloning $script:RepoUrl#$Branch into $InstallDir"
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $InstallDir) | Out-Null
    git clone --branch $Branch $script:RepoUrl $InstallDir
    return $InstallDir
}

function Install-HermesNative {
    Write-Step "installing Hermes Python package natively"
    Push-Location $script:RepoRoot
    try {
        uv venv --python 3.11
        uv pip install -e ".[all]"
    } finally {
        Pop-Location
    }
}

function Initialize-Dirs {
    Write-Step "initializing user directories"
    $hermesHome = Join-Path $HOME ".hermes"
    foreach ($path in @($hermesHome, $VaultPath, (Join-Path $hermesHome "browser-profiles"), (Join-Path $hermesHome "souls"), (Join-Path $hermesHome "logs"))) {
        New-Item -ItemType Directory -Force -Path $path | Out-Null
    }
    $soulsTarget = Join-Path $hermesHome "souls"
    if (-not (Get-ChildItem -Path $soulsTarget -Filter "*.yaml" -ErrorAction SilentlyContinue)) {
        Copy-Item -Path (Join-Path $script:RepoRoot "souls\*.yaml") -Destination $soulsTarget -Force
    }
}

function Initialize-Vault {
    $bash = Find-GitBash
    $vaultBash = Convert-ToBashPath -Path $VaultPath -Bash $bash
    Invoke-BashInRepo "HERMES_VAULT_PATH=$(Quote-Bash $vaultBash) bash scripts/init-vault.sh"
}

function Generate-Env {
    $vaultForCompose = $VaultPath.Replace("\", "/")
    $vnc = if ($VncPassword) { $VncPassword } else { [System.Guid]::NewGuid().ToString("N").Substring(0, 24) }
    $script:ResolvedVncPassword = $vnc
    Invoke-BashInRepo "HERMES_VAULT_PATH=$(Quote-Bash $vaultForCompose) VNC_PASSWORD=$(Quote-Bash $vnc) bash scripts/gen-env.sh"
}

function Compose-Args {
    $args = @("-f", "stack/docker-compose.yml")
    switch ($Profile) {
        "slim" { $args += @("-f", "stack/docker-compose.decepticon-slim.yml") }
        "full" {
            if (Test-Path (Join-Path $script:RepoRoot "stack/docker-compose.decepticon-full.yml")) {
                $args += @("-f", "stack/docker-compose.decepticon-full.yml")
            } else {
                Write-Warn "full profile compose file is not present; using slim profile"
                $args += @("-f", "stack/docker-compose.decepticon-slim.yml")
            }
        }
        "ultra-slim" { }
    }
    $args
}

function Start-Stack {
    Write-Step "starting Docker stack with profile '$Profile'"
    Push-Location $script:RepoRoot
    try {
        $composeArgs = @()
        $composeArgs += Compose-Args
        $composeArgs += @("up", "-d")
        docker compose @composeArgs
    } finally {
        Pop-Location
    }
}

function Wait-Url {
    param(
        [string]$Name,
        [string[]]$Urls,
        [int]$TimeoutSeconds = 120
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        foreach ($url in $Urls) {
            try {
                Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 5 | Out-Null
                Write-Step "$Name is ready at $url"
                return
            } catch {
                Start-Sleep -Seconds 2
            }
        }
    }
    throw "$Name did not become healthy"
}

function Wait-Healthy {
    Wait-Url -Name "9router" -Urls @("http://localhost:20128/health", "http://localhost:20128/api/health", "http://localhost:20128")
    Wait-Url -Name "vault-api" -Urls @("http://localhost:8090/health")
    Wait-Url -Name "vnc-cloak" -Urls @("http://localhost:6080", "http://localhost:9222/json/version")
    if ($Profile -ne "ultra-slim") {
        Wait-Url -Name "langgraph" -Urls @("http://localhost:2024/health")
        Wait-Url -Name "neo4j" -Urls @("http://localhost:7474")
    }
}

function Start-Dashboard {
    try {
        Invoke-WebRequest -UseBasicParsing -Uri "http://localhost:8080/api/status" -TimeoutSec 3 | Out-Null
        Write-Step "dashboard already responds on http://localhost:8080"
        return
    } catch {
    }
    $hermes = Join-Path $script:RepoRoot ".venv\Scripts\hermes.exe"
    if (-not (Test-Path $hermes)) {
        throw "Hermes executable not found at $hermes"
    }
    $logs = Join-Path $HOME ".hermes\logs"
    New-Item -ItemType Directory -Force -Path $logs | Out-Null
    $logPath = Join-Path $logs "dashboard.log"
    $errPath = Join-Path $logs "dashboard.err.log"
    Write-Step "starting Hermes dashboard on http://localhost:8080"
    Start-Process -FilePath $hermes -ArgumentList @("dashboard", "--host", "0.0.0.0", "--port", "8080", "--no-open", "--skip-build") -RedirectStandardOutput $logPath -RedirectStandardError $errPath -WindowStyle Hidden
    Wait-Url -Name "dashboard" -Urls @("http://localhost:8080/api/status", "http://localhost:8080")
}

function Invoke-Wizard {
    if ($NonInteractive) {
        Write-Step "non-interactive mode: skipping post-install wizard"
        return
    }
    $flag = if ($WithSecondBot) { "--with-second-bot" } else { "" }
    Invoke-BashInRepo "bash scripts/post-install-wizard.sh $flag"
}

function Write-Summary {
    @"

Hermes Ultimate install complete.

Dashboard:      http://localhost:8080
9router:        http://localhost:20128
VNC noVNC:      http://localhost:6080
LangGraph:      http://localhost:2024
Vault path:     $VaultPath
Install dir:    $script:RepoRoot
Logs:           $(Join-Path $HOME ".hermes\logs")

VNC password:   $script:ResolvedVncPassword
"@ | Write-Host
}

if ($Help) {
    Write-Usage
    exit 0
}

$script:RepoUrl = $RepoUrl
$script:ResolvedVncPassword = $VncPassword
Install-Dependencies
$script:RepoRoot = Resolve-RepoRoot
Install-HermesNative
Initialize-Dirs
Initialize-Vault
Generate-Env
Start-Stack
Wait-Healthy
Start-Dashboard
Invoke-Wizard
Write-Summary
