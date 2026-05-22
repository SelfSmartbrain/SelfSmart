# 🧠 SelfSmart AI

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-16.2-000000?style=for-the-badge&logo=next.js&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-FF6B35?style=for-the-badge)
![Redis](https://img.shields.io/badge/Redis-Cache_&_Queue-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**A production-grade, continuously learning AI platform powered by RAG, LLM fine-tuning, and real-time knowledge ingestion.**

[Live Demo](#) · [API Docs](http://localhost:8000/docs) · [Architecture](./ARCHITECTURE.md) · [Deployment Guide](./DEPLOYMENT.md)

</div>

---

## 📌 What Is SelfSmart?

SelfSmart is **not a chatbot wrapper**. It is an end-to-end AI system engineered to solve a fundamental limitation of static LLMs: **they stop learning the moment training ends**.

SelfSmart closes this gap with a continuously running knowledge pipeline — crawling the web, ingesting RSS feeds, processing PDFs and YouTube transcripts, ranking content for quality, embedding it into a vector store, and serving grounded, streaming responses through a RAG-backed LLM interface.

> **Core Thesis:** An intelligent assistant should get smarter every day — not just through prompts, but through structured, autonomous learning from the world.

---

## ✅ What Is Working Right Now

| Feature | Status | Details |
|---|---|---|
| 🔴 Streaming Chat (SSE) | ✅ **Live** | Real-time token-by-token streaming via `/api/chat/stream` |
| 🧠 RAG Pipeline | ✅ **Live** | ChromaDB vector search + semantic retrieval for grounded answers |
| 🌐 Web Crawler | ✅ **Live** | Async multi-source crawling with rate limiting and quality filtering |
| 📡 RSS Feed Ingestion | ✅ **Live** | Continuous feed ingestion via `feedparser` |
| 🎥 YouTube Transcript Ingestion | ✅ **Live** | Auto-extract transcripts and embed into knowledge base |
| 📄 PDF Knowledge Ingestion | ✅ **Live** | PDF parsing and chunking via `pypdf` |
| 🔄 Continuous Learning Loop | ✅ **Live** | Start/stop via API; runs autonomously on schedule |
| 💬 Conversation Manager | ✅ **Live** | Multi-session history, persistence, context injection |
| 🤖 Multi-LLM Support | ✅ **Live** | Gemini & DeepSeek backends; pluggable client interface |
| 🗃️ Vector Store | ✅ **Live** | ChromaDB for embeddings; `sentence-transformers` for encoding |
| 📊 Stats & Health APIs | ✅ **Live** | `/api/stats`, `/health`, `/status` endpoints |
| 🏋️ LLM Fine-tuning | ✅ **Live** | LoRA/QLoRA training pipeline + Kaggle/cloud notebooks |
| 🐳 Docker Deployment | ✅ **Live** | Single `Dockerfile` for backend containerization |
| 🌐 Next.js Frontend | ✅ **Live** | Chat UI + dashboard built with Next.js 16, Tailwind, ShadCN |
| 📈 Prometheus Metrics | ✅ **Live** | Instrumented with `prometheus-client` + `structlog` |
| 🔐 Auth & Security | ✅ **Live** | JWT via `python-jose`, bcrypt password hashing |
| 🗄️ Knowledge Graph | ✅ **Live** | `neo4j` + `networkx` for entity relationship mapping |
| ⚙️ Task Queue | ✅ **Live** | Celery + Redis for async task processing and scheduling |

---

## 🏗️ System Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                        SELFSMART AI PLATFORM                       │
├───────────────┬────────────────────────┬───────────────────────────┤
│   FRONTEND    │      BACKEND (FastAPI)  │     ML / AI PIPELINE      │
│  (Next.js 16) │                        │                           │
│               │  • REST + SSE Streams  │  • RAG Service (ChromaDB) │
│  • Chat UI    │  • Conversation Mgmt   │  • Embedding Pipeline     │
│  • Dashboard  │  • Auth (JWT/bcrypt)   │  • LLM Clients (Gemini,   │
│  • Stats View │  • Multi-LLM Routing   │    DeepSeek)              │
│  • ShadCN UI  │  • Async Task Dispatch │  • LoRA Fine-Tuning       │
│               │  • Prometheus Metrics  │  • RAG Evaluator          │
└───────┬───────┴────────────┬───────────┴──────────┬────────────────┘
        │                    │                       │
        ▼                    ▼                       ▼
┌──────────────┐   ┌─────────────────┐   ┌─────────────────────────┐
│   Zustand    │   │  SQLite (dev)   │   │  ChromaDB Vector Store  │
│ (State Mgmt) │   │  PostgreSQL     │   │  sentence-transformers  │
└──────────────┘   │  (production)   │   │  FAISS (optional)       │
                   └─────────────────┘   └─────────────────────────┘
                            │
                   ┌─────────────────┐
                   │  Redis + Celery │
                   │  (Task Queue)   │
                   └─────────────────┘
                            │
          ┌─────────────────┴─────────────────────────┐
          │             KNOWLEDGE PIPELINE             │
          │                                           │
          │  Web Crawler → RSS Feeds → PDF Parser     │
          │  YouTube Transcripts → Wikipedia          │
          │  Free Public APIs → Content Processor     │
          │  Quality Scoring → Embedding → VectorDB   │
          └───────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

### Backend
| Layer | Technology | Purpose |
|---|---|---|
| Web Framework | **FastAPI 0.104** | Async REST API, SSE streaming, auto-generated OpenAPI docs |
| Data Validation | **Pydantic v2** | Schema enforcement, settings management |
| ORM | **SQLAlchemy 2.0** + Alembic | Database abstraction, schema migrations |
| Database | **SQLite** (dev) / **PostgreSQL** (prod) | Persistent storage |
| Task Queue | **Celery 5.3** + **Redis 5** | Async job processing, scheduled learning loops |
| Monitoring | **Prometheus** + **structlog** + **Sentry** | Observability, structured logging, error tracking |
| Security | **python-jose** (JWT) + **passlib** (bcrypt) | Auth tokens, password hashing |

### AI / ML
| Layer | Technology | Purpose |
|---|---|---|
| LLM (Hosted) | **Gemini** / **DeepSeek** | Conversational generation via API |
| LLM (Local) | **PyTorch 2.0+** + **Transformers 4.35** | Custom/fine-tuned model inference |
| Fine-Tuning | **LoRA / QLoRA** + **datasets** + **W&B** | Parameter-efficient fine-tuning + experiment tracking |
| Embeddings | **sentence-transformers 2.2** | Semantic vector encoding |
| Vector Store | **ChromaDB 0.4** | Persistent vector similarity search |
| NLP | **spaCy 3.6** + **TextBlob** | Named entity recognition, sentiment analysis |
| Knowledge Graph | **Neo4j** + **networkx** | Entity relationships, graph traversal |

### Data Ingestion
| Source | Technology | Purpose |
|---|---|---|
| Web Crawling | **aiohttp** + **BeautifulSoup4** + **Selenium** + **Playwright** | Multi-layer crawling (static + JS-rendered pages) |
| RSS/Atom Feeds | **feedparser** | Structured feed ingestion |
| YouTube | **youtube-transcript-api** | Transcript extraction without YouTube API |
| PDFs | **pypdf** | Document parsing and chunking |
| Wikipedia | **wikipedia** | On-demand factual knowledge seeding |
| Free APIs | Custom `api_manager.py` | Curated free public API integrations |

### Frontend
| Layer | Technology | Purpose |
|---|---|---|
| Framework | **Next.js 16.2** + **React 19** + **TypeScript** | App router, SSR, type safety |
| UI Components | **ShadCN UI** + **Base UI** | Accessible, composable component library |
| Styling | **Tailwind CSS v4** | Utility-first styling |
| State | **Zustand 5** | Lightweight global state management |
| Charts | **Recharts 3** | Data visualization for stats/dashboard |
| Markdown | **react-markdown** | Render LLM responses with formatting |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- Redis (for task queue)

### 1. Clone
```bash
git clone https://github.com/genius-0963/SelfSmart.git
cd SelfSmart
```

### 2. Backend Setup
```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate      # macOS/Linux
# .venv\Scripts\activate       # Windows

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Environment Configuration
```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Choose your LLM provider
LLM_PROVIDER=gemini          # or: deepseek

# API Keys (at least one required)
GEMINI_API_KEY=your_key_here
DEEPSEEK_API_KEY=your_key_here

# Infrastructure
DATABASE_URL=sqlite:///./smartself.db
REDIS_URL=redis://localhost:6379/0
```

### 4. Start Backend
```bash
python -m src.web_server
# Server running at: http://localhost:8000
# API docs at:       http://localhost:8000/docs
```

### 5. Start Frontend
```bash
cd frontend
npm install
npm run dev
# UI running at: http://localhost:3000
```

### 6. (Optional) Start Learning Worker
```bash
# In a separate terminal — runs the autonomous learning loop
python -m src.main
```

---

## 🐳 Docker Deployment

```bash
# Build and run the backend
docker build -t selfsmart .
docker run -p 8000:8000 --env-file .env selfsmart
```

For full-stack deployment with Redis, see [DEPLOYMENT.md](./DEPLOYMENT.md).

---

## 📡 API Reference

### Chat

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/chat` | Single-turn chat completion |
| `POST` | `/api/chat/stream` | Streaming chat via Server-Sent Events |

### Conversations

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/conversations` | List all conversation sessions |
| `GET` | `/api/conversations/{id}` | Fetch a conversation by ID |
| `DELETE` | `/api/conversations/{id}` | Delete a conversation |

### Learning Pipeline

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/learning/start` | Start the autonomous learning loop |
| `POST` | `/api/learning/stop` | Stop the learning loop |
| `GET` | `/api/stats` | Retrieval, conversation, and learning statistics |

### Health

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Simple service health check |
| `GET` | `/status` | Detailed feature and service status |

> Full interactive API docs available at `http://localhost:8000/docs` (Swagger UI) and `/redoc` (ReDoc).

---

## 🧬 LLM Fine-Tuning

SelfSmart ships with a complete fine-tuning pipeline for adapting open-source LLMs to your domain.

### Training Assets
| File | Purpose |
|---|---|
| `llm_training_notebook.ipynb` | Full local training workflow (LoRA/QLoRA) |
| `llm_training_notebook_cloud.ipynb` | Cloud-optimized training (Colab/Vertex) |
| `kaggle_train.ipynb` | Free GPU training on Kaggle |
| `train_model.py` | CLI training script |
| `src/llm_training/` | Modular training components: data prep, model loading, LoRA config, evaluation |

### Recommended Fine-Tuning Workflow

```
1. Curate domain-specific data
       ↓
2. Preprocess & tokenize (src/llm_training/data_prep.py)
       ↓
3. Configure LoRA adapters (rank, target modules, dropout)
       ↓
4. Train on GPU (local, Kaggle, or cloud)
       ↓
5. Evaluate with RAG evaluator (src/llm/rag_evaluator.py)
       ↓
6. Merge adapters and connect to local inference path
       ↓
7. Switch LLM_PROVIDER=local in .env and redeploy
```

**Tracked with:** W&B (`wandb`) for loss curves, eval metrics, and model comparison.

---

## 🗺️ Roadmap

### Near-Term (Q3 2026)
- [ ] **Model Router** — Cost/latency-aware routing between Gemini, DeepSeek, and local models
- [ ] **Source Attribution** — Per-response citations with confidence scores
- [ ] **RAG Eval Harness** — Automated RAGAS-style evaluation for retrieval quality
- [ ] **Structured Observability** — Latency histograms, retrieval hit rate, token throughput dashboards

### Medium-Term (Q4 2026)
- [ ] **Multi-Agent Framework** — Orchestrated specialist agents (researcher, summarizer, critic)
- [ ] **PostgreSQL Migration** — Production-grade database with async SQLAlchemy + asyncpg
- [ ] **Knowledge Graph UI** — Visual exploration of the Neo4j entity graph
- [ ] **User-level Memory** — Per-user long-term memory across sessions
- [ ] **Webhook Triggers** — Push-based ingestion from external sources

### Long-Term (2027+)
- [ ] **Mobile App** — React Native companion for on-the-go access
- [ ] **Federated Learning** — Privacy-preserving learning across distributed nodes
- [ ] **Multi-modal Ingestion** — Images, audio, and video understanding
- [ ] **Voice Interface** — Real-time STT/TTS integration
- [ ] **Self-Evaluation Loop** — Model critiques its own answers and initiates targeted learning

---

## 🗂️ Project Structure

```
SelfSmart/
├── src/                          # Backend application
│   ├── web_server.py             # FastAPI app, all endpoints, SSE streaming
│   ├── main.py                   # Standalone learning worker entry point
│   ├── config/                   # Settings, env management (pydantic-settings)
│   ├── llm/                      # LLM layer
│   │   ├── gemini_client.py      # Google Gemini API client
│   │   ├── deepseek_client.py    # DeepSeek API client
│   │   ├── conversation_manager.py # Multi-session conversation history
│   │   ├── rag_service.py        # RAG orchestration: retrieve → augment → generate
│   │   ├── rag_evaluator.py      # Retrieval quality evaluation
│   │   └── agent_tools.py        # Tool definitions for agentic flows
│   ├── learning/                 # Continuous learning orchestration
│   ├── knowledge/                # Knowledge base & vector store management
│   ├── api/                      # Free public API clients
│   ├── crawler/                  # Web + RSS crawlers
│   ├── processor/                # Content cleaning and chunking
│   ├── llm_training/             # Fine-tuning pipeline modules
│   ├── services/                 # Shared application services
│   ├── tasks/                    # Celery async tasks
│   └── utils/                    # Logging helpers, common utilities
│
├── frontend/                     # Next.js 16 application
│   └── src/                      # App router, components, pages
│
├── tests/                        # Test suite (unit, integration, e2e)
├── scripts/                      # Setup and migration scripts
├── configs/                      # Environment configuration profiles
├── data/                         # Knowledge data, cache, uploads
├── vector_store/                 # Persisted ChromaDB embeddings
├── logs/                         # Structured application logs
│
├── llm_training_notebook.ipynb   # Local fine-tuning notebook
├── llm_training_notebook_cloud.ipynb # Cloud fine-tuning notebook
├── kaggle_train.ipynb            # Kaggle GPU training notebook
├── train_model.py                # CLI fine-tuning script
├── llm_pipeline.py               # End-to-end pipeline utility
│
├── Dockerfile                    # Backend container image
├── requirements.txt              # Production Python dependencies
├── requirements_training.txt     # Training-specific dependencies
├── .env.example                  # Environment variable template
├── ARCHITECTURE.md               # Full system architecture docs
├── DEPLOYMENT.md                 # Deployment guide
└── PROJECT_STRUCTURE.md          # Module responsibility map
```

---

## 🔬 Engineering Principles

SelfSmart is designed with production in mind from day one:

| Principle | How It's Applied |
|---|---|
| **Async-first** | FastAPI + aiohttp + asyncpg: no blocking I/O anywhere in the hot path |
| **Modularity** | Every subsystem is independently testable and swappable (e.g., swap ChromaDB for Pinecone with a single config change) |
| **Retrieval Grounding** | Every LLM response is anchored to retrieved knowledge chunks — reducing hallucination at the architecture level |
| **Operational Pragmatism** | SQLite for dev, PostgreSQL for prod; Redis optional but recommended |
| **Observability** | Prometheus metrics, structured JSON logs, Sentry error tracking — built in, not bolted on |
| **Continuous Improvement** | The system is designed to improve its own knowledge base autonomously, not require manual retraining |

---

## 🧪 Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src --cov-report=term-missing

# Run a specific module
pytest tests/unit/
pytest tests/integration/
```

---

## 🤝 Contributing

Contributions are welcome. Please follow these guidelines:

1. **Keep PRs focused** — one feature or fix per pull request
2. **Write tests** — all new logic should have unit tests
3. **Update docs** — architecture changes must update `ARCHITECTURE.md` and `PROJECT_STRUCTURE.md`
4. **Code style** — follow existing async patterns; use type hints everywhere

---

## 📄 License

This project is licensed under the MIT License. See [LICENSE](./LICENSE) for details.

---

## 👤 Author

**Subh** — Founder, Lead Engineer  
Building SelfSmart with the mindset of a founder and senior AI engineer: ship fast, design for scale, keep the architecture honest, and make the machine smarter every day.

---

<div align="center">

⭐ **If SelfSmart helped you, give it a star!** ⭐

Built with 🧠 and ☕ | [Report a Bug](https://github.com/genius-0963/SelfSmart/issues) · [Request a Feature](https://github.com/genius-0963/SelfSmart/issues)

</div>
