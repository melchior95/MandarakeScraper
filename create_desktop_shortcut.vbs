Set WshShell = WScript.CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' Get current directory
strCurrentDir = objFSO.GetParentFolderName(WScript.ScriptFullName)

' Create shortcut on desktop
strDesktop = WshShell.SpecialFolders("Desktop")
Set objShortcut = WshShell.CreateShortcut(strDesktop & "\Mandarake RSS Viewer.lnk")

' Set shortcut properties
objShortcut.TargetPath = strCurrentDir & "\start_rss_viewer_and_open.bat"
objShortcut.WorkingDirectory = strCurrentDir
objShortcut.IconLocation = strCurrentDir & "\rss_viewer_icon.ico"
objShortcut.Description = "Start Mandarake RSS Viewer"
objShortcut.Save

WScript.Echo "Desktop shortcut created successfully!" & vbCrLf & vbCrLf & "Look for 'Mandarake RSS Viewer' on your desktop with the orange RSS icon!"
