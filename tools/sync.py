#!/usr/bin/env python3
"""
ai-history Cloud Sync

Synchronize your AI chat history to cloud storage for backup and cross-device access.

Supported backends:
- Google Drive (via rclone or service account)
- Local folder (for testing or custom sync)

Usage:
    # Configure rclone first: rclone config
    python3 sync.py --setup gdrive
    python3 sync.py --push
    python3 sync.py --pull
    python3 sync.py --status

Requirements:
    - rclone (recommended): https://rclone.org/install/
    - Or: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Configuration
AI_HISTORY_DIR = Path.home() / ".ai-history"
SYNC_CONFIG_PATH = AI_HISTORY_DIR / "sync-config.json"
SYNC_STATE_PATH = AI_HISTORY_DIR / "sync-state.json"


class SyncBackend:
    """Base class for sync backends."""

    def push(self, local_path: Path, remote_path: str) -> bool:
        raise NotImplementedError

    def pull(self, remote_path: str, local_path: Path) -> bool:
        raise NotImplementedError

    def status(self) -> dict:
        raise NotImplementedError


class RcloneBackend(SyncBackend):
    """Sync using rclone (supports Google Drive, Dropbox, S3, etc.)."""

    def __init__(self, remote_name: str = "ai-history"):
        self.remote_name = remote_name
        self.remote_path = f"{remote_name}:ai-history"

    @staticmethod
    def is_available() -> bool:
        """Check if rclone is installed."""
        return shutil.which("rclone") is not None

    def is_configured(self) -> bool:
        """Check if the remote is configured."""
        try:
            result = subprocess.run(
                ["rclone", "listremotes"],
                capture_output=True,
                text=True
            )
            return f"{self.remote_name}:" in result.stdout
        except Exception:
            return False

    def setup_gdrive(self) -> bool:
        """Interactive setup for Google Drive."""
        print("\n" + "=" * 50)
        print("Google Drive Setup")
        print("=" * 50)

        if not self.is_available():
            print("\n❌ rclone is not installed!")
            print("\nInstall rclone:")
            print("  Linux: curl https://rclone.org/install.sh | sudo bash")
            print("  macOS: brew install rclone")
            print("  Windows: choco install rclone")
            return False

        if self.is_configured():
            print(f"\n✓ Remote '{self.remote_name}' is already configured.")
            overwrite = input("Reconfigure? [y/N]: ").strip().lower()
            if overwrite != 'y':
                return True

        print("\nStarting rclone configuration for Google Drive...")
        print("This will open a browser for authentication.\n")

        try:
            # Create rclone config for Google Drive
            subprocess.run([
                "rclone", "config", "create",
                self.remote_name, "drive",
                "scope", "drive.file"
            ], check=True)

            print("\n✓ Google Drive configured successfully!")
            print(f"  Remote: {self.remote_name}:")
            print(f"  Sync folder: ai-history/")

            # Save config
            self._save_config({
                "backend": "rclone",
                "remote_name": self.remote_name,
                "setup_date": datetime.now().isoformat()
            })

            return True

        except subprocess.CalledProcessError as e:
            print(f"\n❌ Configuration failed: {e}")
            return False

    def push(self, local_path: Path = AI_HISTORY_DIR, remote_path: Optional[str] = None) -> bool:
        """Push local changes to remote."""
        if not self.is_configured():
            print("❌ Remote not configured. Run: python3 sync.py --setup gdrive")
            return False

        remote = remote_path or self.remote_path

        print(f"\n📤 Pushing to {remote}...")

        try:
            # Exclude sync state files
            result = subprocess.run([
                "rclone", "sync",
                str(local_path), remote,
                "--exclude", "sync-*.json",
                "--exclude", "*.tmp",
                "-v"
            ], capture_output=True, text=True)

            if result.returncode == 0:
                self._update_sync_state("push")
                print("✓ Push completed successfully!")
                return True
            else:
                print(f"❌ Push failed: {result.stderr}")
                return False

        except Exception as e:
            print(f"❌ Push error: {e}")
            return False

    def pull(self, remote_path: Optional[str] = None, local_path: Path = AI_HISTORY_DIR) -> bool:
        """Pull remote changes to local."""
        if not self.is_configured():
            print("❌ Remote not configured. Run: python3 sync.py --setup gdrive")
            return False

        remote = remote_path or self.remote_path

        print(f"\n📥 Pulling from {remote}...")

        try:
            result = subprocess.run([
                "rclone", "sync",
                remote, str(local_path),
                "--exclude", "sync-*.json",
                "--exclude", "*.tmp",
                "-v"
            ], capture_output=True, text=True)

            if result.returncode == 0:
                self._update_sync_state("pull")
                print("✓ Pull completed successfully!")
                return True
            else:
                print(f"❌ Pull failed: {result.stderr}")
                return False

        except Exception as e:
            print(f"❌ Pull error: {e}")
            return False

    def status(self) -> dict:
        """Get sync status."""
        status = {
            "backend": "rclone",
            "remote_name": self.remote_name,
            "rclone_available": self.is_available(),
            "remote_configured": self.is_configured(),
            "last_sync": None,
            "remote_size": None
        }

        # Load last sync state
        if SYNC_STATE_PATH.exists():
            with open(SYNC_STATE_PATH) as f:
                state = json.load(f)
                status["last_sync"] = state.get("last_sync")
                status["last_action"] = state.get("last_action")

        # Get remote size if configured
        if status["remote_configured"]:
            try:
                result = subprocess.run(
                    ["rclone", "size", self.remote_path, "--json"],
                    capture_output=True, text=True, timeout=30
                )
                if result.returncode == 0:
                    size_info = json.loads(result.stdout)
                    status["remote_files"] = size_info.get("count", 0)
                    status["remote_size_bytes"] = size_info.get("bytes", 0)
                    status["remote_size"] = self._format_size(size_info.get("bytes", 0))
            except Exception:
                pass

        return status

    @staticmethod
    def _format_size(bytes_size: int) -> str:
        """Format bytes to human readable."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024
        return f"{bytes_size:.1f} TB"

    def _save_config(self, config: dict):
        """Save sync configuration."""
        AI_HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        with open(SYNC_CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)

    def _update_sync_state(self, action: str):
        """Update sync state after operation."""
        state = {}
        if SYNC_STATE_PATH.exists():
            with open(SYNC_STATE_PATH) as f:
                state = json.load(f)

        state["last_sync"] = datetime.now().isoformat()
        state["last_action"] = action

        with open(SYNC_STATE_PATH, 'w') as f:
            json.dump(state, f, indent=2)


