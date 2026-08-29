Option Explicit

Dim shell, files, folder, appFolder, command, exitCode, logPath
Set shell = CreateObject("WScript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")

folder = files.GetParentFolderName(WScript.ScriptFullName)
appFolder = folder & "\app"
logPath = appFolder & "\floppyverse-launch.log"

command = "cmd.exe /d /s /c ""cd /d """ & appFolder & """" & _
    " && if not exist "".venv\Scripts\pythonw.exe"" (" & _
    " (py -3 -m venv .venv 2>nul || python -m venv .venv)" & _
    " && "".venv\Scripts\python.exe"" -m pip install -r requirements.txt" & _
    ")" & _
    " && "".venv\Scripts\pythonw.exe"" -m floppyverse" & _
    " 1>""" & logPath & """ 2>&1"""

' Window style 0 keeps the command prompt completely hidden. Wait so failures can be reported.
exitCode = shell.Run(command, 0, True)

If exitCode <> 0 Then
    MsgBox "Floppyverse could not start. Details were saved to:" & vbCrLf & logPath, _
           vbExclamation, "Floppyverse Book Search"
End If
