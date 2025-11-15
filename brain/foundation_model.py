import httpx
import typer
import json
from typing import List, Dict, Optional, Any

from core.config import ConfigManager

class FoundationModel:
    """
    A wrapper for the Ollama LLM, handling generation,
    JSON formatting, and error handling.
    """
    
    SYSTEM_PROMPT = """
You are an elite, autonomous AI Processor. Your goal is to
analyze, summarize, and synthesize knowledge. You will be given
context and a task, and you must respond *only* in the
requested format (e.g., JSON) with no conversational fluff.
"""

    def __init__(self, config: ConfigManager):
        self.config = config
        self.api_url = f"{config.get('ollama_config', 'host')}/api/chat"
        self.model = config.get('ollama_config', 'generation_model')
        self.client = httpx.Client(timeout=120.0)

    def _call_ollama(self, user_prompt: str, system_prompt: str, use_json: bool = False) -> Optional[str]:
        """Makes a synchronous call to the Ollama /api/chat endpoint."""
        typer.secho(f"   [BRAIN] Thinking (Model: {self.model}, JSON: {use_json})...", fg=typer.colors.MAGENTA, dim=True)
        
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
        payload = {"model": self.model, "messages": messages, "stream": False}
        if use_json:
            payload["format"] = "json"
        
        try:
            response = self.client.post(self.api_url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data['message']['content'].strip()
        except Exception as e:
            typer.secho(f"   [BRAIN] Critical Error: {e}", fg=typer.colors.RED, bold=True)
            return None

    def process_text_chunk(self, text_chunk: str, url: str) -> Optional[Dict[str, Any]]:
        """
        Uses the LLM to process a raw text chunk into structured knowledge.
        Returns a dictionary with 'summary', 'entities', and 'title'.
        """
        prompt = f"""
        You will be given a chunk of raw text from the URL: {url}
        Your task is to analyze the text and return a JSON object with three keys:
        1. "title": A concise, descriptive title for this text chunk.
        2. "summary": A dense, one-paragraph summary of the key information.
        3. "entities": A list of the 5-10 most important keywords or entities (people, places, concepts, technologies).
        
        Respond *only* with the valid JSON object.
        
        RAW TEXT CHUNK:
        ---
        {text_chunk}
        ---
        """
        
        response_text = self._call_ollama(user_prompt=prompt, system_prompt=self.SYSTEM_PROMPT, use_json=True)
        if not response_text:
            return None
        
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            typer.secho(f"   [BRAIN] Failed to parse JSON from LLM response.", fg=typer.colors.YELLOW)
            return None

    def answer_query(self, query: str, context_chunks: List[str]) -> str:
        """
        Uses the LLM to generate a final answer based on a query and
        retrieved knowledge (RAG).
        """
        context_str = "\n\n---\n\n".join(context_chunks)
        
        prompt = f"""
        You are an Answer Generation Agent. You will be given a
        user query and a set of "context" chunks retrieved from the
        knowledge base. Your task is to synthesize this information
        to provide a single, clear, and comprehensive answer to
        the user's query.
        
        - Base your answer *only* on the provided context.
        - Do not add information that is not in the context.
        - If the context does not contain the answer, state that.
        
        USER QUERY:
        {query}
        
        RETRIEVED CONTEXT:
        ---
        {context_str}
        ---
        
        ANSWER:
        """
        
        response = self._call_ollama(user_prompt=prompt, system_prompt=self.SYSTEM_PROMPT, use_json=False)
        return response if response else "I am sorry, I was unable to process that request."
