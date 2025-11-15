#!/usr/bin/env python3
"""
Aethelred Launcher (v-Prime)

This is the immutable "Core" Process Manager.
Its sole purpose is to boot, monitor, and gracefully restart
all autonomous services that form the Aethelred Foundry.
"""

import typer
import subprocess
import time
import sys
from typing import List, Dict

# Define the services to be managed
SERVICES = [
    {"name": "Ingestor", "command": ["python3", "aethelred.py", "run-ingestor"]},
    {"name": "Processor", "command": ["python3", "aethelred.py", "run-processor"]},
    {"name": "API", "command": ["python3", "aethelred.py", "run-api"]},
]

class ServiceManager:
    """Manages the lifecycle of all autonomous agent services."""
    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}
        typer.secho("--- [LAUNCHER] Initializing Aethelred Foundry ---", fg=typer.colors.BRIGHT_MAGENTA, bold=True)

    def start_all(self):
        """Starts all defined services as subprocesses."""
        for service in SERVICES:
            name = service["name"]
            command = service["command"]
            try:
                typer.secho(f"[LAUNCHER] Starting service: {name}...", fg=typer.colors.CYAN)
                # We pipe stdout and stderr to the launcher's stdout
                p = subprocess.Popen(command, stdout=sys.stdout, stderr=subprocess.STDOUT)
                self.processes[name] = p
            except Exception as e:
                typer.secho(f"[LAUNCHER] FATAL: Failed to start {name}: {e}", fg=typer.colors.RED, bold=True)

    def monitor_and_restart(self):
        """Monitors all services and restarts any that fail."""
        try:
            while True:
                time.sleep(10) # Check every 10 seconds
                for service in SERVICES:
                    name = service["name"]
                    command = service["command"]
                    
                    if name not in self.processes or self.processes[name].poll() is not None:
                        # Process is dead or was never started
                        typer.secho(f"[LAUNCHER] Service '{name}' is down. Restarting...", fg=typer.colors.YELLOW, bold=True)
                        try:
                            p = subprocess.Popen(command, stdout=sys.stdout, stderr=subprocess.STDOUT)
                            self.processes[name] = p
                        except Exception as e:
                            typer.secho(f"[LAUNCHER] FATAL: Failed to restart {name}: {e}", fg=typer.colors.RED, bold=True)

        except KeyboardInterrupt:
            typer.secho("\n[LAUNCHER] Shutdown signal received. Terminating all services...", fg=typer.colors.RED)
            self.stop_all()

    def stop_all(self):
        """Stops all running services gracefully."""
        for name, p in self.processes.items():
            if p.poll() is None: # If process is still running
                typer.secho(f"[LAUNCHLER] Stopping {name} (PID: {p.pid})...", fg=typer.colors.RED)
                p.terminate()
                try:
                    p.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    typer.secho(f"[LAUNCHER] {name} did not terminate gracefully. Forcing kill.", fg=typer.colors.YELLOW)
                    p.kill()
        typer.secho("[LAUNCHER] All services shut down. Exiting.", fg=typer.colors.WHITE)

def main():
    manager = ServiceManager()
    manager.start_all()
    manager.monitor_and_restart()

if __name__ == "__main__":
    typer.run(main)
