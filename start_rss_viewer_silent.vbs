Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Python Projects\mandarake_scraper"
WshShell.Run "venv\Scripts\python.exe ""archive\yahoo_auction\rss_web_viewer.py""", 0, False
Set WshShell = Nothing