class LocalBackend(SyncBackend):
    """Sync to a local folder (for testing or custom sync solutions)."""

    def __init__(self, target_dir: Path):
        self.target_dir = Path(target_dir)

    def push(self, local_path: Path = AI_HISTORY_DIR) -> bool:
        """Copy to target directory."""
        print(f"\n📤 Copying to {self.target_dir}...")

        try:
            self.target_dir.mkdir(parents=True, exist_ok=True)

            # Use rsync if available, otherwise shutil
            if shutil.which("rsync"):
                subprocess.run([
                    "rsync", "-av", "--delete",
                    "--exclude", "sync-*.json",
                    str(local_path) + "/",
                    str(self.target_dir) + "/"
                ], check=True)
            else:
                # Manual copy
                if self.target_dir.exists():
                    shutil.rmtree(self.target_dir)
                shutil.copytree(local_path, self.target_dir)

            print("✓ Copy completed!")
            return True

        except Exception as e:
            print(f"❌ Copy failed: {e}")
            return False

    def pull(self, local_path: Path = AI_HISTORY_DIR) -> bool:
        """Copy from target directory."""
        if not self.target_dir.exists():
            print(f"❌ Source directory doesn't exist: {self.target_dir}")
            return False

        print(f"\n📥 Copying from {self.target_dir}...")

        try:
            if shutil.which("rsync"):
                subprocess.run([
                    "rsync", "-av", "--delete",
                    "--exclude", "sync-*.json",
                    str(self.target_dir) + "/",
                    str(local_path) + "/"
                ], check=True)
            else:
                if local_path.exists():
                    shutil.rmtree(local_path)
                shutil.copytree(self.target_dir, local_path)

            print("✓ Copy completed!")
            return True

        except Exception as e:
            print(f"❌ Copy failed: {e}")
            return False

    def status(self) -> dict:
        return {
            "backend": "local",
            "target_dir": str(self.target_dir),
            "target_exists": self.target_dir.exists()
        }


def print_status(status: dict):
    """Pretty print sync status."""
    print("\n" + "=" * 50)
    print("Sync Status")
    print("=" * 50)

    print(f"\n📦 Backend: {status.get('backend', 'unknown')}")

    if status.get('backend') == 'rclone':
        print(f"   Remote: {status.get('remote_name', 'unknown')}:")

        if status.get('rclone_available'):
            print("   rclone: ✓ installed")
        else:
            print("   rclone: ❌ not installed")

        if status.get('remote_configured'):
            print("   Remote: ✓ configured")
        else:
            print("   Remote: ❌ not configured")

        if status.get('remote_size'):
            print(f"   Cloud: {status.get('remote_files', 0)} files, {status['remote_size']}")

    if status.get('last_sync'):
        print(f"\n🕐 Last sync: {status['last_sync'][:19]}")
        print(f"   Action: {status.get('last_action', 'unknown')}")
    else:
        print("\n🕐 No sync history")

    print()


def main():
    parser = argparse.ArgumentParser(
        description="Sync ai-history to cloud storage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 sync.py --setup gdrive     # Setup Google Drive
    python3 sync.py --push             # Upload to cloud
    python3 sync.py --pull             # Download from cloud
    python3 sync.py --status           # Check sync status

Supported cloud providers (via rclone):
    - Google Drive
    - Dropbox
    - OneDrive
    - Amazon S3
    - And 40+ more: https://rclone.org/overview/
        """
    )

    parser.add_argument("--setup", choices=["gdrive", "dropbox", "local"],
                        help="Setup sync backend")
    parser.add_argument("--push", action="store_true",
                        help="Push local changes to cloud")
    parser.add_argument("--pull", action="store_true",
                        help="Pull cloud changes to local")
    parser.add_argument("--status", action="store_true",
                        help="Show sync status")
    parser.add_argument("--local-dir", type=Path,
                        help="Target directory for local sync")
    parser.add_argument("--remote", default="ai-history",
                        help="rclone remote name (default: ai-history)")

    args = parser.parse_args()

    # Default to status if no action specified
    if not any([args.setup, args.push, args.pull, args.status]):
        args.status = True

    # Select backend
    if args.local_dir:
        backend = LocalBackend(args.local_dir)
    else:
        backend = RcloneBackend(args.remote)

    # Execute action
    if args.setup:
        if args.setup == "gdrive":
            backend.setup_gdrive()
        elif args.setup == "dropbox":
            print("Dropbox setup: rclone config create ai-history dropbox")
        elif args.setup == "local":
            print("Local sync doesn't need setup. Use --local-dir to specify target.")

    elif args.push:
        backend.push()

    elif args.pull:
        backend.pull()

    elif args.status:
        status = backend.status()
        print_status(status)


if __name__ == "__main__":
    main()
