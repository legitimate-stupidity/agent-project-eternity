# (Project Eternity)
## A Self-Accreting Universal Knowledge Base

Eternity is an autonomous multi-agent system designed to build and serve an ever-evolving knowledge base. It ingests data from specified sources, processes it for contradictions and novelty, indexes it, and serves it via a public query API.

The system is the product of a 3-eon optimization process, evolving from a monolithic reactive LLM (T-0) to a proactive, self-healing multi-agent architecture (T-3eons). This is a fully autonomous knowledge foundry.

---

## 🏗️ Architecture Overview

Eternity is a **distributed microservice system** with three autonomous agents orchestrated by a central launcher:

```
┌─────────────────────────────────────────────────┐
│         Launcher (launcher.py)                  │
│    Core Process Manager & Service Monitor       │
└─────────────────────────────────────────────────┘
         ↓          ↓          ↓
    ┌────────┬──────────┬──────────┐
    ↓        ↓          ↓
┌─────────┐ ┌──────────┐ ┌─────────┐
│Ingestor │ │Processor │ │   API   │
│ Agent   │ │  Agent   │ │ Server  │
└─────────┘ └──────────┘ └─────────┘
```

### Core Components

1. **Launcher (`launcher.py`)**
   - Immutable "Core" process manager
   - Boots all autonomous services as subprocesses
   - Continuously monitors health and automatically restarts failed services
   - Graceful shutdown with SIGTERM/SIGKILL fallback

2. **CLI (`aethelred.py`)**
   - User-facing command-line interface for system management
   - Initializes databases (SQLite + LanceDB)
   - Launches individual services for development/testing
   - Adds new crawl targets to the ingestion queue

3. **Ingestor Service (`services/ingestor_service.py`)**
   - **Role:** Autonomous web crawler and content extractor
   - **Input:** URLs from the crawl_targets queue
   - **Process:**
     - Fetches raw HTML content from target URLs
     - Parses HTML with BeautifulSoup
     - Extracts clean text (removes scripts, styles, excess whitespace)
     - Places raw content into the processing queue
   - **Poll Interval:** Configurable (default: 1 hour)

4. **Processor Service (`services/processor_service.py`)**
   - **Role:** The "brain" of the system—knowledge extraction and validation
   - **Input:** Raw text chunks from the ingestor queue
   - **Process:**
     1. Uses LLM (Ollama) to summarize and extract key entities
     2. Generates a dense one-paragraph summary
     3. Creates vector embeddings using sentence-transformers
     4. Checks for contradictions/duplicates via cosine similarity annealing
     5. Inserts novel knowledge into the vector database
   - **Annealing:** Rejects knowledge chunks that are >95% similar to existing chunks
   - **Poll Interval:** Configurable (default: 10 minutes)

5. **API Service (`services/api_service.py`)**
   - **Role:** Public query interface with Retrieval-Augmented Generation (RAG)
   - **Framework:** FastAPI + Uvicorn
   - **Endpoints:**
     - `POST /query` - Main query interface
       - Input: `{"query": "...", "k": 5}`
       - Output: Answer + sources (title, URL, summary, entities)
     - `GET /health` - Health check
   - **RAG Pipeline:**
     1. Embeds user query
     2. Searches vector database for top-k relevant chunks
     3. Uses LLM to synthesize final answer from context
     4. Returns answer with source attribution

---

## 📊 Data Flow

```
Internet URLs
    ↓
[Ingestor] → raw_content table (SQLite)
    ↓
[Processor] → LLM Processing
    ↓
[Vector DB] (LanceDB) ← Annealing (contradiction detection)
    ↓
[API Service] ← Query Embedding & RAG
    ↓
User Answer
```

### Database Schema

**SQLite** (`workspace/aethelred.db`):
- `crawl_targets`: URLs to ingest (id, url, status, last_crawled_timestamp)
- `raw_content`: Raw fetched text waiting for processing (id, target_id, url, raw_text, status, creation_timestamp)

**LanceDB** (`workspace/aethelred.lancedb`):
- `knowledge` table: Vector embeddings of processed knowledge chunks
  - Fields: `vector` (embedding), `text` (summary), `url`, `title`, `entities`

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **Ollama** running locally (for LLM inference)
- **Ollama models:**
  - `llama3:8b` (generation/reasoning)
  - `mxbai-embed-large` (vector embeddings)

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd agent-project-eternity
   ```

2. **Create a Python virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Ensure Ollama is running:**
   ```bash
   # In a separate terminal
   ollama serve
   
   # Pull models if not already present
   ollama pull llama3:8b
   ollama pull mxbai-embed-large
   ```

5. **Verify Ollama connection:**
   ```bash
   curl http://localhost:11434
   ```

### Configuration

Edit `config.yml` to customize:

```yaml
ollama_config:
  host: "http://localhost:11434"
  generation_model: "llama3:8b"
  embedding_model: "mxbai-embed-large"

