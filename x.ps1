# ./x <script> [args...] [<script> [args...]]...
#   ->  scripts/<script>.ps1 [args...] if that exists, else
#       uv run scripts/<script>.py [args...]; for each script in order,
#       stopping at the first one that fails.
# An argument that names a script starts the next step; any other argument
# goes to the script before it.
$root = $PSScriptRoot
$scripts = Join-Path $root "scripts"

function Show-Scripts {
    Write-Host "usage: ./x <script> [args...] [<script> [args...]]..."
    Write-Host "scripts:"
    Get-ChildItem -Path $scripts -File | Where-Object { $_.Extension -in ".ps1", ".py" } |
        ForEach-Object { $_.BaseName } | Sort-Object -Unique | ForEach-Object { Write-Host "  $_" }
}

# scripts/<name>.ps1 or scripts/<name>.py (in that order of preference), or $null
function Get-ScriptPath($name) {
    if (-not $name -or $name -match '[\\/]') { return $null }
    foreach ($ext in ".ps1", ".py") {
        $path = Join-Path $scripts "$name$ext"
        if (Test-Path $path -PathType Leaf) { return $path }
    }
    return $null
}

function Test-Script($name) {
    $null -ne (Get-ScriptPath $name)
}

if ($args.Count -eq 0) {
    Show-Scripts
    exit 1
}
if (-not (Test-Script $args[0])) {
    Write-Host "no such script: $($args[0])"
    Show-Scripts
    exit 1
}

# [(script, [args])], in order
$steps = @()
foreach ($a in $args) {
    if (Test-Script $a) {
        $steps += , @{ Name = $a; Args = @() }
    } else {
        $steps[-1].Args += , $a
    }
}

foreach ($step in $steps) {
    if ($steps.Count -gt 1) { Write-Host "==> $($step.Name)" }
    $rest = $step.Args
    $path = Get-ScriptPath $step.Name
    if ($path.EndsWith(".ps1")) {
        $global:LASTEXITCODE = 0
        try {
            & $path @rest
            $ok = $?
            $status = if ($LASTEXITCODE) { $LASTEXITCODE } elseif ($ok) { 0 } else { 1 }
        } catch {
            Write-Host $_
            $status = 1
        }
    } else {
        uv run --project $root $path @rest
        $status = $LASTEXITCODE
    }
    if ($status -ne 0) {
        if ($steps.Count -gt 1) { Write-Host "==> $($step.Name) failed (exit $status); stopping" }
        exit $status
    }
}
exit 0
