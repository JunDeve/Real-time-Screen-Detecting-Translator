' 터미널 창 없이 백그라운드로 실행
Dim shell
Set shell = CreateObject("WScript.Shell")
shell.Run "cmd /c cd /d """ & CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) & """ && python main.py", 0, False
Set shell = Nothing
