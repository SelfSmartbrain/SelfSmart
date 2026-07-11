# SelfSmart AI - System Architecture

## Component Architecture Diagram

```ascii
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SELFSMART AI PLATFORM                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐        │
│  │   FRONTEND      │    │   BACKEND API   │    │   TRAINING      │        │
│  │   (Next.js)     │◄──►│   (FastAPI)     │◄──►│   (Manual)      │        │
│  │                 │    │                 │    │                 │        │
│  │ • Chat UI       │    │ • REST Endpoints│    │ • LoRA SFT      │        │
│  │ • Voice Input   │    │ • SSE Streaming │    │ • DPO Training  │        │
│  │ • Conversations │    │ • Auth (JWT)    │    │ • Data Scripts  │        │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘        │
│           │                       │                       │              │
│           │                       │                       │              │
│           ▼                       ▼                       ▼              │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐        │
│  │   DATABASE      │    │   VECTOR STORE  │    │   MODEL STORE   │        │
│  │   (SQLite)      │    │   (ChromaDB)    │    │   (Checkpoints) │        │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘        │
│                                                         │                  │
│                                                         ▼                  │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                        INFERENCE ENGINE                             │  │
│  │  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────────────┐ │  │
│  │  │   RAG       │  │   LLM        │  │   LOCAL INFERENCE           │ │  │
│  │  │   Service   │  │   Clients    │  │   (MLX / API Fallback)      │ │  │
│  │  └─────────────┘  └──────────────┘  └─────────────────────────────┘ │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                           │                        │                      │
│                           ▼                        ▼                      │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐        │
│  │  DATA CRAWL    │    │   CONTENT      │    │   FEEDBACK      │        │
│  │  (Web/RSS/API) │    │   PROCESSOR    │    │   (JSONL)       │        │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Component Responsibility Matrix

| Component | Primary Responsibilities | Key Technologies | Success Metrics |
|-----------|-------------------------|------------------|-----------------|
| **Frontend** | Chat interface, conversation management, voice input | Next.js, TailwindCSS, Lucide | <200ms page loads, responsive UI |
| **Backend API** | Request handling, auth, streaming, orchestration | FastAPI, Pydantic, JWT, slowapi | <100ms API response, 99.9% uptime |
| **RAG Service** | Semantic retrieval, cross-encoder reranking, context injection | ChromaDB, sentence-transformers, CrossEncoder | <100ms retrieval, >80% relevance |
| **Inference Engine** | LLM generation, local MLX inference, API fallback | MLX, DeepSeek/Gemini APIs | <2s response, graceful degradation |
| **Data Crawler** | Web scraping, RSS feeds, API data collection | aiohttp, BeautifulSoup4, feedparser | 90% crawl success rate |
| **Content Processor** | Text cleaning, chunking, entity extraction | spaCy, langchain-text-splitters | Quality score >0.7 |
| **Training Pipeline** | LoRA SFT, DPO training, model merging | PyTorch, PEFT, TRL, transformers | Training completes without OOM |
| **Database** | Conversation storage, user auth, feedback logs | SQLite, aiosqlite | <10ms query, data consistency |
| **Vector Store** | Embedding storage, semantic search, deduplication | ChromaDB, sentence-transformers | <50ms search, semantic dedup |

## Data Flow Architecture

```ascii
1. DATA COLLECTION (Manual / Scheduled)
    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
    │ Web Crawl   │───▶│ Content     │───▶│ Knowledge   │
    │ RSS Feeds   │    │ Processor   │    │ Integrator  │
    │ Free APIs   │    │             │    │             │
    └─────────────┘    └─────────────┘    └─────────────┘
                                                   │
                                                   ▼
                                         ┌─────────────────┐
                                         │   ChromaDB      │
                                         │   Vector Store  │
                                         └─────────────────┘

2. CHAT INFERENCE FLOW
    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
    │ User Query  │───▶│ RAG Service │───▶│ Context     │
    │             │    │ (Retrieve)  │    │ Enhancement │
    └─────────────┘    └─────────────┘    └─────────────┘
                            │                   │
                            ▼                   ▼
                     ┌─────────────┐    ┌─────────────┐
                     │ LLM         │    │ Response    │
                     │ Generation  │    │ Critique    │
                     │ (MLX/API)   │    │ (Optional)  │
                     └─────────────┘    └─────────────┘
                            │                   │
                            ▼                   ▼
                     ┌─────────────┐    ┌─────────────┐
                     │ Stream to   │    │ Save to     │
                     │ Client      │    │ Database    │
                     └─────────────┘    └─────────────┘

3. TRAINING PIPELINE (Manual)
    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
    │ Raw Data    │───▶│ Instruction │───▶│ LoRA SFT    │
    │ (JSON)      │    │ Formatting  │    │ Training    │
    └─────────────┘    └─────────────┘    └─────────────┘
                                                   │
                                                   ▼
                                         ┌─────────────────┐
                                         │   Model         │
                                         │   Checkpoints   │
                                         └─────────────────┘

4. DPO PIPELINE (Manual)
    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
    │ Feedback    │───▶│ Preference  │───▶│ DPO         │
    │ (JSONL)     │    │ Dataset     │    │ Training    │
    └─────────────┘    └─────────────┘    └─────────────┘
                                                   │
                                                   ▼
                                         ┌─────────────────┐
                                         │   Model         │
                                         │   Checkpoints   │
                                         └─────────────────┘
```

## Five Phases of Knowledge Integration

The system implements a 5-phase approach for knowledge integration:

| Phase | Feature | Engineering Details | Automation Status |
|-------|---------|---------------------|-------------------|
| **1** | Web Crawling | Async data collector pulling HTML/RSS into JSON pipelines via `aiohttp` and `BeautifulSoup4`. | Manual script execution |
| **2** | RAG Search Engine | `ChromaDB` integration with `sentence-transformers` for semantic retrieval and context-grounding. | Automated in chat flow |
| **3** | SFT LoRA Fine-Tuning | PyTorch `peft` and `trl.SFTTrainer` pipelines for domain-specific knowledge integration. | Manual script execution |
| **4** | Apple MLX Inference | `mlx-lm` for native Apple Silicon Unified Memory execution with streaming SSE responses. | Automated in chat flow |
| **5** | DPO Training | RLHF pipeline using `trl.DPOTrainer` with Gemini-synthesized preference pairs from user feedback. | Manual script execution |

## Engineering Principles

SelfSmart is designed with a Senior AI/ML Engineering mindset:

| Principle | How It's Applied |
|-----------|------------------|
| **Hardware Symbiosis** | We ditched PyTorch inference on Mac in favor of `mlx-lm` to tap directly into Apple's Unified Memory, bypassing expensive CUDA constraints. |
| **VRAM Optimization** | Kaggle notebooks utilize `bitsandbytes` 4-bit NF4 quantization to squeeze 3.8B parameter models into 16GB T4 instances without OOM crashes. |
| **Data Integrity** | Instead of manually writing synthetic data, the DPO builder proxies through Gemini to guarantee structurally perfect `chosen`/`rejected` pairings. |
| **Architectural Agility** | The system is highly modular. The LLM engine, RAG database, and UI are fully decoupled, allowing plug-and-play swaps as the ecosystem evolves. |
