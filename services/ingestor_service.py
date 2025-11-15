import typer
import time
import httpx
import re
from bs4 import BeautifulSoup
from typing import Optional

from core.config import ConfigManager
from core.database import DatabaseManager

class IngestorService:
    """
    Autonomous agent service.
    Polls the DB for 'pending' crawl targets and ingests their
    raw text content, placing it in the 'raw_content' queue.
    """
    def __init__(self, config: ConfigManager, db: DatabaseManager):
        self.config = config
        self.db = db
        self.poll_interval = config.get("services", "ingestor", "poll_interval_seconds")
        self.client = httpx.Client(follow_redirects=True, timeout=30.0)
        typer.secho(f"[Ingestor] Service initialized. Poll interval: {self.poll_interval}s", fg=typer.colors.GREEN)

    def fetch_url(self, url: str) -> Optional[str]:
        """Fetches the raw text content from a URL."""
        try:
            headers = {
                'User-Agent': 'Aethelred-Knowledge-Ingestor/1.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
            }
            response = self.client.get(url, headers=headers)
            response.raise_for_status()
            
            # Use BeautifulSoup to parse HTML and extract text
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script_or_style in soup(["script", "style"]):
                script_or_style.decompose()
            
            text = soup.get_text(separator='\n', strip=True)
            
            # Clean up excessive newlines
            return re.sub(r'\n{3,}', '\n\n', text)
            
        except httpx.HTTPStatusError as e:
            typer.secho(f"  [Ingestor] HTTP Error fetching {url}: {e}", fg=typer.colors.RED)
            return None
        except Exception as e:
            typer.secho(f"  [Ingestor] General Error fetching {url}: {e}", fg=typer.colors.RED)
            return None

    def run_sweep(self):
        """Runs a single sweep to find and ingest a pending target."""
        typer.secho("\n[Ingestor] Running sweep...", fg=typer.colors.CYAN)
        
        target = self.db.get_next_crawl_target()
        if not target:
            typer.secho("  [Ingestor] No pending targets found.", dim=True)
            return

        typer.secho(f"  [Ingestor] Fetching target {target['id']}: {target['url']}", fg=typer.colors.WHITE)
        self.db.update_crawl_target_status(target['id'], 'active')
        
        raw_text = self.fetch_url(target['url'])
        
        if raw_text:
            typer.secho(f"  [Ingestor] Fetched {len(raw_text)} bytes. Adding to processing queue.", fg=typer.colors.GREEN)
            self.db.add_raw_content(target['id'], target['url'], raw_text)
            self.db.update_crawl_target_status(target['id'], 'completed')
        else:
            typer.secho(f"  [Ingestor] Fetch failed. Marking target as 'failed'.", fg=typer.colors.YELLOW)
            self.db.update_crawl_target_status(target['id'], 'failed')

    def run_loop(self):
        """Runs the autonomous ingestor loop."""
        while True:
            self.run_sweep()
            typer.secho(f"  [Ingestor] Sweep complete. Sleeping for {self.poll_interval}s...", dim=True)
            time.sleep(self.poll_interval)
