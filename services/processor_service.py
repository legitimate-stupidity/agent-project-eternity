import typer
import time
from typing import Optional, Dict, Any

from core.config import ConfigManager
from core.database import DatabaseManager
from brain.foundation_model import FoundationModel
from memory.knowledge_base import KnowledgeBase

class ProcessorService:
    """
    Autonomous agent service.
    Polls the DB for 'pending' raw content, uses the LLM to
    process it, and inserts it into the vector KnowledgeBase.
    """
    def __init__(self, config: ConfigManager, db: DatabaseManager, kb: KnowledgeBase, brain: FoundationModel):
        self.config = config
        self.db = db
        self.kb = kb
        self.brain = brain
        self.poll_interval = config.get("services", "processor", "poll_interval_seconds")
        typer.secho(f"[Processor] Service initialized. Poll interval: {self.poll_interval}s", fg=typer.colors.GREEN)

    def process_chunk(self, content: Dict[str, Any]) -> bool:
        """Processes a single raw text chunk."""
        
        # 1. Use LLM to extract knowledge
        typer.secho(f"  [Processor] Processing chunk {content['id']} from {content['url']}...", fg=typer.colors.WHITE)
        processed_data = self.brain.process_text_chunk(content['raw_text'], content['url'])
        
        if not processed_data:
            typer.secho(f"  [Processor] Brain failed to process chunk {content['id']}.", fg=typer.colors.RED)
            return False
        
        processed_data['url'] = content['url'] # Ensure URL is passed through
        
        # 2. Create vector embedding
        typer.secho(f"  [Processor] Embedding processed chunk...", dim=True)
        vector = self.kb.embed_text(processed_data['summary'])
        
        # 3. Check for contradictions/duplicates
        if self.kb.check_for_contradiction(vector):
            typer.secho(f"  [Processor] Chunk {content['id']} is a duplicate/contradiction. Discarding.", fg=typer.colors.YELLOW)
            return True # Mark as "processed" even if discarded
        
        # 4. Add to KnowledgeBase
        typer.secho(f"  [Processor] Adding new knowledge to vector DB.", fg=typer.colors.GREEN)
        self.kb.add_knowledge(processed_data, vector)
        
        return True

    def run_sweep(self):
        """Runs a single sweep to find and process pending content."""
        typer.secho("\n[Processor] Running sweep...", fg=typer.colors.CYAN)
        
        content = self.db.get_next_raw_content()
        if not content:
            typer.secho("  [Processor] No pending content found.", dim=True)
            return

        typer.secho(f"  [Processor] Processing content {content['id']}...", fg=typer.colors.WHITE)
        
        try:
            if self.process_chunk(content):
                self.db.update_raw_content_status(content['id'], 'processed')
            else:
                self.db.update_raw_content_status(content['id'], 'failed')
        except Exception as e:
            typer.secho(f"  [Processor] CRITICAL failure processing {content['id']}: {e}", fg=typer.colors.RED, bold=True)
            self.db.update_raw_content_status(content['id'], 'failed')

    def run_loop(self):
        """Runs the autonomous processor loop."""
        while True:
            self.run_sweep()
            typer.secho(f"  [Processor] Sweep complete. Sleeping for {self.poll_interval}s...", dim=True)
            time.sleep(self.poll_interval)
