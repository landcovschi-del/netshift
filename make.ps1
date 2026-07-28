<#
.SYNOPSIS
    make replacement for native Windows. GNU make is not available there, and
    the Makefile in this repo relies on bash, so the Windows entry point lives
    here instead.

.EXAMPLE
    .\make.ps1 test
    .\make.ps1 check
    .\make.ps1 up

.NOTES
    Text in this file is deliberately ASCII-only. Windows PowerShell 5.1 reads
    .ps1 files using the system ANSI codepage unless they carry a UTF-8 BOM,
    and a lost BOM turns Cyrillic comments into parser errors. Not worth the
    risk for a task runner.

    If PowerShell refuses to run the script, allow local scripts once:
        Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
    Or bypass for a single run:
        powershell -ExecutionPolicy Bypass -File .\make.ps1 test
#>

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet('help', 'setup', 'up', 'down', 'reset', 'test', 'cov', 'lint',
                 'fmt', 'typecheck', 'check', 'doctor', 'demo', 'clean')]
    [string]$Target = 'help'
)

$ErrorActionPreference = 'Stop'
Set-Location -Path $PSScriptRoot
$env:PYTHONUTF8 = '1'

function Write-Step($text) { Write-Host "==> $text" -ForegroundColor Cyan }
function Write-Ok($text)   { Write-Host "OK  $text" -ForegroundColor Green }
function Write-Bad($text)  { Write-Host "!!  $text" -ForegroundColor Red }

function Assert-Tool($name, $hint) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        Write-Bad "$name not found in PATH. $hint"
        exit 1
    }
}

function Invoke-Checked($label, [scriptblock]$block) {
    Write-Step $label
    & $block
    if ($LASTEXITCODE -ne 0) {
        Write-Bad "$label failed (exit $LASTEXITCODE)"
        exit $LASTEXITCODE
    }
}

switch ($Target) {

    'help' {
        Write-Host ""
        Write-Host "netshift targets" -ForegroundColor White
        Write-Host ""
        $rows = [ordered]@{
            'setup'     = 'create .env and install dependencies'
            'up'        = 'start Postgres and wait until healthy'
            'down'      = 'stop containers (data is kept)'
            'reset'     = 'stop containers and DELETE the data volume'
            'test'      = 'run tests'
            'cov'       = 'run tests with a coverage report'
            'lint'      = 'ruff check'
            'fmt'       = 'ruff format + autofixes'
            'typecheck' = 'mypy in strict mode'
            'check'     = 'lint + typecheck + test - same as CI'
            'doctor'    = 'netshift doctor: environment report'
            'demo'      = 'inspect every file under samples/'
            'clean'     = 'remove caches and build artifacts'
        }
        foreach ($k in $rows.Keys) { "  {0,-10} {1}" -f $k, $rows[$k] | Write-Host }
        Write-Host ""
        Write-Host "  .\make.ps1 <target>" -ForegroundColor DarkGray
        Write-Host ""
    }

    'setup' {
        Assert-Tool 'uv' 'Install it: irm https://astral.sh/uv/install.ps1 | iex'
        if (-not (Test-Path '.env')) {
            Copy-Item '.env.example' '.env'
            Write-Ok '.env created from .env.example - put your keys there'
        } else {
            Write-Ok '.env already exists, leaving it alone'
        }
        Invoke-Checked 'uv sync' { uv sync }
        Write-Ok 'done - now run: .\make.ps1 check'
    }

    'up' {
        Assert-Tool 'docker' 'Install Docker Desktop and make sure it is running.'
        Invoke-Checked 'docker compose up -d' { docker compose up -d }

        Write-Step 'waiting for Postgres to become healthy'
        $deadline = (Get-Date).AddSeconds(90)
        while ($true) {
            $state = docker inspect -f '{{.State.Health.Status}}' netshift-postgres 2>$null
            if ($state -eq 'healthy') { Write-Ok 'Postgres accepts connections'; break }
            if ((Get-Date) -gt $deadline) {
                Write-Bad "timed out (last status: $state)"
                Write-Host 'Logs: docker compose logs postgres' -ForegroundColor DarkGray
                exit 1
            }
            Start-Sleep -Seconds 2
        }
        Write-Host 'Remember to set NETSHIFT_STORE=postgres in .env' -ForegroundColor DarkGray
    }

    'down'  { Invoke-Checked 'docker compose down' { docker compose down } }

    'reset' {
        Write-Host 'This permanently deletes the Postgres data volume.' -ForegroundColor Yellow
        $answer = Read-Host 'Continue? (y/N)'
        if ($answer -ne 'y') { Write-Host 'Cancelled.'; break }
        Invoke-Checked 'docker compose down -v' { docker compose down -v }
    }

    'test'      { Invoke-Checked 'pytest' { uv run pytest } }

    'cov'       { Invoke-Checked 'pytest --cov' {
                    uv run pytest --cov=netshift --cov-report=term-missing
                  } }

    'lint'      { Invoke-Checked 'ruff check' { uv run ruff check . } }

    'fmt'       {
                    Invoke-Checked 'ruff format' { uv run ruff format . }
                    Invoke-Checked 'ruff check --fix' { uv run ruff check --fix . }
                }

    'typecheck' { Invoke-Checked 'mypy' { uv run mypy } }

    'check'     {
                    Invoke-Checked 'ruff check' { uv run ruff check . }
                    Invoke-Checked 'mypy'       { uv run mypy }
                    Invoke-Checked 'pytest'     { uv run pytest }
                    Write-Ok 'all green'
                }

    'doctor'    { uv run netshift doctor }

    'demo'      {
                    foreach ($file in Get-ChildItem 'samples' -Filter '*.csproj') {
                        uv run netshift inspect $file.FullName
                    }
                    # inspect exits 1 when blockers are found; for a demo that is
                    # expected output, not a failure.
                    $global:LASTEXITCODE = 0
                }

    'clean'     {
                    $targets = @('.pytest_cache', '.ruff_cache', '.mypy_cache',
                                 'htmlcov', '.coverage', 'dist', 'build')
                    foreach ($t in $targets) {
                        if (Test-Path $t) { Remove-Item $t -Recurse -Force; Write-Ok "removed $t" }
                    }
                    Get-ChildItem -Recurse -Directory -Filter '__pycache__' -ErrorAction SilentlyContinue |
                        Where-Object { $_.FullName -notmatch '\\\.venv\\' } |
                        ForEach-Object { Remove-Item $_.FullName -Recurse -Force }
                    Write-Ok 'caches cleaned'
                }
}
