"""
Cleanup Manager

Handles cleanup of orphaned files and old caches:
- Orphaned CSV files (config deleted)
- Orphaned image folders (config deleted)
- Old debug comparison folders
- Python cache files
- Old log files

Protects files needed by:
- Existing configs
- Scheduled configs (active schedules)
"""

import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Set, Tuple


class CleanupManager:
    """Manager for cleaning up orphaned and old files."""

    def __init__(self, root_dir: Path = None):
        """
        Initialize cleanup manager.

        Args:
            root_dir: Root directory of the project (defaults to current working directory)
        """
        self.root_dir = root_dir or Path.cwd()
        self.configs_dir = self.root_dir / "configs"
        self.results_dir = self.root_dir / "results"
        self.images_dir = self.root_dir / "images"
        self.debug_dir = self.root_dir / "debug_comparison"
        self.schedules_file = self.root_dir / "schedules.json"

    def _get_protected_configs(self) -> Set[str]:
        """
        Get set of config basenames that should be protected from cleanup.

        Includes:
        - All existing config files
        - Config files referenced in active schedules

        Returns:
            Set of config basenames (without .json extension)
        """
        protected_configs = set()

        # Add all existing config files
        if self.configs_dir.exists():
            for config_file in self.configs_dir.glob("*.json"):
                # Skip special files
                if config_file.name in ['.config_order.json']:
                    continue
                protected_configs.add(config_file.stem)

        # Add config files from active schedules
        if self.schedules_file.exists():
            try:
                with open(self.schedules_file, 'r', encoding='utf-8') as f:
                    schedules = json.load(f)

                # schedules.json is a list of schedule objects
                if isinstance(schedules, list):
                    for schedule in schedules:
                        # Only protect configs from active schedules
                        if schedule.get('active', False):
                            config_files = schedule.get('config_files', [])
                            for config_file in config_files:
                                # Remove .json extension if present
                                basename = Path(config_file).stem
                                protected_configs.add(basename)
                                print(f"[CLEANUP] Protecting scheduled config: {basename}")

            except (json.JSONDecodeError, IOError) as e:
                print(f"[CLEANUP] Warning: Could not load schedules.json: {e}")

        return protected_configs

    def scan_orphaned_files(self) -> Dict[str, List[Path]]:
        """
        Scan for orphaned files (CSVs and image folders without configs).

        Protects files associated with:
        - Existing config files
        - Active scheduled configs

        Returns:
            Dict with keys 'csvs', 'images', 'debug_folders', 'pycache', 'logs'
            containing lists of orphaned file/folder paths
        """
        orphaned = {
            'csvs': [],
            'images': [],
            'debug_folders': [],
            'pycache': [],
            'logs': []
        }

        # Get all protected config basenames
        protected_configs = self._get_protected_configs()
        print(f"[CLEANUP] Protecting {len(protected_configs)} config(s) and their associated files")

        # Find orphaned CSVs
        if self.results_dir.exists():
            for csv_file in self.results_dir.glob("*.csv"):
                # CSV basename should match a protected config
                if csv_file.stem not in protected_configs:
                    orphaned['csvs'].append(csv_file)

        # Find orphaned image folders
        if self.images_dir.exists():
            for img_folder in self.images_dir.iterdir():
                if img_folder.is_dir() and img_folder.name not in protected_configs:
                    orphaned['images'].append(img_folder)

        # Find old debug comparison folders (older than 7 days)
        if self.debug_dir.exists():
            cutoff_date = datetime.now() - timedelta(days=7)
            for debug_folder in self.debug_dir.iterdir():
                if debug_folder.is_dir():
                    # Check folder modification time
                    mtime = datetime.fromtimestamp(debug_folder.stat().st_mtime)
                    if mtime < cutoff_date:
                        orphaned['debug_folders'].append(debug_folder)

        # Find __pycache__ folders
        for pycache in self.root_dir.rglob("__pycache__"):
            if pycache.is_dir():
                orphaned['pycache'].append(pycache)

        # Find old log files (older than 30 days)
        log_cutoff = datetime.now() - timedelta(days=30)
        for log_file in self.root_dir.glob("*.log"):
            mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            if mtime < log_cutoff:
                orphaned['logs'].append(log_file)

        return orphaned

    def get_cleanup_summary(self, orphaned: Dict[str, List[Path]]) -> str:
        """
        Get human-readable summary of orphaned files.

        Args:
            orphaned: Dictionary from scan_orphaned_files()

        Returns:
            Formatted summary string
        """
        lines = []

        if orphaned['csvs']:
            lines.append(f"📄 {len(orphaned['csvs'])} orphaned CSV file(s)")

        if orphaned['images']:
            lines.append(f"🖼️  {len(orphaned['images'])} orphaned image folder(s)")

        if orphaned['debug_folders']:
            lines.append(f"🐛 {len(orphaned['debug_folders'])} old debug folder(s) (>7 days)")

        if orphaned['pycache']:
            lines.append(f"🗑️  {len(orphaned['pycache'])} Python cache folder(s)")

        if orphaned['logs']:
            lines.append(f"📝 {len(orphaned['logs'])} old log file(s) (>30 days)")

        if not lines:
            return "✨ No orphaned files found! Everything is clean."

        return "\n".join(lines)

    def calculate_space(self, orphaned: Dict[str, List[Path]]) -> int:
        """
        Calculate total space used by orphaned files.

        Args:
            orphaned: Dictionary from scan_orphaned_files()

        Returns:
            Total size in bytes
        """
        total_size = 0

        for category, paths in orphaned.items():
            for path in paths:
                if path.is_file():
                    total_size += path.stat().st_size
                elif path.is_dir():
                    # Sum all files in directory
                    for file_path in path.rglob("*"):
                        if file_path.is_file():
                            try:
                                total_size += file_path.stat().st_size
                            except (OSError, PermissionError):
                                pass  # Skip files we can't read

        return total_size

    def format_size(self, size_bytes: int) -> str:
        """
        Format byte size to human-readable string.

        Args:
            size_bytes: Size in bytes

        Returns:
            Formatted string (e.g., "1.5 MB")
        """
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    def delete_orphaned_files(self, orphaned: Dict[str, List[Path]]) -> Tuple[int, int]:
        """
        Delete all orphaned files and folders.

        Args:
            orphaned: Dictionary from scan_orphaned_files()

        Returns:
            Tuple of (success_count, error_count)
        """
        success_count = 0
        error_count = 0

        for category, paths in orphaned.items():
            for path in paths:
                try:
                    if path.is_file():
                        path.unlink()
                        print(f"[CLEANUP] Deleted file: {path}")
                    elif path.is_dir():
                        shutil.rmtree(path)
                        print(f"[CLEANUP] Deleted folder: {path}")
                    success_count += 1
                except Exception as e:
                    print(f"[CLEANUP] Error deleting {path}: {e}")
                    error_count += 1

        return success_count, error_count

    def get_detailed_report(self, orphaned: Dict[str, List[Path]]) -> str:
        """
        Get detailed report of all orphaned files.

        Args:
            orphaned: Dictionary from scan_orphaned_files()

        Returns:
            Detailed formatted report
        """
        lines = ["=== Orphaned Files Report ===\n"]

        # Add protection notice
        protected_configs = self._get_protected_configs()
        lines.append(f"ℹ️  Protected {len(protected_configs)} config(s) (existing + scheduled)")
        lines.append("   CSVs and images for these configs will NOT be deleted.\n")

        if orphaned['csvs']:
            lines.append(f"\n📄 Orphaned CSV Files ({len(orphaned['csvs'])}):")
            for csv_file in sorted(orphaned['csvs']):
                size = self.format_size(csv_file.stat().st_size)
                lines.append(f"  • {csv_file.name} ({size})")

        if orphaned['images']:
            lines.append(f"\n🖼️  Orphaned Image Folders ({len(orphaned['images'])}):")
            for img_folder in sorted(orphaned['images']):
                # Count files in folder
                file_count = sum(1 for _ in img_folder.rglob("*") if _.is_file())
                lines.append(f"  • {img_folder.name}/ ({file_count} files)")

        if orphaned['debug_folders']:
            lines.append(f"\n🐛 Old Debug Folders ({len(orphaned['debug_folders'])}):")
            for debug_folder in sorted(orphaned['debug_folders']):
                mtime = datetime.fromtimestamp(debug_folder.stat().st_mtime)
                age_days = (datetime.now() - mtime).days
                lines.append(f"  • {debug_folder.name}/ ({age_days} days old)")

        if orphaned['pycache']:
            lines.append(f"\n🗑️  Python Cache Folders ({len(orphaned['pycache'])}):")
            for pycache in sorted(orphaned['pycache'])[:10]:  # Limit to 10
                rel_path = pycache.relative_to(self.root_dir)
                lines.append(f"  • {rel_path}")
            if len(orphaned['pycache']) > 10:
                lines.append(f"  ... and {len(orphaned['pycache']) - 10} more")

        if orphaned['logs']:
            lines.append(f"\n📝 Old Log Files ({len(orphaned['logs'])}):")
            for log_file in sorted(orphaned['logs']):
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                age_days = (datetime.now() - mtime).days
                lines.append(f"  • {log_file.name} ({age_days} days old)")

        if not any(orphaned.values()):
            return "✨ No orphaned files found! Everything is clean."

        total_size = self.calculate_space(orphaned)
        lines.append(f"\n💾 Total space used: {self.format_size(total_size)}")

        return "\n".join(lines)
