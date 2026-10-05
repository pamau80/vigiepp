' Cierra VigiEPP (sin admin)
CreateObject("WScript.Shell").Run "cmd /c """ & CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) & "\portable\run\stop.cmd""", 0, True
