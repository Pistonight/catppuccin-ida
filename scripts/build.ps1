# ./x.ps1 build: the full build. Runs check-css, build-css, build-icons, then
# build-py; stops at the first failure.
$root = Split-Path $PSScriptRoot -Parent

if ($args.Count -gt 0) {
    Write-Host "build takes no arguments (got: $args)"
    exit 1
}

& (Join-Path $root "x.ps1") check-css build-css build-icons build-py
exit $LASTEXITCODE