database_config:
  sqlite_db_path: "workspace/aethelred.db"
  lancedb_path: "workspace/aethelred.lancedb"

services:
  ingestor:
    poll_interval_seconds: 3600  # 1 hour
    crawl_targets:
      - "https://www.digitalocean.com/community/tutorials"
      - "https://www.rust-lang.org/learn"
  
  processor:
    poll_interval_seconds: 600   # 10 minutes
    annealing_threshold: 0.95    # Similarity threshold for deduplication
  
  api:
    host: "0.0.0.0"
    port: 8000
```

### Usage

#### Initialize the System (One-Time Setup)

```bash
python3 aethelred.py init
```

This will:
- Verify Ollama connection
- Create/reset SQLite database with schema
- Create/reset LanceDB vector table
- Load embedding models

#### Run the Full Foundry

```bash
python3 launcher.py
```

This launches all three services (Ingestor, Processor, API) and monitors them continuously.

#### Individual Service Development

```bash
# Terminal 1: Ingestor
python3 aethelred.py run-ingestor

# Terminal 2: Processor
python3 aethelred.py run-processor

# Terminal 3: API
python3 aethelred.py run-api
```

#### Add New Crawl Targets

```bash
python3 aethelred.py add-target "https://example.com"
python3 aethelred.py add-target "https://another-site.org/docs"
```

---

## 🔍 Usage Examples

### Querying the Knowledge Base

Once the system is running, you can query it via the FastAPI endpoint:

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "How do I install Python on Ubuntu?", "k": 5}'
```

**Response:**
```json
{
  "answer": "To install Python on Ubuntu, you can use the apt package manager. First, update your package lists with `sudo apt update`, then install Python with `sudo apt install python3`. You can verify the installation by running `python3 --version`.",
  "sources": [
    {
      "title": "Python Installation Guide",
      "url": "https://www.digitalocean.com/community/tutorials/...",
      "summary": "This guide covers installing Python on Linux systems...",
      "entities": "Python, Ubuntu, apt, installation, Linux"
    },
    {
      "title": "Ubuntu Package Management",
      "url": "https://example.com/apt-guide",
      "summary": "Learn how to use apt to install packages on Ubuntu...",
      "entities": "Ubuntu, apt, package manager, installation"
    }
  ]
}
```

### Health Check

```bash
curl http://localhost:8000/health
# Returns: {"status": "ok"}
```

---

## 📈 How It Works: The Three Agents

### 1. Ingestor Agent (Data Acquisition)

```
Poll database every hour
    ↓
Find next 'pending' crawl target
    ↓
Fetch URL (with proper User-Agent header)
    ↓
Parse HTML and extract clean text
    ↓
Store in raw_content table
    ↓
Mark target as 'completed' or 'failed'
    ↓
Sleep and repeat
```

**Error Handling:**
- HTTP errors (404, 403, etc.) → mark target as 'failed'
- Connection timeouts → mark target as 'failed'
- Invalid URLs → mark target as 'failed'

### 2. Processor Agent (Knowledge Synthesis)

```
Poll database every 10 minutes
    ↓
Find next 'pending' raw content chunk
    ↓
Send to LLM for processing
    ↓
LLM returns: {title, summary, entities}
    ↓
Create vector embedding of summary
    ↓
Check similarity against existing knowledge
    ↓
If similarity > threshold (0.95):
    Discard as duplicate
Else:
    Add to vector database
    ↓
Mark content as 'processed' or 'failed'
    ↓
Sleep and repeat
```

**Knowledge Annealing:**
Uses cosine similarity in vector space to detect and reject:
- Exact duplicates
- Contradictory information
- Highly similar (>95%) existing knowledge

### 3. API Agent (Query Interface)

```
User sends query
    ↓
Embed query text
    ↓
Search vector DB for top-5 similar chunks
    ↓
Retrieve source texts
    ↓
Build RAG context prompt
    ↓
Send to LLM for synthesis
    ↓
LLM generates answer
    ↓
Return answer + attribution
```

---

## 🧠 Core Modules

