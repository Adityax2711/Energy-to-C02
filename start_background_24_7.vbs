' Silent Background 24/7 Launcher for Energy-to-CO2 Engine
Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)

' Run python uvicorn silently in background (0 = hide window, false = do not wait)
WshShell.CurrentDirectory = currentDir
WshShell.Run """" & currentDir & "\.venv\Scripts\python.exe"" -m uvicorn app.main:app --host 0.0.0.0 --port 8000", 0, False

WScript.Echo "Energy-to-CO2 Translation Engine is now running 24/7 in the background!" & vbCrLf & vbCrLf & _
             "Dashboard:     http://localhost:8000" & vbCrLf & _
             "OpenAPI Docs:  http://localhost:8000/docs" & vbCrLf & _
             "Metrics:       http://localhost:8000/metrics" & vbCrLf & vbCrLf & _
             "To stop it anytime, run stop_server.bat"
