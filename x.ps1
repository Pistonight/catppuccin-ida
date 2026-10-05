# ./x.ps1 <script> [args...]  ->  uv run scripts/<script>.py [args...]
$root = $PSScriptRoot
$scripts = Join-Path $root "scripts"

function Show-Scripts {
    Write-Host "usage: ./x <script> [args...]"
    Write-Host "scripts:"
    Get-ChildItem -Path $scripts -Filter *.py | ForEach-Object { Write-Host "  $($_.BaseName)" }
}

if ($args.Count -eq 0) {
    Show-Scripts
    exit 1
}

$name = $args[0]
$rest = @($args | Select-Object -Skip 1)
$path = Join-Path $scripts "$name.py"
if (-not (Test-Path $path -PathType Leaf)) {
    Write-Host "no such script: $name"
    Show-Scripts
    exit 1
}

uv run --project $root $path @rest
exit $LASTEXITCODE
