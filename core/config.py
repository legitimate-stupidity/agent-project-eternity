import yaml
import typer
import httpx
from pathlib import Path
from typing import Any, Dict

DEFAULT_CONFIG = {
    "ollama_config": {
        "host": "http://localhost:11434",
        "generation_model": "llama3:8b",
        "embedding_model": "mxbai-embed-large"
    },
    "database_config": {
        "sqlite_db_path": "workspace/aethelred.db",
        "lancedb_path": "workspace/aethelred.lancedb"
    },
    "services": {
        "ingestor": {
            "poll_interval_seconds": 3600,
            "crawl_targets": []
        },
        "processor": {
            "poll_interval_seconds": 600,
            "annealing_threshold": 0.95
        },
        "api": {
            "host": "0.0.0.0",
            "port": 8000
        }
    }
}

class ConfigManager:
    """Handles loading and saving of agent configuration from config.yml."""
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.config = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        """Loads configuration from YAML file."""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                config_data = yaml.safe_load(f)
                # Recursively merge defaults
                return self._merge_defaults(DEFAULT_CONFIG, config_data)
        return DEFAULT_CONFIG
    
    def _merge_defaults(self, default: Dict, user: Dict) -> Dict:
        """Recursively merges user config into defaults."""
        for key, value in default.items():
            if key not in user:
                user[key] = value
            elif isinstance(value, dict) and isinstance(user.get(key), dict):
                user[key] = self._merge_defaults(value, user.get(key, {}))
        return user

    def save_config(self):
        """Saves current configuration to YAML file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)

    def get(self, *keys: str, default: Any = None) -> Any:
        """Gets a nested configuration value."""
        val = self.config
        for key in keys:
            if isinstance(val, dict):
                val = val.get(key)
            else:
                return default
        return val if val is not None else default

    def set(self, value: Any, *keys: str):
        """Sets a nested configuration value and saves it."""
        d = self.config
        for key in keys[:-1]:
            d = d.setdefault(key, {})
        d[keys[-1]] = value
        self.save_config()

    def ensure_config(self):
        """Ensures essential configuration (Ollama) is present."""
        
        # 1. Ollama Connection
        host = self.get("ollama_config", "host")
        typer.secho(f"Checking Ollama connection at {host}...", fg=typer.colors.CYAN)
        try:
            httpx.get(host)
            typer.secho("Ollama connection successful.", fg=typer.colors.GREEN)
        except httpx.ConnectError:
            typer.secho(f"Error: Cannot connect to Ollama at {host}.", fg=typer.colors.RED, bold=True)
            typer.secho("Please ensure Ollama is running.", fg=typer.colors.RED)
            exit(1)
            
        # Save to create file if it didn't exist
        self.save_config()
