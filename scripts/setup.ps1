# ./x.ps1 setup: install the dependencies (pnpm install, uv sync).
$root = Split-Path $PSScriptRoot -Parent

if ($args.Count -gt 0) {
    Write-Host "setup takes no arguments (got: $args)"
    exit 1
}

pnpm --dir $root install
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
uv sync --project $root
exit $LASTEXITCODE
