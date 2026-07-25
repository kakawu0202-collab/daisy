' 850 Toolbox — 静默启动（无命令行窗口）
' 双击此文件，server 在后台运行，看不到黑窗口
CreateObject("WScript.Shell").Run "cmd /c cd /d d:\workspace\850-toolbox && python server.py", 0, False
