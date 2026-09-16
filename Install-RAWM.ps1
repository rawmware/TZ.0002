[CmdletBinding()]
param(
    [ValidateSet('runtime','fast','code','all')]
    [string]$Component = 'all'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$runtimeDir = Join-Path $root 'runtime\llama.cpp'
$modelsDir = Join-Path $root 'models'
New-Item -ItemType Directory -Path $runtimeDir,$modelsDir -Force | Out-Null

function Get-RemoteFile {
    param([string]$Uri, [string]$Destination)
    $partial = "$Destination.partial"
    Write-Host "Downloading $([IO.Path]::GetFileName($Destination))..." -ForegroundColor Cyan
    $downloaded = $false
    if (Get-Command Start-BitsTransfer -ErrorAction SilentlyContinue) {
        try {
            Start-BitsTransfer -Source $Uri -Destination $partial -DisplayName ('RAWM: ' + [IO.Path]::GetFileName($Destination))
            $downloaded = $true
        } catch {
            Write-Warning 'Background transfer failed; trying the standard HTTPS downloader.'
        }
    }
    if (-not $downloaded) {
        $curl = Get-Command curl.exe -ErrorAction SilentlyContinue
        if ($curl) {
            & $curl.Source '--location' '--fail' '--retry' '8' '--retry-all-errors' '--retry-delay' '5' '--continue-at' '-' '--output' $partial $Uri
            if ($LASTEXITCODE -ne 0) { throw "Download failed after retries: $Uri" }
        } else {
            Invoke-WebRequest -Uri $Uri -OutFile $partial -UseBasicParsing
        }
    }
    Move-Item -LiteralPath $partial -Destination $Destination -Force
}

if ($Component -in @('runtime','all') -and -not (Test-Path -LiteralPath (Join-Path $runtimeDir 'llama-server.exe'))) {
    $releases = Invoke-RestMethod -Uri 'https://api.github.com/repos/ggml-org/llama.cpp/releases?per_page=20' -Headers @{ 'User-Agent'='RAWM-Installer' }
    $release = $releases | Where-Object {
        $_.assets | Where-Object { $_.name -match '^llama-.*-bin-win-(cpu-)?x64\.zip$' }
    } | Select-Object -First 1
    $asset = $release.assets | Where-Object { $_.name -match '^llama-.*-bin-win-(cpu-)?x64\.zip$' } | Select-Object -First 1
    if (-not $asset) { throw 'A recent Windows x64 CPU llama.cpp package was not found in the GitHub releases.' }
    $zip = Join-Path $env:TEMP $asset.name
    Get-RemoteFile $asset.browser_download_url $zip
    $extract = Join-Path $env:TEMP ('rawm-llama-' + [guid]::NewGuid().ToString('N'))
    Expand-Archive -LiteralPath $zip -DestinationPath $extract -Force
    $server = Get-ChildItem -LiteralPath $extract -Filter 'llama-server.exe' -Recurse | Select-Object -First 1
    if (-not $server) { throw 'llama-server.exe was not present in the downloaded archive.' }
    Get-ChildItem -LiteralPath $server.DirectoryName -Force | Copy-Item -Destination $runtimeDir -Recurse -Force
    [pscustomobject]@{ release=$release.tag_name; asset=$asset.name; installedAt=(Get-Date).ToString('o') } |
        ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtimeDir 'runtime-manifest.json') -Encoding UTF8
}

if ($Component -in @('fast','all')) {
    $target = Join-Path $modelsDir 'Qwen3.5-0.8B-Q4_K_M.gguf'
    if (-not (Test-Path -LiteralPath $target)) {
        Get-RemoteFile 'https://huggingface.co/notschmee/Qwen3.5-0.8B-GGUF/resolve/main/Qwen3.5-0.8B-Q4_K_M.gguf?download=true' $target
    }
}

if ($Component -in @('code','all')) {
    $target = Join-Path $modelsDir 'Qwen3.5-4B-Q4_K_M.gguf'
    if (-not (Test-Path -LiteralPath $target)) {
        Get-RemoteFile 'https://huggingface.co/bartowski/Qwen_Qwen3.5-4B-GGUF/resolve/main/Qwen_Qwen3.5-4B-Q4_K_M.gguf?download=true' $target
    }
}

Write-Host 'RAWM components installed.' -ForegroundColor Green
