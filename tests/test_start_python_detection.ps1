$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$sandbox = Join-Path $env:RUNNER_TEMP ("generator-python-detection-" + [guid]::NewGuid().ToString("N"))
$fakeBin = Join-Path $sandbox "fake-bin"
$fakeLocalAppData = Join-Path $sandbox "local-app-data"
$fakeTemp = Join-Path $sandbox "temp"
$work = Join-Path $sandbox "work"

New-Item -ItemType Directory -Force -Path $fakeBin, $fakeLocalAppData, $fakeTemp, $work | Out-Null
Copy-Item (Join-Path $repoRoot "start.bat") (Join-Path $work "start.bat")

# Windows' new Python Install Manager can report success even when 3.11 is
# absent. Use a real executable here: calling another .cmd from start.bat
# without `call` transfers control and would make the test stop too early.
$fakePythonSource = @'
using System;

public static class FakePython
{
    public static int Main(string[] args)
    {
        if (args.Length > 0 && args[0].StartsWith("-3.", StringComparison.Ordinal))
        {
            Console.Error.WriteLine("[ERROR] No runtime installed that matches 3.11. Try running \"py install 3.11\".");
            return 0;
        }

        return 1;
    }
}
'@

$fakePythonExe = Join-Path $sandbox "fake-python.exe"
Add-Type -TypeDefinition $fakePythonSource -Language CSharp -OutputAssembly $fakePythonExe -OutputType ConsoleApplication
Copy-Item $fakePythonExe (Join-Path $fakeBin "py.exe")
Copy-Item $fakePythonExe (Join-Path $fakeBin "python.exe")

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
    # Redirect stdin from NUL so a possible `pause` cannot block CI. Running a
    # batch file inside a pipe creates another cmd process and can stop label
    # calls early, which would hide the behavior this regression test targets.
    $psi.Arguments = '/D /S /C "start.bat --setup-only < nul"'
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
