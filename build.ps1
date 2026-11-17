# Build the branded phone app on your own Windows PC.
# Needs: PowerShell 7, Git, Python 3, Visual Studio 2022 (C++ desktop + MFC/ATL + Windows SDK).
# Optional: Inno Setup 6 for the installer (without it you still get the portable zip).
#   pwsh -File build.ps1            # full build
#   pwsh -File build.ps1 -Clean     # fresh copy of the upstream source first
param([switch]$Clean)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$u = Get-Content upstream.json -Raw | ConvertFrom-Json
$src = Join-Path $PSScriptRoot 'upstream'
$buildRoot = Join-Path $PSScriptRoot 'microsip-build'
function Run([string]$exe, [string[]]$a) { & $exe @a; if ($LASTEXITCODE) { throw "$exe $($a -join ' ') failed" } }

if ($Clean -and (Test-Path $src)) { Remove-Item $src -Recurse -Force }
if (!(Test-Path $src)) {
    Run git @('init', $src)
    Run git @('-C', $src, 'remote', 'add', 'origin', $u.repo)
    Run git @('-C', $src, 'fetch', '--depth', '1', 'origin', $u.commit)
    Run git @('-C', $src, 'checkout', '--detach', 'FETCH_HEAD')
}
Run python @('-m', 'pip', 'install', '--quiet', 'pillow')
Run python @('tools/make_icon.py')
Run python @('tools/brand.py', $src)
& "$src\build-custom.ps1" -BuildRoot $buildRoot
Run python @('tools/package.py', $src, '--build-root', $buildRoot)
Write-Host "`nFinished. Your files are in $PSScriptRoot\dist" -ForegroundColor Green
