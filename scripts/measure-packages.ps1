# Measures each package directory's disk usage in the project's Python venv
# site-packages folder. Writes raw robocopy output to scripts/packages_raw.txt,
# then invokes scripts/sort_packages.py to produce scripts/packages_sorted.md.
#
# Usage (from anywhere):
#   powershell -ExecutionPolicy Bypass -File scripts/measure-packages.ps1
#   pwsh -File scripts/measure-packages.ps1

$ErrorActionPreference = "Stop"

$ScriptDir   = $PSScriptRoot
$ProjectRoot = Split-Path -Parent $ScriptDir

Push-Location $ProjectRoot
try {
    if (Test-Path ".\.venv\Lib\site-packages") {
        $VenvDir = ".\.venv"
    } elseif (Test-Path ".\venv\Lib\site-packages") {
        $VenvDir = ".\venv"
    } else {
        Write-Host "[Error] No venv found. Expected .\.venv\Lib\site-packages or .\venv\Lib\site-packages." -ForegroundColor Red
        exit 1
    }

    $SitePackages = Join-Path $VenvDir "Lib\site-packages"
    $RawFile      = Join-Path $ScriptDir "packages_raw.txt"
    $SortScript   = Join-Path $ScriptDir "sort_packages.py"

    Write-Host "[Symphony] Measuring package sizes in $SitePackages ..."

    $lines = foreach ($d in (Get-ChildItem $SitePackages -Directory)) {
        $size = (robocopy $d.FullName NULL /L /E /BYTES /NFL /NDL /NJH | Select-String "Bytes :").ToString()
        "$($d.Name): $size"
    }

    $lines | Set-Content -Path $RawFile -Encoding ascii

    Write-Host "[Symphony] Wrote raw sizes to $RawFile"
    Write-Host "[Symphony] Sorting via sort_packages.py..."

    $VenvPython = Join-Path $VenvDir "Scripts\python.exe"
    if (Test-Path $VenvPython) {
        & $VenvPython $SortScript
    } else {
        python $SortScript
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[Error] sort_packages.py failed with exit code $LASTEXITCODE." -ForegroundColor Red
        exit $LASTEXITCODE
    }

    Write-Host "[Done] Sorted package sizes written to scripts/packages_sorted.md."
}
finally {
    Pop-Location
}