### `core/config.py` - ConfigManager
- Loads configuration from `config.yml`
- Merges user config with defaults
- Validates Ollama connection
- Provides nested key access: `config.get("services", "api", "port")`

### `core/database.py` - DatabaseManager
- Manages SQLite connection and schema
- Task queue operations (add, get, update)
- Status tracking for crawl targets and raw content

### `brain/foundation_model.py` - FoundationModel
- Wrapper around Ollama HTTP API
- JSON formatting and error handling
- Two main methods:
  - `process_text_chunk()` - Extracts knowledge
  - `answer_query()` - Generates RAG answers

### `memory/knowledge_base.py` - KnowledgeBase
- LanceDB vector database interface
- Embedding generation (sentence-transformers)
- Vector search and similarity checking
- Contradiction/annealing detection

---

## 📋 Dependencies

All dependencies are in `requirements.txt`:

```
typer[all]           # CLI framework
httpx                # Async HTTP client
lancedb              # Vector database
sentence-transformers # Embedding models
pyyaml               # YAML config parsing
fastapi              # Web framework
uvicorn              # ASGI server
beautifulsoup4       # HTML parsing
scikit-learn         # Cosine similarity
```

---

## 🔧 Advanced Configuration

### Custom Models

To use different Ollama models:

```yaml
ollama_config:
  generation_model: "mistral:7b"  # Faster, smaller
  embedding_model: "all-minilm"    # Lighter embeddings
```

### Database Paths

Store databases in a custom location:

```yaml
database_config:
  sqlite_db_path: "/mnt/data/aethelred.db"
  lancedb_path: "/mnt/data/aethelred.lancedb"
```

### Crawl Targets

Add targets dynamically:

```bash
python3 aethelred.py add-target "https://docs.example.com"
python3 aethelred.py add-target "https://blog.site.org"
```

Or edit `config.yml` directly:

```yaml
services:
  ingestor:
    crawl_targets:
      - "https://source1.com"
      - "https://source2.com"
      - "https://source3.com"
```

### Annealing Threshold

Adjust knowledge deduplication sensitivity (0.0-1.0):

```yaml
services:
  processor:
    annealing_threshold: 0.90  # More aggressive deduplication
```

---

## 🐛 Troubleshooting

### Ollama Connection Error

```
Error: Cannot connect to Ollama at http://localhost:11434.
Please ensure Ollama is running.
```

**Fix:**
```bash
# Start Ollama in a separate terminal
ollama serve

# Verify connection
curl http://localhost:11434
```

### Missing Models

```
Error: model not found
```

**Fix:**
```bash
ollama pull llama3:8b
ollama pull mxbai-embed-large
```

### Database Lock

If SQLite reports "database is locked":
- Ensure only one process is accessing the database
- Check for stale processes: `ps aux | grep aethelred.py`
- Restart the system: `python3 aethelred.py init`

### Vector DB Issues

If LanceDB encounters errors:
```bash
# Reinitialize (WARNING: wipes existing knowledge)
python3 aethelred.py init
```

### Slow Processing

If the processor is slow:
- Reduce model size: use `mistral:7b` instead of `llama3:8b`
- Increase `poll_interval_seconds` to give it more thinking time
- Reduce `k` in query requests

---

## 📊 Monitoring

Check service logs by running in separate terminals:

```bash
# Terminal 1: Watch ingestor
python3 aethelred.py run-ingestor

# Terminal 2: Watch processor
python3 aethelred.py run-processor

# Terminal 3: Watch API
python3 aethelred.py run-api
```

All services print colored output to stdout for easy debugging.

---

## 🎯 Design Philosophy

**The T-3eons Architecture:**

- **Autonomous:** Each service runs independently with no manual intervention
- **Self-Healing:** The launcher automatically restarts failed services
- **Proactive:** Knowledge synthesis happens continuously, not on-demand
- **Annealing:** The system "cools" contradictory information through similarity checking
- **Scalable:** Add new crawl targets and the system ingests them automatically

The architecture evolved from a monolithic reactive LLM (T-0) to this distributed, autonomous, knowledge-building system (T-3eons).

---

## 📝 License

See LICENSE file.

---

## 🤝 Contributing

Contributions welcome! Areas for expansion:
- Additional content sources (RSS, databases, APIs)
- Alternative embedding models
- Multi-language support
- Distributed processing
- Web UI for management

---

## 📞 Support

For issues or questions:
1. Check troubleshooting section above
2. Review service logs for error messages
3. Ensure all dependencies are installed correctly
4. Verify Ollama is running and models are available
