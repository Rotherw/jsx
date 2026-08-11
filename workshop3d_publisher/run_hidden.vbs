Option Explicit

' Start the normal launcher with no console window and no browser tab.  The
' dashboard remains available at http://127.0.0.1:5000 when the user wants it.
Dim shell, fso, appDir, command
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
appDir = fso.GetParentFolderName(WScript.ScriptFullName)
command = "cmd.exe /d /c " & Chr(34) & Chr(34) & appDir & _
          "\run.bat" & Chr(34) & " --no-browser" & Chr(34)
shell.Run command, 0, False
