#!/usr/bin/env python3
"""Configuration Manager Module - Handles all configuration-related operations."""

import json
import time
import tkinter as tk
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from tkinter import messagebox, filedialog

from gui import utils


class ConfigurationManager:
    """Manages configuration operations for the GUI."""
    
    def __init__(self, settings_manager):
        """Initialize the configuration manager.
        
        Args:
            settings_manager: Settings manager instance
        """
        self.settings = settings_manager
        self.last_saved_path: Optional[Path] = None
        
    def suggest_config_filename(self, config: Dict[str, Any]) -> str:
        """Generate a filename for a config based on its parameters."""
        return utils.suggest_config_filename(config)
    
    def generate_csv_filename(self, config: Dict[str, Any]) -> str:
        """Generate CSV filename based on search parameters."""
        return utils.generate_csv_filename(config)
    
    def find_matching_csv(self, config: Dict[str, Any]) -> Optional[Path]:
        """Find existing CSV files that match the search parameters."""
        return utils.find_matching_csv(config)
    
    def collect_config_from_gui(self, gui_instance) -> Optional[Dict[str, Any]]:
        """Collect configuration data from GUI widgets."""
        try:
            keyword = gui_instance.keyword_var.get().strip()
            
            config: Dict[str, Any] = {
                'store': gui_instance.current_store.get().lower(),
                'keyword': keyword,
                'hide_sold_out': gui_instance.hide_sold_var.get(),
                'csv_show_in_stock_only': gui_instance.csv_in_stock_only.get() if hasattr(gui_instance, 'csv_in_stock_only') else False,
                'csv_add_secondary_keyword': gui_instance.csv_add_secondary_keyword.get() if hasattr(gui_instance, 'csv_add_secondary_keyword') else False,
                'language': gui_instance.language_var.get(),
                'fast': gui_instance.advanced_tab.fast_var.get() if hasattr(gui_instance, 'advanced_tab') else False,
                'resume': gui_instance.advanced_tab.resume_var.get() if hasattr(gui_instance, 'advanced_tab') else True,
                'debug': gui_instance.advanced_tab.debug_var.get() if hasattr(gui_instance, 'advanced_tab') else False,
            }
            
            # Store URL if provided
            current_url = gui_instance.url_var.get()
            if current_url.startswith('http') and not current_url.endswith(')'):
                config['search_url'] = current_url
            elif hasattr(gui_instance, '_provided_url') and gui_instance._provided_url:
                config['search_url'] = gui_instance._provided_url
            
            # Suruga-ya specific fields
            if hasattr(gui_instance, 'exclude_word_var'):
                exclude_word = gui_instance.exclude_word_var.get().strip()
                if exclude_word:
                    config['exclude_word'] = exclude_word
            
            if hasattr(gui_instance, 'condition_var'):
                condition = gui_instance.condition_var.get()
                condition_map = {'All': 'all', 'New Only': '1', 'Used Only': '2'}
                config['condition'] = condition_map.get(condition, 'all')
            
            # Adult content filter
            if hasattr(gui_instance, 'adult_filter_var'):
                adult_filter = gui_instance.adult_filter_var.get()
                config['adult_only'] = (adult_filter == "Adult Only")
            
            # Category handling
            main_category_text = gui_instance.main_category_var.get()
            main_category_code = utils.extract_code(main_category_text) if main_category_text else None
            
            if main_category_code:
                config['category1'] = main_category_code
            
            categories = gui_instance._get_selected_categories()
            if categories:
                category_code = categories[0]
                if gui_instance.current_store.get() == "Suruga-ya":
                    config['category2'] = category_code
                    config['category'] = category_code
                else:
                    from mandarake_codes import get_category_name
                    category_name = get_category_name(category_code, language='en')
                    config['category'] = category_code
                    config['category_name'] = category_name
            
            # Max pages
            max_pages = gui_instance.max_pages_var.get().strip()
            if max_pages:
                try:
                    config['max_pages'] = int(max_pages)
                except ValueError:
                    messagebox.showerror("Validation", "Max pages must be an integer.")
                    return None
            else:
                # Ensure max_pages is always in config (empty string if not set)
                config['max_pages'] = ''
            
            # Results per page
            results_per_page = gui_instance.results_per_page_var.get().strip()
            if results_per_page:
                try:
                    config['results_per_page'] = int(results_per_page)
                except ValueError:
                    config['results_per_page'] = 48
            else:
                config['results_per_page'] = 48
            
            # Recent hours
            recent_hours = gui_instance._get_recent_hours_value()
            if recent_hours:
                config['recent_hours'] = recent_hours
            
            # Shop
            shop_value = gui_instance._resolve_shop()
            if shop_value:
                config['shop'] = shop_value
                from mandarake_codes import get_store_name
                shop_name = get_store_name(shop_value, language='en')
                config['shop_name'] = shop_name
            
            # Output settings
            csv_path = gui_instance.csv_path_var.get().strip()
            if csv_path:
                config['csv'] = csv_path
            
            download_dir = gui_instance.download_dir_var.get().strip()
            if download_dir:
                config['download_images'] = download_dir
            
            thumbs = gui_instance.thumbnails_var.get().strip()
            if thumbs:
                try:
                    config['thumbnails'] = int(thumbs)
                except ValueError:
                    messagebox.showerror("Validation", "Thumbnail width must be an integer.")
                    return None
            
            return config
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to collect configuration: {e}")
            return None
    
    def save_config_to_path(self, config: Dict[str, Any], path: Path, update_tree: bool = True) -> None:
        """Save configuration to a specific path."""
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate paths for CSV and images
        results_dir = Path('results')
        csv_filename = self.generate_csv_filename(config)
        config['csv'] = str(results_dir / csv_filename)
        
        # Auto-generate download_images path
        config_stem = path.stem
        images_dir = Path('images') / config_stem
        config['download_images'] = str(images_dir) + '/'
        
        with path.open('w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        self.last_saved_path = path
    
    def save_config_autoname(self, config: Dict[str, Any]) -> Path:
        """Save configuration with auto-generated filename."""
        filename = self.suggest_config_filename(config)
        path = Path('configs') / filename
        self.save_config_to_path(config, path, update_tree=True)
        return path
    
    def load_config_from_path(self, path: Path) -> Optional[Dict[str, Any]]:
        """Load configuration from a file."""
        try:
            with path.open('r', encoding='utf-8') as f:
                config = json.load(f)
            return config
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load config: {e}")
            return None
    
    def populate_gui_from_config(self, config: Dict[str, Any], gui_instance) -> None:
        """Populate GUI widgets with configuration data."""
        # Set loading flag to prevent trace callbacks
        gui_instance._loading_config = True
        
        try:
            # Store provided URL if present
            if 'search_url' in config:
                gui_instance._provided_url = config['search_url']
                gui_instance.url_var.set(config['search_url'])
            else:
                gui_instance._provided_url = None
            
            gui_instance.keyword_var.set(config.get('keyword', ''))
            
            # Categories
            category = config.get('category')
            if isinstance(category, list):
                categories = category
            elif category:
                categories = [category]
            else:
                categories = []
            gui_instance._select_categories(categories)
            
            gui_instance.max_pages_var.set(str(config.get('max_pages', '')))
            gui_instance.recent_hours_var.set(gui_instance._label_for_recent_hours(config.get('recent_hours')))
            
            # Shop selection
            shop_value = config.get('shop', '')
            matched = False
            
            # Try to find matching shop in listbox
            for idx, code in enumerate(gui_instance.shop_code_map):
                if str(shop_value) == str(code) or shop_value == 'all':
                    gui_instance.shop_listbox.selection_clear(0, tk.END)
                    gui_instance.shop_listbox.selection_set(idx)
                    gui_instance.shop_listbox.see(idx)
                    matched = True
                    break
            
            # If not matched, try matching by name
            if not matched and config.get('shop_name'):
                shop_name = config.get('shop_name')
                for idx, code in enumerate(gui_instance.shop_code_map):
                    if code == "all" or code == "custom":
                        continue
                    from gui.constants import STORE_OPTIONS
                    for store_code, store_name in STORE_OPTIONS:
                        if store_code == code and (shop_name == store_name or shop_name in store_name):
                            gui_instance.shop_listbox.selection_clear(0, tk.END)
                            gui_instance.shop_listbox.selection_set(idx)
                            gui_instance.shop_listbox.see(idx)
                            matched = True
                            break
                    if matched:
                        break
            
            # Default to "All Stores" if not matched
            if not matched:
                gui_instance.shop_listbox.selection_clear(0, tk.END)
                gui_instance.shop_listbox.selection_set(0)
            
            # Other settings
            gui_instance.hide_sold_var.set(config.get('hide_sold_out', False))
            if hasattr(gui_instance, 'csv_in_stock_only'):
                gui_instance.csv_in_stock_only.set(config.get('csv_show_in_stock_only', False))
            if hasattr(gui_instance, 'csv_add_secondary_keyword'):
                gui_instance.csv_add_secondary_keyword.set(config.get('csv_add_secondary_keyword', False))
            gui_instance.language_var.set(config.get('language', 'en'))
            if hasattr(gui_instance, 'advanced_tab'):
                gui_instance.advanced_tab.fast_var.set(config.get('fast', False))
                gui_instance.advanced_tab.resume_var.set(config.get('resume', True))
                gui_instance.advanced_tab.debug_var.set(config.get('debug', False))
            
            # Adult filter
            if hasattr(gui_instance, 'adult_filter_var'):
                adult_only = config.get('adult_only', False)
                gui_instance.adult_filter_var.set("Adult Only" if adult_only else "All")
            
            # Output settings
            gui_instance.csv_path_var.set(config.get('csv', ''))
            gui_instance.download_dir_var.set(config.get('download_images', ''))
            gui_instance.thumbnails_var.set(str(config.get('thumbnails', '')))
            
            # Results per page
            if config.get('store') == 'suruga-ya':
                gui_instance.results_per_page_var.set('50')
            else:
                gui_instance.results_per_page_var.set(str(config.get('results_per_page', '240')))

            if hasattr(gui_instance, 'advanced_tab'):
                gui_instance.advanced_tab.schedule_var.set(config.get('schedule', ''))
            gui_instance._update_preview()
            
        finally:
            gui_instance._loading_config = False
    
    def create_new_config(self, gui_instance) -> Optional[Path]:
        """Create a new configuration from current GUI values."""
        # Ensure "All Stores" is selected if nothing is selected
        if not gui_instance.shop_listbox.curselection():
            gui_instance.shop_listbox.selection_clear(0, tk.END)
            gui_instance.shop_listbox.selection_set(0)
        
        config = self.collect_config_from_gui(gui_instance)
        if not config:
            return None
        
        # Generate filename
        timestamp = int(time.time())
        configs_dir = Path('configs')
        configs_dir.mkdir(parents=True, exist_ok=True)
        
        has_keyword = bool(config.get('keyword', '').strip())
        if has_keyword:
            suggested_filename = self.suggest_config_filename(config)
            path = configs_dir / suggested_filename
            if path.exists():
                keyword_part = config.get('keyword', 'new').replace(' ', '_') or 'new'
                filename = f"{keyword_part}_{timestamp}.json"
                path = configs_dir / filename
        else:
            filename = f'new_config_{timestamp}.json'
            path = configs_dir / filename
        
        # Save the configuration
        self.save_config_to_path(config, path, update_tree=False)
        self.last_saved_path = path
        
        return path
    
    def delete_config(self, path: Path) -> bool:
        """Delete a configuration file and its associated CSV/images."""
        try:
            # Delete the config file
            path.unlink()

            # Clean up associated CSV file
            csv_path = Path('results') / f"{path.stem}.csv"
            if csv_path.exists():
                try:
                    csv_path.unlink()
                    print(f"[DELETE] Removed CSV: {csv_path.name}")
                except Exception as e:
                    print(f"[DELETE] Could not remove CSV {csv_path.name}: {e}")

            # Clean up associated images folder
            images_dir = Path('images') / path.stem
            if images_dir.exists() and images_dir.is_dir():
                try:
                    import shutil
                    shutil.rmtree(images_dir)
                    print(f"[DELETE] Removed images folder: {images_dir.name}")
                except Exception as e:
                    print(f"[DELETE] Could not remove images folder {images_dir.name}: {e}")

            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete config: {e}")
            return False
    
    def get_config_tree_values(self, config: Dict[str, Any], path: Path) -> Tuple:
        """Get values for displaying in config tree."""
        keyword = config.get('keyword', '')
        category = config.get('category_name', config.get('category', ''))
        shop = config.get('shop_name', config.get('shop', ''))
        hide_sold = 'Yes' if config.get('hide_sold_out') else 'No'
        results_per_page = config.get('results_per_page', 48)
        max_pages = config.get('max_pages', '')
        recent_hours = config.get('recent_hours')
        
        # Format latest additions
        from gui.constants import RECENT_OPTIONS
        latest_additions = ''
        if recent_hours:
            for display, hours in RECENT_OPTIONS:
                if hours == recent_hours:
                    latest_additions = display
                    break
        
        language = config.get('language', 'en')
        store = config.get('store', 'Mandarake').title()
        
        return (store, path.name, keyword, category, shop, hide_sold, 
                results_per_page, max_pages, latest_additions, language)
    
    def add_to_recent_files(self, path: Path) -> None:
        """Add a config file to recent files list."""
        self.settings.add_recent_config_file(str(path))
    
    def get_recent_files(self) -> List[str]:
        """Get list of recent config files."""
        return self.settings.get_recent_config_files()
