# RSS Viewer - Easy Startup Guide 🚀

## 🎨 Create Desktop Shortcut with Icon (One-Time Setup)

**Double-click**: `create_desktop_shortcut.vbs`

This creates a shortcut on your desktop with a **cute orange RSS icon**!

After running this once, you'll have:
- **Desktop icon**: "Mandarake RSS Viewer" with orange RSS logo
- **One-click startup**: Just double-click the desktop icon
- **Auto-opens browser**: No need to manually navigate

---

## Quick Start Options

You now have **3 easy ways** to start the RSS viewer:

### Option 1: Desktop Shortcut ⚡ (Recommended)

**After running** `create_desktop_shortcut.vbs` once:

**What it does:**
- Cute orange RSS icon on your desktop
- Starts the server automatically
- Opens http://localhost:5000 in your browser after 3 seconds
- Runs in the background

**How to use:**
1. Double-click the **"Mandarake RSS Viewer"** icon on your desktop
2. Browser opens automatically after 3 seconds
3. Done! RSS viewer is ready

**To stop:**
- Close the command window that appeared (minimized in taskbar)

---

### Option 2: Simple Start (No Auto-Open)

**File**: `start_rss_viewer.bat`

**What it does:**
- Starts the server
- Shows console output for debugging
- Does NOT auto-open browser

**How to use:**
1. Double-click `start_rss_viewer.bat`
2. Manually open http://localhost:5000
3. Keep console window open

**To stop:**
- Press Ctrl+C in the console window

---

### Option 3: Windows Startup (Auto-start on boot) 🚀

**File**: `start_rss_viewer_silent.vbs`

**What it does:**
- Runs completely silently (no window)
- Starts server in background
- Perfect for Windows startup

**How to set up:**

1. **Press Win+R**, type `shell:startup`, press Enter
2. **Right-click** in the Startup folder → **New** → **Shortcut**
3. **Browse** to:
   ```
   C:\Python Projects\mandarake_scraper\start_rss_viewer_silent.vbs
   ```
4. Click **Next** → Name it "Mandarake RSS Viewer" → Click **Finish**

Now the server will **auto-start** every time Windows boots!

**To stop:**
- Open Task Manager (Ctrl+Shift+Esc)
- Find "python.exe" (command line: rss_web_viewer.py)
- End task

---

## Checking If Server Is Running

**Open Task Manager** (Ctrl+Shift+Esc) → **Details** tab → Look for:
```
python.exe    (Command line: rss_web_viewer.py)
```

If you see it, the server is running at http://localhost:5000

---

## Troubleshooting

### "Port already in use" error

**Problem**: Another instance is already running

**Fix**:
1. Open Task Manager
2. Find all `python.exe` processes
3. End the one running `rss_web_viewer.py`
4. Try starting again

### Server not accessible

**Check**:
1. Is python.exe running in Task Manager?
2. Try http://127.0.0.1:5000 instead of localhost
3. Check Windows Firewall settings

### Browser doesn't open automatically

**Fix**:
- Manually navigate to http://localhost:5000
- The server is still running even if browser didn't open

---

## Recommended Setup

**For daily use:**
1. Use `start_rss_viewer_and_open.bat` when you want to browse
2. Or set up Windows Startup for always-on access

**For development:**
1. Use `start_rss_viewer.bat` to see console output
2. Keep console window open to see RSS fetch logs

---

## File Summary

| File | Purpose | Opens Browser? | Shows Console? |
|------|---------|----------------|----------------|
| `start_rss_viewer_and_open.bat` | Quick start | ✅ Yes (auto) | ❌ No (minimized) |
| `start_rss_viewer.bat` | Debug mode | ❌ No | ✅ Yes |
| `start_rss_viewer_silent.vbs` | Background/Startup | ❌ No | ❌ No (silent) |

---

## URLs

- **RSS Viewer**: http://localhost:5000
- **Alternative**: http://127.0.0.1:5000

Both URLs work the same - use whichever you prefer!

---

**Last Updated**: October 10, 2025
**Status**: ✅ Ready to use
