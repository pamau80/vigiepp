' VigiEPP — doble clic para abrir (sin ventana negra, sin admin)
Option Explicit

Dim sh, fso, root, i

Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
root = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = root

If Not fso.FileExists(root & "\portable\runtime\python\python.exe") Then
    MsgBox "Paquete incompleto." & vbCrLf & vbCrLf & "Descargue VigiEPP.exe (archivo unico) desde GitHub Actions.", vbCritical, "VigiEPP"
    WScript.Quit 1
End If

If VigieppUp() Then
    sh.Run "http://127.0.0.1:8000/", 1, False
    WScript.Quit 0
End If

sh.Run "cmd /c """ & root & "\portable\run\launch.cmd""", 0, False

For i = 1 To 90
    WScript.Sleep 1000
    If VigieppUp() Then
        sh.Run "http://127.0.0.1:8000/", 1, False
        WScript.Quit 0
    End If
Next

MsgBox "VigiEPP no pudo iniciar." & vbCrLf & "Revise portable\logs\", vbExclamation, "VigiEPP"

Function VigieppUp()
    On Error Resume Next
    Dim x
    Set x = CreateObject("MSXML2.ServerXMLHTTP.6.0")
    x.open "GET", "http://127.0.0.1:8000/api/health", False
    x.setTimeouts 2000, 2000, 2000, 2000
    x.send
    VigieppUp = (Err.Number = 0 And x.Status = 200)
End Function
