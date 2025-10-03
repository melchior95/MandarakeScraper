"""
Schedule executor - runs scheduled tasks in background.

Monitors active schedules and executes them when due.
"""

import threading
import time
from typing import Optional, Callable
from pathlib import Path

from gui.schedule_manager import ScheduleManager
from gui.schedule_states import Schedule


class ScheduleExecutor:
    """
    Executes scheduled tasks in a background thread.

    This class monitors active schedules and triggers execution
    when they are due to run.
    """

    def __init__(self, gui_config_ref):
        """
        Initialize executor.

        Args:
            gui_config_ref: Reference to main GUI (ScraperGUI instance)
                           for accessing CSV tree, load_config, run_compare_all, etc.
        """
        self.gui = gui_config_ref
        self.manager = ScheduleManager()
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.check_interval = 60  # Check every 60 seconds

    def start(self):
        """Start the background scheduler thread."""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        print("[SCHEDULE EXECUTOR] Started")

    def stop(self):
        """Stop the background scheduler thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("[SCHEDULE EXECUTOR] Stopped")

    def _run_loop(self):
        """Main loop that checks for due schedules."""
        while self.running:
            try:
                self._check_and_execute()
            except Exception as e:
                print(f"[SCHEDULE EXECUTOR] Error in check loop: {e}")

            # Sleep in small intervals to allow quick shutdown
            for _ in range(self.check_interval):
                if not self.running:
                    break
                time.sleep(1)

    def _check_and_execute(self):
        """Check for due schedules and execute them."""
        due_schedules = self.manager.get_schedules_due_for_execution()

        for schedule in due_schedules:
            print(f"[SCHEDULE EXECUTOR] Executing schedule: {schedule.name} (ID: {schedule.schedule_id})")
            try:
                self._execute_schedule(schedule)
                self.manager.mark_schedule_executed(schedule.schedule_id)
                print(f"[SCHEDULE EXECUTOR] Completed schedule: {schedule.name}")
            except Exception as e:
                print(f"[SCHEDULE EXECUTOR] Error executing schedule {schedule.name}: {e}")

    def _execute_schedule(self, schedule: Schedule):
        """
        Execute a schedule by running all its config files.

        Args:
            schedule: Schedule to execute
        """
        configs_dir = Path("configs")

        for config_filename in schedule.config_files:
            config_path = configs_dir / config_filename

            if not config_path.exists():
                print(f"[SCHEDULE EXECUTOR] Config not found: {config_path}")
                continue

            print(f"[SCHEDULE EXECUTOR] Processing config: {config_filename}")

            # Execute on main thread using after()
            self.gui.after(0, lambda p=config_path: self._run_config_on_main_thread(p, schedule))

    def _run_config_on_main_thread(self, config_path: Path, schedule: Schedule):
        """
        Run a single config on the main GUI thread.

        This method:
        1. Sets CSV filter options from schedule
        2. Loads the config into the GUI
        3. Runs Compare All
        4. Sends results to alerts tab (items meeting thresholds)

        Args:
            config_path: Path to config JSON file
            schedule: Parent schedule (for logging)
        """
        try:
            # Set CSV filter options from schedule
            print(f"[SCHEDULE EXECUTOR] Setting CSV filters from schedule: newly_listed={schedule.csv_newly_listed}, in_stock={schedule.csv_in_stock}, 2nd_kw={schedule.csv_2nd_keyword}")
            self.gui.csv_newly_listed_only.set(schedule.csv_newly_listed)
            self.gui.csv_in_stock_only.set(schedule.csv_in_stock)
            self.gui.csv_add_secondary_keyword.set(schedule.csv_2nd_keyword)

            # Load config into GUI
            print(f"[SCHEDULE EXECUTOR] Loading config: {config_path.name}")
            self.gui._load_config_file(config_path)

            # Wait a moment for config to load
            self.gui.after(500, lambda: self._run_comparison(config_path, schedule))

        except Exception as e:
            print(f"[SCHEDULE EXECUTOR] Error loading config {config_path.name}: {e}")

    def _run_comparison(self, config_path: Path, schedule: Schedule):
        """
        Run comparison after config is loaded.

        Args:
            config_path: Path to config (for logging)
            schedule: Parent schedule (for logging)
        """
        try:
            print(f"[SCHEDULE EXECUTOR] Running comparison for: {config_path.name}")

            # Get alert tab thresholds
            alert_tab = self.gui.alert_tab
            min_similarity, min_profit = alert_tab.get_threshold_values()

            # Run compare all (this will populate csv_comparison_results)
            self.gui._run_csv_comparison_async()

            # Wait for comparison to complete, then send to alerts
            # We'll use a callback approach
            self.gui.after(2000, lambda: self._check_comparison_complete(
                config_path, schedule, min_similarity, min_profit
            ))

        except Exception as e:
            print(f"[SCHEDULE EXECUTOR] Error running comparison for {config_path.name}: {e}")

    def _check_comparison_complete(
        self,
        config_path: Path,
        schedule: Schedule,
        min_similarity: float,
        min_profit: float
    ):
        """
        Check if comparison is complete and send results to alerts.

        Args:
            config_path: Path to config (for logging)
            schedule: Parent schedule
            min_similarity: Similarity threshold
            min_profit: Profit threshold
        """
        # Check if comparison results exist
        if not hasattr(self.gui, 'csv_comparison_results') or not self.gui.csv_comparison_results:
            # Not ready yet, check again in 1 second
            self.gui.after(1000, lambda: self._check_comparison_complete(
                config_path, schedule, min_similarity, min_profit
            ))
            return

        try:
            # Send results to alerts tab
            results = self.gui.csv_comparison_results
            print(f"[SCHEDULE EXECUTOR] Sending {len(results)} results to alerts for {config_path.name}")

            # Filter results by thresholds and send to alerts
            filtered_results = []
            for result in results:
                similarity = result.get('similarity', 0)
                profit = result.get('profit_margin', 0)

                if similarity >= min_similarity and profit >= min_profit:
                    filtered_results.append(result)

            if filtered_results:
                self.gui.alert_tab.add_comparison_results_to_alerts(filtered_results)
                print(f"[SCHEDULE EXECUTOR] Added {len(filtered_results)} items to alerts")
            else:
                print(f"[SCHEDULE EXECUTOR] No items met thresholds for {config_path.name}")

        except Exception as e:
            print(f"[SCHEDULE EXECUTOR] Error sending to alerts: {e}")

    def execute_schedule_now(self, schedule_id: int):
        """
        Manually trigger a schedule execution immediately.

        Args:
            schedule_id: ID of schedule to execute
        """
        schedule = self.manager.storage.get_by_id(schedule_id)
        if schedule:
            print(f"[SCHEDULE EXECUTOR] Manual execution of: {schedule.name}")
            self._execute_schedule(schedule)
            self.manager.mark_schedule_executed(schedule_id)
