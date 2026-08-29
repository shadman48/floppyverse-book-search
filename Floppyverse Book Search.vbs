Option Explicit

Dim shell, files, folder, appFolder, command, exitCode, logPath
Set shell = CreateObject("WScript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")

folder = files.GetParentFolderName(WScript.ScriptFullName)
appFolder = folder & "\app"
logPath = appFolder & "\floppyverse-launch.log"
command = Chr(34) & appFolder & "\launch.cmd" & Chr(34)

' Window style 0 keeps the internal command launcher completely hidden.
exitCode = shell.Run(command, 0, True)

If exitCode <> 0 Then
    MsgBox "Floppyverse could not start. Details were saved to:" & vbCrLf & logPath, _
           vbExclamation, "Floppyverse Book Search"
End If

