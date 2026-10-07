# ./x.ps1 clean: delete dist/, .cache/, .venv/, every __pycache__/ under src/
# and scripts/, and node_modules/ (via pnpm clean).
$root = Split-Path $PSScriptRoot -Parent

if ($args.Count -gt 0) {
    Write-Host "clean takes no arguments (got: $args)"
    exit 1
}

$dirs = @("dist", ".cache", ".venv")
foreach ($tree in "src", "scripts") {
    $dirs += Get-ChildItem -Path (Join-Path $root $tree) -Directory -Recurse -Force -Filter __pycache__ -ErrorAction SilentlyContinue |
        ForEach-Object { $_.FullName.Substring($root.Length + 1).Replace("\", "/") }
}
foreach ($dir in $dirs) {
    $path = Join-Path $root $dir
    if (Test-Path $path) {
        Write-Host "Removing $dir"
        try {
            Remove-Item -Recurse -Force $path -ErrorAction Stop
        } catch {
            Write-Host "could not delete ${path}: $_"
            exit 1
        }
    }
}
pnpm --dir $root clean
exit $LASTEXITCODE
