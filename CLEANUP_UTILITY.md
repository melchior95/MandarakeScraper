# Cleanup Utility Documentation

## Overview

The Cleanup Utility helps manage disk space by identifying and removing orphaned files that are no longer needed. It safely deletes old CSVs, image folders, debug outputs, and cache files while **protecting data associated with active configurations and schedules**.

---

## Location

**Advanced Tab** → **Maintenance** → **"Clean Up Orphaned Files..."** button

---

## What Gets Cleaned Up

### 1. **Orphaned CSV Files** 📄
- CSV files in `results/` directory
- No matching config file in `configs/`
- Not referenced by any active schedule

**Example**: If you delete `configs/old_search.json` but `results/old_search.csv` remains, it will be flagged for cleanup.

### 2. **Orphaned Image Folders** 🖼️
- Image folders in `images/` directory
- No matching config file
- Not referenced by any active schedule

**Example**: `images/deleted_config_name/` with hundreds of product images

### 3. **Old Debug Comparison Folders** 🐛
- Debug output folders in `debug_comparison/`
- Older than **7 days**
- Contains image comparison debug output

**Example**: `debug_comparison/Yura_Kano_Photobook_20251004_001049/`

### 4. **Python Cache Folders** 🗑️
- `__pycache__` directories throughout the project
- Can be safely regenerated

### 5. **Old Log Files** 📝
- Log files in root directory (e.g., `mandarake_scraper_20251004.log`)
- Older than **30 days**

---

## Protected Files (NOT Deleted)

The cleanup utility **protects** files associated with:

### ✅ Existing Config Files
- Any config in `configs/*.json`
- Associated CSV in `results/`
- Associated image folder in `images/`

### ✅ Active Scheduled Configs
- Configs referenced in `schedules.json` with `"active": true`
- Even if the config file itself is deleted, the CSV and images are preserved
- Allows you to keep historical comparison data for scheduled searches

**Example**: If you have a daily scheduled search for "Dragon Ball Cards", the cleanup will protect:
- `results/dragon_ball_one_piece_cards_all_stores.csv`
- `images/dragon_ball_one_piece_cards_all_stores/`

Even if you delete the config file, as long as the schedule is active, the data is safe.

---

## How to Use

### 1. **Open Cleanup Dialog**
   - Navigate to **Advanced** tab
   - Click **"Clean Up Orphaned Files..."** button

### 2. **Review Preview**
   - **Summary** section shows quick overview
   - **Detailed Report** lists all files to be deleted
   - Shows total disk space to be freed

### 3. **Confirm or Cancel**
   - Click **"Delete All (X MB)"** to proceed
   - Click **"Cancel"** to exit without changes
   - Confirmation dialog ensures intentional deletion

### 4. **Completion**
   - Success message shows items deleted and space freed
   - Warning message if some files couldn't be deleted

---

## Example Cleanup Report

```
=== Orphaned Files Report ===

ℹ️  Protected 5 config(s) (existing + scheduled)
   CSVs and images for these configs will NOT be deleted.

📄 Orphaned CSV Files (14):
  • all_010801_0.csv (1.2 MB)
  • all_050801_0.csv (856.3 KB)
  • all_700_unknown_store_all.csv (2.1 MB)
  ...

🖼️  Orphaned Image Folders (8):
  • old_search_term/ (127 files)
  • deleted_category/ (45 files)
  ...

🐛 Old Debug Folders (3):
  • Yura_Kano_20251001_123456/ (15 days old)
  • Test_Search_20250920_090000/ (18 days old)
  ...

🗑️  Python Cache Folders (12):
  • gui/__pycache__
  • __pycache__
  ...

📝 Old Log Files (2):
  • mandarake_scraper_20240905.log (90 days old)
  • mandarake_scraper_20240912.log (83 days old)

💾 Total space used: 45.3 MB
```

---

## Safety Features

### 1. **Preview Before Delete**
- Always shows detailed preview
- Lists every file to be deleted
- Shows total space calculation

### 2. **Double Confirmation**
- Preview dialog → "Delete All" button
- Confirmation messagebox with warning

### 3. **Protected Configs**
- Automatically detects active schedules
- Preserves data for scheduled searches
- Console output shows protection status

### 4. **Error Handling**
- Reports success/failure counts
- Continues on individual file errors
- Shows which files couldn't be deleted

---

## Technical Details

### Implementation

**Module**: `gui/cleanup_manager.py`

**Key Methods**:
- `scan_orphaned_files()` - Identifies orphaned files
- `_get_protected_configs()` - Determines which configs to protect
- `calculate_space()` - Calculates disk space usage
- `delete_orphaned_files()` - Performs deletion

### Protection Logic

```python
# Protected configs include:
protected_configs = (
    existing_configs |           # Files in configs/*.json
    active_scheduled_configs     # Configs in schedules.json with active=true
)

# A file is orphaned if:
orphaned = (
    file exists in results/ or images/ AND
    basename NOT IN protected_configs
)
```

### Age Thresholds

| File Type | Age Threshold | Reason |
|-----------|---------------|--------|
| Debug folders | 7 days | Recent comparisons may still be reviewed |
| Log files | 30 days | Retain recent troubleshooting data |
| CSV files | N/A | Based on config existence only |
| Image folders | N/A | Based on config existence only |

---

## When to Run Cleanup

### Recommended Scenarios

1. **After Deleting Multiple Configs**
   - Remove associated CSVs and images
   - Free up significant disk space

2. **Before Archiving Project**
   - Clean up temporary and debug files
   - Reduce project size for backup

3. **Periodic Maintenance**
   - Monthly cleanup of old debug folders
   - Quarterly cleanup of old logs

4. **Low Disk Space**
   - Quick way to identify large orphaned folders
   - Image folders can consume hundreds of MB

### Not Recommended

❌ **Before running scheduled tasks** - Cleanup is schedule-aware, but verify schedules are properly configured

❌ **During active scraping** - Wait for all operations to complete

---

## Troubleshooting

### "No orphaned files found"

✅ **Good!** Everything is clean. Common reasons:
- All configs are still active
- You regularly delete CSVs when deleting configs
- Fresh installation with minimal data

### "Failed to delete X items"

Possible causes:
- **File in use** - Close file viewers or Excel
- **Permission denied** - Run as administrator (rare)
- **Path too long** - Deep nested debug folders (Windows limitation)

**Solution**: Manually delete problematic files or retry after closing applications

### Protected configs not shown correctly

- Check `schedules.json` format is valid
- Verify schedule has `"active": true`
- Look for console output: `[CLEANUP] Protecting scheduled config: ...`

---

## Related Features

- **Config Management** (Stores tab) - Create/delete configs
- **Scheduling** (Stores → Schedules) - Set up automated searches
- **CSV Export** (Search results) - Generate CSV files
- **Image Downloads** (Scraping) - Download product images

---

## Future Enhancements

Potential improvements:
- Configurable age thresholds
- Preview individual category before deletion
- Export cleanup report to file
- Scheduled automatic cleanup
- Recovery/undo feature (trash instead of delete)

---

**Last Updated**: 2025-01-04
**Module**: `gui/cleanup_manager.py`
**Related**: `gui/advanced_tab.py`, `schedules.json`
