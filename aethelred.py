#!/usr/bin/env python3
"""
Aethelred CLI (v-Eternity)

This is the main user-facing command-line interface for managing
the Aethelred Foundry. It is used to initialize the database
and to launch the individual services (which are managed by launcher.py).
"""

import typer
import uvicorn
import re
from pathlib import Path
from typing_extensions import Annotated

from core.config import ConfigManager
from core.database import DatabaseManager
from brain.foundation_model import FoundationModel
from memory.knowledge_base import KnowledgeBase
from services.ingestor_service import IngestorService
from services.processor_service import ProcessorService
from services.api_service import app as fastapi_app

# --- Component Factory ---

cli = typer.Typer(name="aethelred", help="Aethelred Autonomous Knowledge Foundry CLI")
CONFIG_PATH = Path("./config.yml")

def initialize_components():
    """Initializes and returns all core components."""
    config = ConfigManager(CONFIG_PATH)
    config.ensure_config()
    db = DatabaseManager(config)
    kb = KnowledgeBase(config)
    brain = FoundationModel(config)
    return config, db, kb, brain

# --- CLI Commands ---

@cli.command()
def init():
    """Initializes/Resets the system's databases."""
    typer.secho("Initializing Aethelred Foundry...", fg=typer.colors.BRIGHT_BLUE, bold=True)
    
    config = ConfigManager(CONFIG_PATH)
    config.ensure_config()
    typer.secho(f"Config: {config.config_path.resolve()} (Ensured)", fg=typer.colors.GREEN)

    db = DatabaseManager(config)
    db.init_db(config)
    typer.secho(f"SQLite DB: {db.db_path.resolve()} (Tables Recreated)", fg=typer.colors.GREEN)

    kb = KnowledgeBase(config)
    kb.init_kb()
    typer.secho(f"LanceDB: {kb.db_path.resolve()} (Vector Table Recreated)", fg=typer.colors.GREEN)
    
    typer.secho("Initialization complete.", fg=typer.colors.BRIGHT_GREEN)

@cli.command()
def run_ingestor():
    """Runs the autonomous Ingestor service."""
    typer.secho("[SERVICE] Starting Ingestor Service...", fg=typer.colors.CYAN)
    config, db, _, _ = initialize_components()
    service = IngestorService(config, db)
    service.run_loop()

@cli.command()
def run_processor():
    """Runs the autonomous Processor service."""
    typer.secho("[SERVICE] Starting Processor Service...", fg=typer.colors.CYAN)
    config, db, kb, brain = initialize_components()
    service = ProcessorService(config, db, kb, brain)
    service.run_loop()

@cli.command()
def run_api():
    """Runs the public-facing FastAPI service."""
    typer.secho("[SERVICE] Starting FastAPI Service...", fg=typer.colors.CYAN)
    config, db, kb, brain = initialize_components()
    
    # Inject components into the FastAPI app's state
    fastapi_app.state.config = config
    fastapi_app.state.db = db
    fastapi_app.state.kb = kb
    fastapi_app.state.brain = brain
    
    host = config.get("services", "api", "host")
    port = config.get("services", "api", "port")
    
    typer.secho(f"FastAPI running on http://{host}:{port}", fg=typer.colors.GREEN)
    uvicorn.run(fastapi_app, host=host, port=port)

@cli.command()
def add_target(url: Annotated[str, typer.Argument(help="The URL to add to the crawl list.")]):
    """Adds a new URL target for the Ingestor to crawl."""
    config, db, _, _ = initialize_components()
    try:
        db.add_crawl_target(url)
        typer.secho(f"Successfully added new crawl target: {url}", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"Error adding target: {e}", fg=typer.colors.RED)

if __name__ == "__main__":
    cli()
