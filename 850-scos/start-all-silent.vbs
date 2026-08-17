Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
Set ws = CreateObject("WScript.Shell")

ws.CurrentDirectory = root & "\data-engine"
ws.Run "python main.py --daemon", 0, False

ws.CurrentDirectory = root & "\portal"
ws.Run "python main.py", 0, False
