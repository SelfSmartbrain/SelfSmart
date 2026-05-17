# SmartSelf AI

**Founder-built, production-minded AI platform for continuous learning, retrieval, and real-time conversation.**

SmartSelf AI is not just another chatbot wrapper.  
It is an opinionated system for building a learning assistant that:

- learns from live public data sources,
- stores and ranks knowledge for retrieval,
- answers with conversational quality using LLM + RAG,
- and exposes this through a clean API and web interface.

---

## Vision

Most assistants are static snapshots of model weights.  
SmartSelf is built on a different belief:

> **An assistant should improve every day by learning from the world, not just from prompts.**

This repository is the engineering foundation for that direction: modular backend services, streaming chat UX, knowledge ingestion, and a training path for local model fine-tuning.

---

## What This Project Delivers

- **Continuous learning pipeline** from web and free public APIs
- **RAG-backed responses** using a vector store and semantic retrieval
- **LLM abstraction layer** for API-based inference and local model inference
- **Streaming chat** over SSE for responsive UX
- **Conversation memory** with multi-conversation management
- **FastAPI service** with clean endpoints for product integration
- **Training utilities and notebooks** for iterative LLM improvement

---

## System Architecture

At a high level:

1. **Ingest**: collect signals from web and API sources  
2. **Process**: normalize, clean, and structure content  
3. **Store**: persist retrievable representations in vector/database layers  
4. **Retrieve**: augment user query with relevant context  
5. **Generate**: produce grounded responses via LLM  
6. **Learn**: feed newly acquired knowledge back into the system

Core runtime modules live in `src/`:

- `src/web_server.py` - FastAPI server, chat endpoints, streaming, status APIs
- `src/learning/` - continuous learning orchestration
- `src/knowledge/` - knowledge integration and export/import flows
- `src/llm/` - conversation manager, DeepSeek client, RAG service
- `src/llm_training/` - local training/inference pipeline components
- `src/api/` - public API integration clients
- `src/crawler/` - crawler primitives
- `src/config/` - settings and environment configuration

---

## Product Surface (Current)

- `POST /api/chat` - standard chat completion
- `POST /api/chat/stream` - streaming responses (SSE)
- `GET /api/conversations` - list conversation sessions
- `GET /api/conversations/{id}` - fetch one conversation
- `DELETE /api/conversations/{id}` - delete conversation
- `GET /api/stats` - retrieval/conversation/learning stats
- `POST /api/learning/start` - start learning loop
- `POST /api/learning/stop` - stop learning loop
- `GET /health` and `GET /status` - service health and feature status

---

## Quick Start

### 1) Clone and enter project

```bash
git clone https://github.com/genius-0963/SelfSmart.git
cd SelfSmart
```

### 2) Create virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3) Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4) Configure environment

```bash
cp .env.example .env
```

Set at least:

- `DEEPSEEK_API_KEY` (if using hosted LLM path)
- `OPENAI_API_KEY` (optional, depending on your selected client path)
- `HOST`, `PORT`, `DEBUG` as needed

### 5) Run API server

```bash
python -m src.web_server
```

Then open: `http://localhost:8000`

---

## Alternative Runtime: Learning Worker

To run the standalone learning loop:

```bash
python -m src.main
```

This path is useful when you want ingestion/learning running independently from the web UI lifecycle.

---

## Training and Experimentation

This repository includes training-oriented assets:

- `llm_training_notebook.ipynb`
- `llm_training_notebook_cloud.ipynb`
- `kaggle_train.ipynb`
- `train_model.py`
- `src/llm_training/` modules for data prep, LoRA flow, model loading, and inference

Recommended workflow:

1. curate domain data  
2. run preprocessing  
3. train/fine-tune  
4. validate inference quality  
5. connect checkpoints into local inference path

---

## Engineering Principles

SmartSelf is intentionally built with:

- **modularity** over monolith complexity,
- **operational pragmatism** over premature abstraction,
- **async-first services** for scale and latency control,
- **retrieval grounding** to reduce hallucination risk,
- **extensibility** for future multi-agent and multi-model upgrades.

---

## Near-Term Roadmap

- Model routing and fallback strategies (cost/latency aware)
- Better source attribution and confidence scoring in answers
- Eval harness for RAG quality and response safety
- Deployment profiles for local, cloud VM, and containerized environments
- Structured observability (latency, retrieval hit rate, answer quality)

---

## Development

Run tests:

```bash
pytest tests/
```

If you contribute, keep changes focused, testable, and documented.  
For major architecture shifts, update `ARCHITECTURE.md` and `PROJECT_STRUCTURE.md` in the same PR.

---

## Founder Note

I built SmartSelf with the mindset of a founder and lead engineer: ship fast, design for scale, and keep the architecture honest.  
This codebase is meant to be both a working product and a serious technical foundation for the next iteration of continuously learning AI systems.
