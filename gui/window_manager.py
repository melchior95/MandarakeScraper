"""Window and paned position management for GUI."""
import re
import logging


class WindowManager:
    """Manages window geometry, paned positions, and window state."""

    def __init__(self, root, settings_manager):
        """Initialize window manager.

        Args:
            root: The Tk root window
            settings_manager: SettingsManager instance
        """
        self.root = root
        self.settings = settings_manager
        self._user_sash_ratio = None  # Listbox paned ratio
        self._user_vertical_sash_ratio = None  # Vertical paned ratio

    def apply_window_settings(self):
        """Apply saved window settings to the root window."""
        window_settings = self.settings.get_window_settings()
        width = window_settings.get('width', 780)
        height = window_settings.get('height', 760)
        x = window_settings.get('x', 100)
        y = window_settings.get('y', 100)

        self.root.geometry(f"{width}x{height}+{x}+{y}")

        # Restore maximized state if it was maximized
        if window_settings.get('maximized', False):
            self.root.state('zoomed')  # Windows/Linux
            # For macOS, use: self.root.attributes('-zoomed', True)

    def save_window_settings(self):
        """Save current window settings."""
        try:
            # Get current window geometry
            geometry = self.root.geometry()
            width, height, x, y = self._parse_geometry(geometry)

            # Check if maximized
            maximized = self.root.state() == 'zoomed'

            # Get paned window sash position (if it exists)
            ebay_paned_pos = None
            if hasattr(self.root, 'ebay_tab') and hasattr(self.root.ebay_tab, 'ebay_paned'):
                try:
                    # Get sash position (distance from top)
                    sash_coords = self.root.ebay_tab.ebay_paned.sash_coord(0)  # First sash
                    if sash_coords:
                        ebay_paned_pos = sash_coords[1]  # Y coordinate
                except:
                    pass

            # Save window settings with paned position
            settings_dict = {
                'width': width,
                'height': height,
                'x': x,
                'y': y,
                'maximized': maximized
            }
            if ebay_paned_pos is not None:
                settings_dict['ebay_paned_pos'] = ebay_paned_pos

            self.settings.save_window_settings(**settings_dict)
            self.settings.save_settings()

        except Exception as e:
            logging.error(f"Error saving window settings: {e}")

    def _parse_geometry(self, geometry_string: str) -> tuple:
        """Parse tkinter geometry string into width, height, x, y."""
        try:
            # Format: "800x600+100+50"
            match = re.match(r'(\d+)x(\d+)\+(\d+)\+(\d+)', geometry_string)
            if match:
                return int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4))
            else:
                return 780, 760, 100, 100
        except:
            return 780, 760, 100, 100

    def restore_paned_position(self, paned_widget, paned_type='ebay'):
        """Restore the paned window sash position from saved settings.

        Args:
            paned_widget: The PanedWindow widget to restore
            paned_type: Type of paned window ('ebay', 'vertical', 'listbox')
        """
        try:
            if paned_type == 'ebay':
                window_settings = self.settings.get_window_settings()
                ebay_paned_pos = window_settings.get('ebay_paned_pos')

                if ebay_paned_pos is not None:
                    # Set the sash position
                    paned_widget.sash_place(0, 0, ebay_paned_pos)
                    print(f"[GUI] Restored eBay paned window position: {ebay_paned_pos}")

            elif paned_type == 'vertical':
                # Load from GUI settings (legacy location)
                gui_settings = self.settings.get_setting('gui_settings', {})
                ratio = gui_settings.get('vertical_paned_ratio', 0.5)  # Default 50/50 split
                total_height = paned_widget.winfo_height()

                # If height is too small, the window hasn't been laid out yet - schedule retry
                if total_height < 100:
                    print(f"[VERTICAL PANED] Height too small ({total_height}px), retrying in 200ms...")
                    self.root.after(200, lambda: self.restore_paned_position(paned_widget, paned_type))
                    return

                sash_pos = int(total_height * ratio)
                paned_widget.sash_place(0, 0, sash_pos)
                self._user_vertical_sash_ratio = ratio  # Initialize user ratio to the restored value
                print(f"[VERTICAL PANED] Restored position with ratio: {ratio:.2f} (height={total_height}px, sash={sash_pos}px)")

            elif paned_type == 'listbox':
                # Load from GUI settings (legacy location)
                gui_settings = self.settings.get_setting('gui_settings', {})
                ratio = gui_settings.get('listbox_paned_ratio', 0.65)  # Default 65% for categories, 35% for shops
                total_width = paned_widget.winfo_width()

                # If width is too small, the window hasn't been laid out yet - schedule retry
                if total_width < 100:
                    print(f"[LISTBOX PANED] Width too small ({total_width}px), retrying in 200ms...")
                    self.root.after(200, lambda: self.restore_paned_position(paned_widget, paned_type))
                    return

                sash_pos = int(total_width * ratio)
                paned_widget.sash_place(0, sash_pos, 0)
                self._user_sash_ratio = ratio  # Initialize user ratio to the restored value
                print(f"[LISTBOX PANED] Restored position with ratio: {ratio:.2f} (width={total_width}px, sash={sash_pos}px)")

        except Exception as e:
            print(f"[PANED] Error restoring {paned_type} position: {e}")
            import traceback
            traceback.print_exc()

    def on_listbox_sash_moved(self, event, paned_widget):
        """Track when user manually moves the listbox sash."""
        try:
            total_width = paned_widget.winfo_width()
            if total_width < 100:
                return

            sash_pos = paned_widget.sash_coord(0)[0]
            ratio = sash_pos / total_width
            self._user_sash_ratio = ratio
            print(f"[LISTBOX PANED] User moved sash - new ratio: {ratio:.2f}")
        except Exception as e:
            print(f"[LISTBOX PANED] Error tracking sash movement: {e}")

    def get_sash_ratios(self):
        """Get the current sash ratios for saving."""
        return {
            'listbox_paned_ratio': self._user_sash_ratio if self._user_sash_ratio is not None else 0.65,
            'vertical_paned_ratio': self._user_vertical_sash_ratio if self._user_vertical_sash_ratio is not None else 0.5
        }
