$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$sandbox = Join-Path $env:RUNNER_TEMP ("generator-python-detection-" + [guid]::NewGuid().ToString("N"))
$fakeBin = Join-Path $sandbox "fake-bin"
$fakeLocalAppData = Join-Path $sandbox "local-app-data"
$fakeTemp = Join-Path $sandbox "temp"
$work = Join-Path $sandbox "work"

New-Item -ItemType Directory -Force -Path $fakeBin, $fakeLocalAppData, $fakeTemp, $work | Out-Null
Copy-Item (Join-Path $repoRoot "start.bat") (Join-Path $work "start.bat")

# Windows' new Python Install Manager can report success even when 3.11 is absent.
# This fake reproduces the exact behavior seen on the user's computer.
@'
@echo off
>&2 echo [ERROR] No runtime installed that matches 3.11. Try running "py install 3.11".
exit /b 0
'@ | Set-Content -Encoding Ascii (Join-Path $fakeBin "py.cmd")

@'
@echo off
exit /b 1
'@ | Set-Content -Encoding Ascii (Join-Path $fakeBin "python.cmd")

$oldPath = $env:PATH
$oldLocalAppData = $env:LOCALAPPDATA
$oldTemp = $env:TEMP
$oldTmp = $env:TMP

try {
    # Keep only the controlled fake commands. Built-in cmd commands still work.
    $env:PATH = $fakeBin
    $env:LOCALAPPDATA = $fakeLocalAppData
    $env:TEMP = $fakeTemp
    $env:TMP = $fakeTemp

    $psi = [System.Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $env:ComSpec
    $psi.WorkingDirectory = $work
    $psi.Arguments = '/D /S /C "echo.| start.bat --setup-only"'
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true

    $process = [System.Diagnostics.Process]::Start($psi)
    $stdout = $process.StandardOutput.ReadToEnd()
    $stderr = $process.StandardError.ReadToEnd()
    $process.WaitForExit()
    $output = $stdout + "`n" + $stderr
}
finally {
    $env:PATH = $oldPath
    $env:LOCALAPPDATA = $oldLocalAppData
    $env:TEMP = $oldTemp
    $env:TMP = $oldTmp
    Remove-Item -Recurse -Force $sandbox -ErrorAction SilentlyContinue
}

if ($output -notmatch [regex]::Escape("[15%] Pobieram zgodny Python 3.11")) {
    throw "Instalator uznal nieistniejacy Python 3.11 za gotowy.`n$output"
}

if ($output -match [regex]::Escape("[25%] Tworze bezpieczne srodowisko")) {
    throw "Instalator probowal utworzyc env nieistniejacym Pythonem.`n$output"
}

Write-Host "OK: brakujacy runtime 3.11 uruchamia automatyczna instalacje Pythona."
