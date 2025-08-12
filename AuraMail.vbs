Set objShell = CreateObject("Wscript.Shell")
objShell.CurrentDirectory = "E:\Projects\EmailAgent"
objShell.Run "cmd /c venv\Scripts\activate.bat && python main.py", 0, True
