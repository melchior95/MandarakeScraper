# Final Modularization Plan - Phases 4-6

## Current Status
- **gui_config.py**: 4,880 lines (still too large)
- **Completed modules**: 8 modular managers from Phase 3
- **Goal**: Reduce main file to ~1,000 lines through systematic extraction

## Phase 4: Core GUI Logic Extraction
**Target**: Extract remaining core GUI functionality

### 4.1 Search and URL Management Module
**File**: `gui/search_url_manager.py`
**Responsibilities**:
- URL preview generation
- Search parameter handling
- Store-specific URL building
- Category and shop selection logic

**Methods to extract**:
- `_update_preview()`
- `_extract_code()`, `_match_main_code()`
- `_select_categories()`, `_get_selected_categories()`
- `_get_recent_hours_value()`, `_label_for_recent_hours()`
- `_resolve_shop()`
- URL building logic for Mandarake and Suruga-ya

### 4.2 Config Management Module
**File**: `gui/config_management.py`
**Responsibilities**:
- Config file operations (save/load/delete)
- Auto-save functionality
- Config tree management
- Recent files handling

**Methods to extract**:
- `_collect_config()`, `_save_config_to_path()`, `_save_config_autoname()`
- `_populate_from_config()`, `_update_tree_item()`
- `_auto_save_config()`, `_do_auto_save()`, `_commit_keyword_changes()`
- `_new_config()`, `_delete_selected_config()`, `_move_config()`
- `_load_config_tree()`, `_filter_config_tree()`
- Recent files management

### 4.3 Menu and Dialog Management Module
**File**: `gui/menu_dialog_manager.py`
**Responsibilities**:
- Menu bar creation and handling
- Dialog windows (about, settings, help)
- Context menus

**Methods to extract**:
- `_create_menu_bar()`, `_update_recent_menu()`
- `_show_settings_summary()`, `_reset_settings()`
- `_export_settings()`, `_import_settings()`
- `_show_about()`, `_show_image_search_help()`, `_show_ransac_info()`
- Context menu methods

## Phase 5: Data Processing and Display
**Target**: Extract data handling and display logic

### 5.1 Results Processing Module
**File**: `gui/results_processor.py`
**Responsibilities**:
- CSV loading and processing
- Results tree management
- Image handling and thumbnails

**Methods to extract**:
- `_load_results_table()`, `_load_csv_worker()`
- `_toggle_thumbnails()`, `_on_result_double_click()`
- Results tree operations
- Image loading and caching

### 5.2 eBay Integration Module
**File**: `gui/ebay_integration.py`
**Responsibilities**:
- eBay search operations
- Image comparison logic
- CSV comparison workflow

**Methods to extract**:
- `_search_ebay_sold()`, `_display_ebay_results()`
- `_compare_images()`, `_fetch_exchange_rate()`
- CSV comparison methods
- eBay API integration

### 5.3 Publisher and Keyword Management Module
**File**: `gui/keyword_manager.py`
**Responsibilities**:
- Publisher list management
- Keyword extraction and processing
- Secondary keyword logic

**Methods to extract**:
- `_load_publisher_list()`, `_save_publisher_list()`
- `_add_to_publisher_list()`, `_show_keyword_menu()`
- `_extract_secondary_keyword()`
- `_add_full_title_to_search()`, `_add_secondary_keyword_from_csv()`

## Phase 6: Advanced Features and Utilities
**Target**: Extract remaining specialized functionality

### 6.1 Store Management Module
**File**: `gui/store_manager.py`
**Responsibilities**:
- Store switching logic
- Category population for different stores
- Store-specific configurations

**Methods to extract**:
- `_on_store_changed()`, `_populate_detail_categories()`
- `_populate_shop_list()`, `_populate_surugaya_categories()`
- `_populate_surugaya_shops()`, `_on_main_category_selected()`

### 6.2 Scraper Execution Module
**File**: `gui/scraper_executor.py`
**Responsibilities**:
- Scraper execution logic
- Thread management
- Progress tracking

**Methods to extract**:
- `run_now()`, `cancel_search()`, `_run_scraper()`
- `_run_surugaya_scraper()`, `_start_thread()`
- `_poll_queue()`, queue handling

### 6.3 Window and Layout Management Module
**File**: `gui/window_manager.py`
**Responsibilities**:
- Window state management
- Layout restoration
- Sash position handling

**Methods to extract**:
- `_save_window_settings()`, `_parse_geometry()`
- `_restore_paned_position()`, `_restore_listbox_paned_position()`
- `_on_window_mapped()`, `_on_listbox_sash_moved()`
- Layout and geometry management

## Implementation Strategy

### For Each Phase:
1. **Create the module file** with proper class structure
2. **Extract methods** from gui_config.py to the new module
3. **Update imports** in gui_config.py
4. **Replace method implementations** with delegation calls
5. **Test functionality** to ensure nothing breaks
6. **Update documentation** and progress tracking

### Expected Results:
- **Phase 4**: Reduce from 4,880 to ~3,500 lines
- **Phase 5**: Reduce from ~3,500 to ~2,200 lines  
- **Phase 6**: Reduce from ~2,200 to ~1,000 lines

### Final Structure:
```
gui/
├── __init__.py
├── constants.py
├── utils.py
├── workers.py
├── alert_tab.py
├── schedule_frame.py
├── schedule_executor.py
├── configuration_manager.py
├── tree_manager.py
├── ebay_search_manager.py
├── csv_comparison_manager.py
├── ui_construction_manager.py
├── event_handlers_manager.py
├── results_display_manager.py
├── settings_preferences_manager.py
├── search_url_manager.py (NEW)
├── config_management.py (NEW)
├── menu_dialog_manager.py (NEW)
├── results_processor.py (NEW)
├── ebay_integration.py (NEW)
├── keyword_manager.py (NEW)
├── store_manager.py (NEW)
├── scraper_executor.py (NEW)
└── window_manager.py (NEW)
```

## Success Criteria
1. **gui_config.py** under 1,000 lines
2. **All functionality preserved** - no feature loss
3. **Clean separation of concerns** - each module has single responsibility
4. **Proper documentation** - all modules documented
5. **Tested functionality** - all features work correctly

## Timeline
- **Phase 4**: 2-3 days (largest impact)
- **Phase 5**: 2 days (data-heavy operations)
- **Phase 6**: 1-2 days (final cleanup)

Total estimated time: **5-7 days** for complete modularization.
