# Phase 6 Implementation Plan - Config Tree Manager

## Current Status

**After Phase 5:**
- gui_config.py: **3405 lines**
- Removed: 2005 lines (37.0% from original 5410)
- Target: <2000 lines
- **Remaining: 1405 lines to remove (41.2%)**

## Phase 6 Overview

**Goal**: Extract Config Tree Manager (~360 lines)
**Estimated Time**: 3-4 hours
**Complexity**: Medium-High (tree widgets, drag-drop, dialogs)
**Impact**: High (11% reduction)

## Methods to Extract

### Located in gui_config.py lines ~1926-2286

1. **_filter_config_tree()** (lines 1931-1954) - ~24 lines
   - Filters config tree based on store selection
   - Uses self.config_store_filter, self.config_tree, self.config_paths

2. **_setup_column_drag()** (lines 1956-1986) - ~31 lines
   - Enables drag-to-reorder for treeview columns
   - Binds mouse events for drag operations
   - Generic utility, could be in utils

3. **_reorder_columns()** (lines 1988-2024) - ~37 lines
   - Reorders treeview columns
   - Preserves headings, widths, settings
   - Generic utility, could be in utils

4. **_show_config_tree_menu()** (lines 2053-2061) - ~9 lines
   - Shows context menu on config tree right-click
   - Selects item under cursor

5. **_edit_category_from_menu()** (lines 2063-2101) - ~39 lines
   - Edits category name from right-click menu
   - Loads config, shows edit dialog

6. **_show_edit_category_dialog()** (lines 2103-2200+) - ~100+ lines
   - Shows dialog to edit/add category name
   - Complex UI construction
   - Form validation and saving

7. **_on_config_tree_double_click()** (lines 2206-2244+) - ~40+ lines
   - Handles double-click on config tree
   - Loads config or shows edit dialog

8. **_load_csv_from_config()** (lines 2245-2285+) - ~40+ lines
   - Loads CSV file from selected config
   - Updates UI with CSV data

9. **_autofill_search_query_from_config()** (lines 2286+) - ~30+ lines
   - Autofills eBay search from config keyword

**Total: ~360 lines**

## Implementation Strategy

### Step 1: Create Config Tree Manager Module

Create `gui/config_tree_manager.py` with:

```python
class ConfigTreeManager:
    """Manager for configuration tree widget operations."""

    def __init__(self, tree_widget, config_paths, main_window):
        self.tree = tree_widget
        self.config_paths = config_paths
        self.main = main_window

    def filter_tree(self, filter_value):
        """Filter tree based on store selection"""
        # Implementation from _filter_config_tree

    def setup_column_drag(self):
        """Enable column drag-to-reorder"""
        # Implementation from _setup_column_drag

    def reorder_columns(self, src_col, dst_col):
        """Reorder columns"""
        # Implementation from _reorder_columns

    def show_context_menu(self, event, menu):
        """Show context menu"""
        # Implementation from _show_config_tree_menu

    def edit_category_from_menu(self):
        """Edit category via right-click menu"""
        # Implementation from _edit_category_from_menu

    def show_edit_category_dialog(self, config_path, config, category_code, store, event):
        """Show category edit dialog"""
        # Implementation from _show_edit_category_dialog

    def on_double_click(self, event):
        """Handle tree double-click"""
        # Implementation from _on_config_tree_double_click

    def load_csv_from_config(self):
        """Load CSV from selected config"""
        # Implementation from _load_csv_from_config

    def autofill_search_query(self, config):
        """Autofill eBay search from config"""
        # Implementation from _autofill_search_query_from_config
```

### Step 2: Integrate into gui_config.py

1. **Import**: `from gui.config_tree_manager import ConfigTreeManager`

2. **Initialize** in `_build_widgets()` after config tree creation:
   ```python
   self.config_tree_manager = ConfigTreeManager(
       self.config_tree,
       self.config_paths,
       self
   )
   ```

3. **Replace method calls**:
   - `self._filter_config_tree()` → `self.config_tree_manager.filter_tree(filter_value)`
   - `self._setup_column_drag(tree)` → `self.config_tree_manager.setup_column_drag(tree)`
   - etc.

4. **Update bindings**:
   - Right-click menu command → `self.config_tree_manager.edit_category_from_menu`
   - Double-click binding → `self.config_tree_manager.on_double_click`

### Step 3: Testing

1. Test config tree filtering by store
2. Test column drag-to-reorder
3. Test right-click menu → edit category
4. Test double-click to load config
5. Test CSV loading from config
6. Test autofill search from config

## Challenges & Considerations

### 1. Widget References
Many methods access:
- `self.config_tree`
- `self.config_paths`
- `self.config_store_filter`
- Various UI widgets

**Solution**: Pass main_window reference, access via `self.main.widget_name`

### 2. Dialog Positioning
`_show_edit_category_dialog()` creates Toplevel dialog with specific positioning

**Solution**: Dialog creation stays in manager, positioned relative to main window

### 3. CSV Manager Integration
`_load_csv_from_config()` calls CSV comparison manager methods

**Solution**: Access via `self.main.csv_comparison_manager` or pass as dependency

### 4. Event Binding
Several methods are bound to tree events

**Solution**: Manager methods can be bound directly:
```python
self.config_tree.bind('<Double-1>', self.config_tree_manager.on_double_click)
```

## Alternative: Incremental Extraction

If full extraction is too complex, extract in phases:

**Phase 6a**: Column drag utilities (~70 lines)
- Extract `_setup_column_drag()` and `_reorder_columns()` to `gui/utils.py`
- These are generic utilities, not config-tree specific

**Phase 6b**: Dialog methods (~150 lines)
- Extract category edit dialog to separate module
- Create `gui/category_dialog.py`

**Phase 6c**: Tree operations (~140 lines)
- Extract remaining tree operations
- Create minimal ConfigTreeManager

**Total**: Same ~360 lines, but less risky

## Expected Results

After Phase 6 complete:
- **gui_config.py: 3405 → 3045 lines** (-360 lines, -10.6%)
- **Total removed: 2365 lines** (43.7% from original)
- **Remaining to target: 1045 lines** (30.7%)

## Next Steps After Phase 6

From PHASE_5_AUDIT.md recommendations:

**Phase 7**: Extract Worker Coordinator (~350 lines) → 2695 lines
**Phase 8**: Extract Results Manager (~150 lines) → 2545 lines
**Phase 9**: Extract Settings Manager (~200 lines) → 2345 lines
**Phase 10**: Cleanup & Optimization (~345 lines) → **~2000 lines** ✅

**Total remaining effort**: 5-8 hours across 5 phases

## Summary

Phase 6 is the most complex extraction so far due to:
- Tree widget event handling
- Drag-and-drop operations
- Dialog management
- Multiple widget interactions

**Recommendation**:
- Allocate 3-4 hours for careful implementation
- Test thoroughly after each method extraction
- Consider incremental approach if full extraction is too risky

**Priority**: High - This is the largest remaining extraction opportunity

