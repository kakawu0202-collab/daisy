' 850 SCOS — DEV silent startup (Ports: Portal 5051 | Engine 8701, isolated from prod 5050/8700)
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
Set ws = CreateObject("WScript.Shell")

' Port overrides so dev never touches the production instances
ws.Environment("PROCESS")("SCOS_PORTAL_PORT") = "5051"
ws.Environment("PROCESS")("SCOS_ENGINE_PORT") = "8701"
ws.Environment("PROCESS")("SCOS_CONTROL_PORT") = "8901"
ws.Environment("PROCESS")("YUMIN_URL") = "http://localhost:5051/sync"

ws.CurrentDirectory = root & "\data-engine"
ws.Run "python main.py --daemon", 0, False

ws.CurrentDirectory = root & "\portal"
ws.Run "python main.py", 0, False
