#!/usr/bin/env python3
"""
Settings Manager for Mandarake Scraper GUI

Handles saving and loading user preferences including window size,
eBay analysis settings, and other configuration options.
"""

import json
import logging
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class SettingsManager:
    """Manages persistent user settings for the application"""

    def __init__(self, settings_file: str = "user_settings.json"):
        self.settings_file = Path(settings_file)
        self.default_settings = {
            # Window settings
            "window": {
                "width": 1000,
                "height": 700,
                "x": 100,
                "y": 100,
                "maximized": False
            },

            # General preferences
            "general": {
                "language": "en",
                "thumbnail_width": 400,
                "csv_thumbnails_enabled": True,
                "auto_save_configs": True,
                "recent_files_limit": 10
            },

            # Scraper-specific defaults
            "scrapers": {
                "mandarake": {
                    "max_pages": 2,
                    "results_per_page": 48,
                    "resume": True,
                    "browser_mimic": True
                },
                "surugaya": {
                    "max_pages": 2,
                    "results_per_page": 50,
                    "show_out_of_stock": False,
                    "translate_titles": True
                }
            },

            # eBay integration settings
            "ebay": {
                "search_method": "scrapy",
                "max_results": 10,
                "sold_listings": True,
                "days_back": 90
            },

            # eBay API credentials
            "ebay_api": {
                "client_id": "",
                "client_secret": ""
            },

            # eBay Analysis settings (legacy, keep for compatibility)
            "ebay_analysis": {
                "min_sold_items": 3,
                "search_days_back": 90,
                "min_profit_margin": 20.0,
                "usd_jpy_rate": 150.0
            },

            # Image comparison settings
            "image_comparison": {
                "similarity_threshold": 70,
                "profit_threshold": 20,
                "enable_ransac": False,
                "save_debug_images": False,
                "weights": {
                    "template": 60,
                    "orb": 25,
                    "ssim": 10,
                    "histogram": 5
                }
            },

            # Alert tab filter settings
            "alerts": {
                "filter_min_similarity": 70.0,
                "filter_min_profit": 20.0,
                "ebay_send_min_similarity": 70.0,
                "ebay_send_min_profit": 20.0,
                "auto_send": False
            },

            # Output directories
            "output": {
                "csv_dir": "results",
                "images_dir": "images",
                "debug_dir": "debug_comparison"
            },

            # Scraper settings (legacy, keep for compatibility)
            "scraper": {
                "last_config_directory": "",
                "auto_save_results": True,
                "default_output_format": "google_sheets",
                "resume_enabled": True,
                "fast_mode": False,
                "download_thumbnails": True,
                "max_csv_items": 0
            },

            # UI preferences
            "ui": {
                "theme": "default",
                "show_debug_messages": False,
                "auto_clear_logs": True,
                "status_update_interval": 1000
            },

            # Recent files and paths
            "recent": {
                "config_files": [],
                "image_analysis_path": "",
                "last_export_directory": "",
                "last_results_save_path": ""
            },

            # Application metadata
            "meta": {
                "version": "1.0.0",
                "first_run": True,
                "last_updated": None,
                "settings_version": 2  # Incremented for new structure
            },

            # Marketplace toggles and settings
            "marketplaces": {
                "enabled": {
                    "mandarake": True,
                    "ebay": True,
                    "surugaya": False,
                    "dejapan": False,
                    "alerts": True
                },
                "surugaya": {
                    "default_category": "7",  # Books & Photobooks
                    "default_shop": "all",
                    "show_out_of_stock": False
                },
                "dejapan": {
                    "favorite_sellers": [],
                    "default_max_results": 50,
                    "highlight_ending_soon": True
                }
            }
        }

        self.current_settings = self.default_settings.copy()
        self.load_settings()

    def load_settings(self) -> Dict[str, Any]:
        """Load settings from file, using defaults if file doesn't exist"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    saved_settings = json.load(f)

                # Merge saved settings with defaults (in case new settings were added)
                self.current_settings = self._merge_settings(self.default_settings, saved_settings)

                # Update metadata
                self.current_settings["meta"]["last_updated"] = datetime.now().isoformat()
                self.current_settings["meta"]["first_run"] = False

                logging.info(f"Settings loaded from {self.settings_file}")
            else:
                logging.info("No settings file found, using defaults")
                self.current_settings = self.default_settings.copy()

        except Exception as e:
            logging.error(f"Error loading settings: {e}")
            self.current_settings = self.default_settings.copy()

        return self.current_settings

    def save_settings(self) -> bool:
        """Save current settings to file"""
        try:
            # Update metadata before saving
            self.current_settings["meta"]["last_updated"] = datetime.now().isoformat()

            # Create backup of existing settings
            if self.settings_file.exists():
                backup_path = self.settings_file.with_suffix('.backup.json')
                try:
                    # Remove existing backup if it exists
                    if backup_path.exists():
                        backup_path.unlink()
                    # Copy current settings to backup instead of rename
                    shutil.copy2(self.settings_file, backup_path)
                except Exception as backup_error:
                    logging.warning(f"Could not create backup: {backup_error}")
                    # Continue saving even if backup fails

            # Save current settings
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.current_settings, f, indent=2, ensure_ascii=False)

            logging.info(f"Settings saved to {self.settings_file}")
            return True

        except Exception as e:
            logging.error(f"Error saving settings: {e}")
            return False

    def get_setting(self, key_path: str, default=None) -> Any:
        """
        Get a setting value using dot notation (e.g., 'ebay_analysis.min_sold_items')
        """
        try:
            keys = key_path.split('.')
            value = self.current_settings

            for key in keys:
                value = value[key]

            return value

        except (KeyError, TypeError):
            logging.warning(f"Setting not found: {key_path}, using default: {default}")
            return default

    def set_setting(self, key_path: str, value: Any) -> bool:
        """
        Set a setting value using dot notation (e.g., 'ebay_analysis.min_sold_items', 5)
        """
        try:
            keys = key_path.split('.')
            target = self.current_settings

            # Navigate to the parent dictionary
            for key in keys[:-1]:
                if key not in target:
                    target[key] = {}
                target = target[key]

            # Set the final value
            target[keys[-1]] = value

            logging.debug(f"Setting updated: {key_path} = {value}")
            return True

        except Exception as e:
            logging.error(f"Error setting {key_path}: {e}")
            return False

    def get_window_settings(self) -> Dict[str, Any]:
        """Get window-specific settings"""
        return self.get_setting("window", {})

    def save_window_settings(self, width: int, height: int, x: int, y: int, maximized: bool = False, ebay_paned_pos: int = None):
        """Save window geometry and state"""
        self.set_setting("window.width", width)
        self.set_setting("window.height", height)
        self.set_setting("window.x", x)
        self.set_setting("window.y", y)
        self.set_setting("window.maximized", maximized)
        if ebay_paned_pos is not None:
            self.set_setting("window.ebay_paned_pos", ebay_paned_pos)

    def get_ebay_analysis_settings(self) -> Dict[str, Any]:
        """Get eBay analysis specific settings"""
        return self.get_setting("ebay_analysis", {})

    def save_ebay_analysis_settings(self, **kwargs):
        """Save eBay analysis settings"""
        for key, value in kwargs.items():
            self.set_setting(f"ebay_analysis.{key}", value)

    def get_scraper_settings(self) -> Dict[str, Any]:
        """Get scraper specific settings"""
        return self.get_setting("scraper", {})

    def save_scraper_settings(self, **kwargs):
        """Save scraper settings"""
        for key, value in kwargs.items():
            self.set_setting(f"scraper.{key}", value)

    def get_marketplace_toggles(self) -> Dict[str, bool]:
        """Get which marketplaces are enabled"""
        return self.get_setting("marketplaces.enabled", {
            "mandarake": True,
            "ebay": True,
            "surugaya": False,
            "dejapan": False,
            "alerts": True
        })

    def save_marketplace_toggles(self, toggles: Dict[str, bool]):
        """Save marketplace enable/disable state"""
        for marketplace, enabled in toggles.items():
            self.set_setting(f"marketplaces.enabled.{marketplace}", enabled)
        self.save_settings()

    def get_surugaya_settings(self) -> Dict[str, Any]:
        """Get Suruga-ya specific settings"""
        return self.get_setting("marketplaces.surugaya", {
            "default_category": "7",
            "default_shop": "all",
            "show_out_of_stock": False
        })

    def save_surugaya_settings(self, **kwargs):
        """Save Suruga-ya settings"""
        for key, value in kwargs.items():
            self.set_setting(f"marketplaces.surugaya.{key}", value)
        self.save_settings()

    def get_dejapan_settings(self) -> Dict[str, Any]:
        """Get DejaJapan specific settings"""
        return self.get_setting("marketplaces.dejapan", {
            "favorite_sellers": [],
            "default_max_results": 50,
            "highlight_ending_soon": True
        })

    def save_dejapan_settings(self, **kwargs):
        """Save DejaJapan settings"""
        for key, value in kwargs.items():
            self.set_setting(f"marketplaces.dejapan.{key}", value)
        self.save_settings()

    def get_alert_settings(self) -> Dict[str, Any]:
        """Get alert filter settings"""
        return self.get_setting("alerts", {
            "filter_min_similarity": 70.0,
            "filter_min_profit": 20.0,
            "ebay_send_min_similarity": 70.0,
            "ebay_send_min_profit": 20.0
        })

    def save_alert_settings(self, **kwargs):
        """Save alert filter settings"""
        for key, value in kwargs.items():
            self.set_setting(f"alerts.{key}", value)
        self.save_settings()

    def add_dejapan_favorite_seller(self, seller_id: str, name: str, notes: str = ""):
        """Add a seller to DejaJapan favorites"""
        favorites = self.get_setting("marketplaces.dejapan.favorite_sellers", [])
        seller = {
            "id": seller_id,
            "name": name,
            "notes": notes,
            "added_at": datetime.now().isoformat()
        }
        favorites.append(seller)
        self.set_setting("marketplaces.dejapan.favorite_sellers", favorites)
        self.save_settings()

    def remove_dejapan_favorite_seller(self, seller_id: str):
        """Remove a seller from DejaJapan favorites"""
        favorites = self.get_setting("marketplaces.dejapan.favorite_sellers", [])
        favorites = [s for s in favorites if s.get("id") != seller_id]
        self.set_setting("marketplaces.dejapan.favorite_sellers", favorites)
        self.save_settings()

    def get_ebay_credentials(self) -> Dict[str, str]:
        """Get eBay API credentials"""
        return self.get_setting("ebay_api", {
            "client_id": "",
            "client_secret": ""
        })

    def save_ebay_credentials(self, client_id: str, client_secret: str):
        """Save eBay API credentials"""
        self.set_setting("ebay_api.client_id", client_id)
        self.set_setting("ebay_api.client_secret", client_secret)
        self.save_settings()

    def add_recent_config_file(self, file_path: str, max_recent: int = 10):
        """Add a config file to recent files list"""
        recent_files = self.get_setting("recent.config_files", [])

        # Remove if already exists
        if file_path in recent_files:
            recent_files.remove(file_path)

        # Add to beginning
        recent_files.insert(0, file_path)

        # Limit to max_recent
        recent_files = recent_files[:max_recent]

        self.set_setting("recent.config_files", recent_files)

    def get_recent_config_files(self) -> list:
        """Get list of recent config files"""
        return self.get_setting("recent.config_files", [])

    def save_recent_paths(self, **kwargs):
        """Save recent file paths"""
        for key, value in kwargs.items():
            self.set_setting(f"recent.{key}", value)

    def reset_to_defaults(self) -> bool:
        """Reset all settings to defaults"""
        try:
            self.current_settings = self.default_settings.copy()
            self.save_settings()
            logging.info("Settings reset to defaults")
            return True
        except Exception as e:
            logging.error(f"Error resetting settings: {e}")
            return False

    def export_settings(self, export_path: str) -> bool:
        """Export current settings to a file"""
        try:
            export_file = Path(export_path)
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(self.current_settings, f, indent=2, ensure_ascii=False)
            logging.info(f"Settings exported to {export_path}")
            return True
        except Exception as e:
            logging.error(f"Error exporting settings: {e}")
            return False

    def import_settings(self, import_path: str) -> bool:
        """Import settings from a file"""
        try:
            import_file = Path(import_path)
            if not import_file.exists():
                raise FileNotFoundError(f"Import file not found: {import_path}")

            with open(import_file, 'r', encoding='utf-8') as f:
                imported_settings = json.load(f)

            # Validate and merge imported settings
            self.current_settings = self._merge_settings(self.default_settings, imported_settings)
            self.save_settings()

            logging.info(f"Settings imported from {import_path}")
            return True
        except Exception as e:
            logging.error(f"Error importing settings: {e}")
            return False

    def _merge_settings(self, defaults: Dict, saved: Dict) -> Dict:
        """Recursively merge saved settings with defaults"""
        merged = defaults.copy()

        for key, value in saved.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._merge_settings(merged[key], value)
            else:
                merged[key] = value

        return merged

    def get_all_settings(self) -> Dict[str, Any]:
        """Get all current settings"""
        return self.current_settings.copy()

    def is_first_run(self) -> bool:
        """Check if this is the first time the application is run"""
        return self.get_setting("meta.first_run", True)

    def get_settings_summary(self) -> str:
        """Get a formatted summary of current settings"""
        summary = "=== CURRENT SETTINGS SUMMARY ===\n\n"

        # Window settings
        window = self.get_window_settings()
        summary += f"Window Size: {window.get('width', 'default')}x{window.get('height', 'default')}\n"
        summary += f"Window Position: ({window.get('x', 'default')}, {window.get('y', 'default')})\n"
        summary += f"Maximized: {window.get('maximized', False)}\n\n"

        # eBay analysis settings
        ebay = self.get_ebay_analysis_settings()
        summary += "eBay Analysis Settings:\n"
        summary += f"  Min Sold Items: {ebay.get('min_sold_items', 'default')}\n"
        summary += f"  Search Days Back: {ebay.get('search_days_back', 'default')}\n"
        summary += f"  Min Profit Margin: {ebay.get('min_profit_margin', 'default')}%\n"
        summary += f"  USD/JPY Rate: {ebay.get('usd_jpy_rate', 'default')}\n\n"

        # Recent files
        recent_configs = self.get_recent_config_files()
        summary += f"Recent Config Files: {len(recent_configs)} files\n"

        # Meta info
        meta = self.get_setting("meta", {})
        summary += f"Last Updated: {meta.get('last_updated', 'Never')}\n"
        summary += f"First Run: {meta.get('first_run', True)}\n"

        return summary


# Global settings manager instance
_settings_manager = None

def get_settings_manager() -> SettingsManager:
    """Get the global settings manager instance"""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager()
    return _settings_manager


# Convenience functions
def load_settings() -> Dict[str, Any]:
    """Load and return all settings"""
    return get_settings_manager().load_settings()

def save_settings() -> bool:
    """Save current settings"""
    return get_settings_manager().save_settings()

def get_setting(key_path: str, default=None) -> Any:
    """Get a setting value"""
    return get_settings_manager().get_setting(key_path, default)

def set_setting(key_path: str, value: Any) -> bool:
    """Set a setting value"""
    return get_settings_manager().set_setting(key_path, value)


if __name__ == '__main__':
    # Example usage and testing
    import sys

    settings = SettingsManager()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "summary":
            print(settings.get_settings_summary())

        elif command == "reset":
            if settings.reset_to_defaults():
                print("Settings reset to defaults successfully")
            else:
                print("Failed to reset settings")

        elif command == "export" and len(sys.argv) > 2:
            export_path = sys.argv[2]
            if settings.export_settings(export_path):
                print(f"Settings exported to {export_path}")
            else:
                print(f"Failed to export settings to {export_path}")

        elif command == "import" and len(sys.argv) > 2:
            import_path = sys.argv[2]
            if settings.import_settings(import_path):
                print(f"Settings imported from {import_path}")
            else:
                print(f"Failed to import settings from {import_path}")

        else:
            print("Unknown command or missing arguments")

    else:
        print("Usage:")
        print("  python settings_manager.py summary                    # Show settings summary")
        print("  python settings_manager.py reset                      # Reset to defaults")
        print("  python settings_manager.py export <file_path>         # Export settings")
        print("  python settings_manager.py import <file_path>         # Import settings")
