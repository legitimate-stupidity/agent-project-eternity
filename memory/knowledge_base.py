import lancedb
import typer
import shutil
from pathlib import Path
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from core.config import ConfigManager

class KnowledgeBase:
    """
    Handles all interactions with the LanceDB vector database.
    Manages embedding, storage, querying, and annealing.
    """
    def __init__(self, config: ConfigManager):
        self.db_path = Path(config.get("database_config", "lancedb_path"))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = lancedb.connect(self.db_path)
        
        model_name = config.get("ollama_config", "embedding_model")
        typer.secho(f"  [KB] Loading embedding model: {model_name}...", dim=True)
        self.model = SentenceTransformer(model_name, device='cpu')
        typer.secho("  [KB] Embedding model loaded.", dim=True)
        
        self.table_name = "knowledge"
        self.annealing_threshold = config.get("services", "processor", "annealing_threshold")
        self.table = self.init_kb()


    def init_kb(self):
        """Initializes or opens the vector database table."""
        try:
            # Drop table if it exists
            self.db.drop_table(self.table_name)
            typer.secho(f"  [KB] Dropped existing table '{self.table_name}'.", dim=True)
        except Exception:
            pass # Table didn't exist, which is fine

        typer.secho(f"  [KB] Creating new table '{self.table_name}'.", dim=True)
        
        # Create sample data for schema inference
        sample_vector = self.model.encode("test").tolist()
        sample_data = [{
            "vector": sample_vector,
            "text": "This is a test chunk.",
            "url": "http://example.com",
            "title": "Example",
            "entities": "example, test"
        }]
        
        return self.db.create_table(self.table_name, data=sample_data)

    def embed_text(self, text: str) -> List[float]:
        """Creates a vector embedding for a text chunk."""
        return self.model.encode(text).tolist()

    def add_knowledge(self, processed_data: Dict[str, Any], vector: List[float]):
        """Adds a new, processed knowledge chunk to the database."""
        data = {
            "vector": vector,
            "text": processed_data['summary'],
            "url": processed_data['url'],
            "title": processed_data['title'],
            "entities": ", ".join(processed_data['entities']) # Store as string
        }
        self.table.add([data])

    def query_knowledge(self, query_text: str, k: int = 5) -> List[Dict[str, Any]]:
        """Queries the vector DB for the top-k most relevant chunks."""
        query_vector = self.embed_text(query_text)
        results = self.table.search(query_vector).limit(k).to_list()
        return results
        
    def check_for_contradiction(self, new_vector: List[float]) -> bool:
        """
        Checks if a new vector contradicts or is too similar to
        existing knowledge, based on the annealing threshold.
        """
        # Search for the single most similar chunk
        try:
            results = self.table.search(new_vector).limit(1).to_list()
            if not results or len(results[0]['vector']) == 0:
                return False # No existing knowledge, cannot contradict
        except Exception as e:
            # This can happen if the table is empty (e.g., only sample data)
            typer.secho(f"  [KB] Warning: Search failed, assuming no contradiction. Error: {e}", dim=True)
            return False

        nearest_chunk = results[0]
        
        # Calculate cosine similarity
        existing_vector = nearest_chunk['vector']
        similarity = cosine_similarity(
            np.array(new_vector).reshape(1, -1),
            np.array(existing_vector).reshape(1, -1)
        )[0][0]
        
        if similarity > self.annealing_threshold:
            typer.secho(f"  [KB] Knowledge Annealing: New chunk similarity {similarity:.2f} exceeds threshold.", fg=typer.colors.YELLOW)
            typer.secho(f"  [KB] >  New:     '{nearest_chunk['title']}'", fg=typer.colors.YELLOW, dim=True)
            typer.secho(f"  [KB] >  Similar: '{nearest_chunk['title']}' ({nearest_chunk['url']})", fg=typer.colors.YELLOW, dim=True)
            return True # It's a duplicate/contradiction
            
        return False
