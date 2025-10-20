"""
Backup utility for Meal Planner data files.
Automatically creates backups of JSON data files.
"""
import json
import shutil
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class BackupManager:
    """Manages automatic backups of data files."""

    def __init__(self, data_dir: Path, backup_dir: Path = None):
        self.data_dir = Path(data_dir)
        self.backup_dir = backup_dir or (self.data_dir / 'backups')
        self.backup_dir.mkdir(exist_ok=True)

    def create_backup(self, filename: str) -> bool:
        """Create a timestamped backup of a data file."""
        try:
            source = self.data_dir / filename
            if not source.exists():
                logger.warning(f"File not found for backup: {filename}")
                return False

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{source.stem}_{timestamp}{source.suffix}"
            destination = self.backup_dir / backup_name

            shutil.copy2(source, destination)
            logger.info(f"Backup created: {backup_name}")

            # Cleanup old backups (keep last 10)
            self._cleanup_old_backups(source.name)
            return True

        except Exception as e:
            logger.error(f"Backup failed for {filename}: {e}")
            return False

    def _cleanup_old_backups(self, filename: str, keep: int = 10):
        """Remove old backups, keeping only the most recent ones."""
        pattern = f"{Path(filename).stem}_*{Path(filename).suffix}"
        backups = sorted(self.backup_dir.glob(pattern), key=lambda p: p.stat().st_mtime)

        # Remove oldest backups if we have more than 'keep'
        for backup in backups[:-keep]:
            try:
                backup.unlink()
                logger.info(f"Removed old backup: {backup.name}")
            except Exception as e:
                logger.error(f"Failed to remove old backup {backup.name}: {e}")

    def restore_backup(self, backup_filename: str) -> bool:
        """Restore a specific backup file."""
        try:
            backup_path = self.backup_dir / backup_filename
            if not backup_path.exists():
                logger.error(f"Backup not found: {backup_filename}")
                return False

            # Extract original filename from backup name
            original_name = backup_filename.rsplit('_', 1)[0].split('_')[0] + Path(backup_filename).suffix
            destination = self.data_dir / original_name

            # Create backup of current file before restoring
            if destination.exists():
                self.create_backup(destination.name)

            shutil.copy2(backup_path, destination)
            logger.info(f"Restored backup: {backup_filename} -> {original_name}")
            return True

        except Exception as e:
            logger.error(f"Restore failed for {backup_filename}: {e}")
            return False

    def list_backups(self, filename: str = None) -> list:
        """List all backups or backups for a specific file."""
        if filename:
            pattern = f"{Path(filename).stem}_*{Path(filename).suffix}"
        else:
            pattern = "*"

        backups = sorted(
            self.backup_dir.glob(pattern),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        return [
            {
                'name': b.name,
                'size': b.stat().st_size,
                'created': datetime.fromtimestamp(b.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            }
            for b in backups
        ]

    def backup_all(self):
        """Create backups for all JSON files in data directory."""
        json_files = self.data_dir.glob('*.json')
        results = {}

        for file in json_files:
            results[file.name] = self.create_backup(file.name)

        return results


# Convenience function for scheduled backups
def auto_backup():
    """Create automatic backups of all data files."""
    from meal.infra.paths import DATA_DIR
    manager = BackupManager(DATA_DIR)
    return manager.backup_all()


if __name__ == "__main__":
    # Test backup functionality
    from meal.infra.paths import DATA_DIR
    manager = BackupManager(DATA_DIR)

    print("Creating backups...")
    results = manager.backup_all()
    for filename, success in results.items():
        status = "✓" if success else "✗"
        print(f"{status} {filename}")

    print("\nAvailable backups:")
    for backup in manager.list_backups():
        print(f"  - {backup['name']} ({backup['size']} bytes) - {backup['created']}")

