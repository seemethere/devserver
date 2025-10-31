#!/usr/bin/env python3
"""
Development script to watch for file changes and sync them to the remote operator.
"""

import argparse
import subprocess
import sys
import time
import threading
import getpass
from pathlib import Path

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError:
    print("❌ watchdog is not installed. Please run: uv pip install watchdog")
    sys.exit(1)

from kubernetes import client, config


class SourceFileHandler(FileSystemEventHandler):
    """Handler for file system events."""

    def __init__(self, namespace: str, pod_name: str, debounce_seconds: float = 1.0):
        self.namespace = namespace
        self.pod_name = pod_name
        self.debounce_seconds = debounce_seconds
        self.last_sync_time = 0
        self.pending_sync = False
        self.sync_lock = threading.Lock()

    def on_any_event(self, event):
        """Called on any file system event."""
        # Ignore directory events and temporary files
        if event.is_directory:
            return

        # Ignore common temporary/cache files
        ignored_patterns = [
            '__pycache__',
            '.pyc',
            '.pyo',
            '.swp',
            '.swo',
            '~',
            '.DS_Store',
            '.egg-info',
        ]

        if any(pattern in event.src_path for pattern in ignored_patterns):
            return

        with self.sync_lock:
            current_time = time.time()
            # Debounce: only sync if enough time has passed since last sync
            if current_time - self.last_sync_time < self.debounce_seconds:
                # Mark that we need to sync, but don't do it yet
                self.pending_sync = True
                return

            # Perform the sync
            self.perform_sync()

    def perform_sync(self):
        """Sync files to the pod."""
        print("\n🔄 File change detected. Syncing to pod...")
        self.last_sync_time = time.time()
        self.pending_sync = False

        project_root = Path(__file__).parent.parent
        source_path = project_root / "src"
        dest_path = f"{self.namespace}/{self.pod_name}:/app"

        # Remove old source directory and copy new one
        rm_cmd = ["kubectl", "exec", "-n", self.namespace, self.pod_name, "--", "rm", "-rf", "/app/src"]
        cp_cmd = ["kubectl", "cp", str(source_path.resolve()), dest_path]

        try:
            subprocess.run(rm_cmd, check=True, capture_output=True, text=True)
            subprocess.run(cp_cmd, check=True, capture_output=True, text=True)

            # Restart the operator
            restart_cmd = ["kubectl", "exec", "-n", self.namespace, self.pod_name, "--", "kill", "-HUP", "1"]
            subprocess.run(restart_cmd, check=True, capture_output=True, text=True)

            print(f"✅ Files synced and operator restarted at {time.strftime('%H:%M:%S')}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Error syncing files: {e.stderr}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")

    def check_pending_sync(self):
        """Check if there's a pending sync that needs to be performed."""
        with self.sync_lock:
            if self.pending_sync:
                current_time = time.time()
                if current_time - self.last_sync_time >= self.debounce_seconds:
                    self.perform_sync()


def get_current_context():
    """Get the current kubeconfig context."""
    try:
        contexts, active_context = config.list_kube_config_contexts()
        if not contexts:
            print("❌ No contexts found in kubeconfig.")
            sys.exit(1)
        return active_context['name']
    except Exception as e:
        print(f"❌ Failed to get current kubeconfig context: {e}")
        sys.exit(1)


def get_default_namespace():
    """Gets the default namespace for the current user."""
    user = getpass.getuser().lower()
    sanitized_user = ''.join(c for c in user if c.isalnum() or c == '-')
    if not sanitized_user:
        print("❌ Could not determine a valid username for the namespace.")
        sys.exit(1)
    return f"dev-{sanitized_user}"


def get_operator_pod(namespace: str, context: str) -> str:
    """Get the operator pod name."""
    config.load_kube_config(context=context)
    api = client.CoreV1Api()

    pods = api.list_namespaced_pod(namespace, label_selector="app=devserver-operator-dev")
    if not pods.items:
        print(f"❌ No operator pod found in namespace '{namespace}'")
        sys.exit(1)

    pod = pods.items[0]
    if pod.status.phase != "Running":
        print(f"❌ Operator pod is not running (status: {pod.status.phase})")
        sys.exit(1)

    return pod.metadata.name


def stream_logs(namespace: str):
    """Stream logs from the operator pod."""
    cmd = [
        "kubectl", "logs", "-f",
        "-n", namespace,
        "-l", "app=devserver-operator-dev",
        "--tail", "10"  # Start with last 10 lines to avoid huge backlog
    ]

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        pass


def watch_files(namespace: str, pod_name: str, watch_path: Path):
    """Watch for file changes and sync them."""
    print(f"👀 Watching for file changes in {watch_path}...")
    print(f"   Files will sync to pod '{pod_name}' in namespace '{namespace}'")
    print("   Press Ctrl+C to stop\n")

    event_handler = SourceFileHandler(namespace, pod_name)
    observer = Observer()
    observer.schedule(event_handler, str(watch_path), recursive=True)
    observer.start()

    try:
        # Periodically check for pending syncs (due to debouncing)
        while True:
            time.sleep(0.5)
            event_handler.check_pending_sync()
    except KeyboardInterrupt:
        observer.stop()
        print("\n\n👋 Stopping file watcher...")

    observer.join()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Watch for file changes and sync to remote operator"
    )
    parser.add_argument(
        "--context",
        help="The kubectl context to use.",
    )
    parser.add_argument(
        "--namespace",
        "-n",
        help="Namespace to deploy to (defaults to 'dev-<username>').",
    )
    parser.add_argument(
        "--no-logs",
        action="store_true",
        help="Don't stream logs (only watch and sync files).",
    )
    args = parser.parse_args()

    context = args.context or get_current_context()
    namespace = args.namespace or get_default_namespace()

    # Get the operator pod
    pod_name = get_operator_pod(namespace, context)
    print(f"✅ Found operator pod: {pod_name}")

    # Set up the file watcher in a separate thread
    project_root = Path(__file__).parent.parent
    watch_path = project_root / "src"

    if args.no_logs:
        # Just watch files
        watch_files(namespace, pod_name, watch_path)
    else:
        # Watch files in a background thread and stream logs in the main thread
        watcher_thread = threading.Thread(
            target=watch_files,
            args=(namespace, pod_name, watch_path),
            daemon=True
        )
        watcher_thread.start()

        # Stream logs in the main thread
        print("📋 Streaming logs...\n")
        print("=" * 80)
        try:
            stream_logs(namespace)
        except KeyboardInterrupt:
            print("\n\n👋 Stopping...")


if __name__ == "__main__":
    main()
