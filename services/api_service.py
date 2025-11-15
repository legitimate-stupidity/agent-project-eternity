import typer
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

# We create the app instance here, but it's populated
# and run by the `aethelred.py` CLI.

app = FastAPI(
    title="Aethelred Knowledge Foundry",
    description="Query the autonomous, self-accreting knowledge base.",
    version="1.0.0"
)

class QueryRequest(BaseModel):
    query: str
    k: int = 5

class QueryResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]

@app.post("/query", response_model=QueryResponse)
async def handle_query(request: Request, body: QueryRequest):
    """
    Handle a user query.
    1. Embeds the query.
    2. Searches the KnowledgeBase for relevant chunks.
    3. Uses the FoundationModel (LLM) to synthesize an answer (RAG).
    """
    typer.secho(f"[API] Received query: '{body.query[:50]}...'", fg=typer.colors.BRIGHT_BLUE)
    
    # Get components injected by the CLI
    kb = request.app.state.kb
    brain = request.app.state.brain
    
    if not kb or not brain:
        raise HTTPException(status_code=500, detail="Server components not initialized.")

    try:
        # 1. Search for relevant chunks
        source_chunks = kb.query_knowledge(body.query, k=body.k)
        
        if not source_chunks:
            return QueryResponse(
                answer="I found no relevant information in the knowledge base to answer that query.",
                sources=[]
            )
        
        # 2. Generate answer
        context_summaries = [chunk['text'] for chunk in source_chunks]
        answer = brain.answer_query(body.query, context_summaries)
        
        # 3. Format sources for response
        sources_response = [
            {
                "title": chunk['title'],
                "url": chunk['url'],
                "summary": chunk['text'],
                "entities": chunk['entities']
            } for chunk in source_chunks
        ]
        
        return QueryResponse(answer=answer, sources=sources_response)

    except Exception as e:
        typer.secho(f"[API] Error processing query: {e}", fg=typer.colors.RED)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    """Simple health check endpoint."""
    return {"status": "ok"}
