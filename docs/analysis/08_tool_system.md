# 8. Tool System Report

The tool system in ModelX provides the "hands" of the autonomous agents, allowing them to interact with the external world and internal databases.

## Architecture
Tools are modular and inherit from a base abstraction (`src/tools/base.py`). The tool system is heavily integrated with LangChain's tool abstraction, allowing seamless binding to LLM function calling endpoints.

## Built-In Tools
Based on the `src/tools/` directory, the following tools are natively supported:

| Tool | File | Purpose |
|------|------|---------|
| **Web Search** | `web_search.py` | Performs web searches (likely via Tavily based on `.env`) |
| **Wikipedia** | `wikipedia_search.py` | Queries Wikipedia for factual summaries |
| **Arxiv** | `arxiv_search.py` | Searches academic papers on Arxiv |
| **File Operations** | `file_operations.py` | Reads, writes, and manipulates files |
| **Filesystem** | `filesystem_tool.py` | Directory listing, traversal, and OS-level file management |
| **Python Executor** | `python_executor.py` | Executes Python code dynamically (sandboxed via Docker) |
| **Shell Tool** | `shell_tool.py` | Executes bash/shell commands |
| **Database Query** | `database_query.py` | Executes raw SQL or ORM queries against PostgreSQL |
| **PDF Ingestion** | `pdf_ingestion.py` | Extracts text from PDF files |
| **Semantic Retrieval**| `semantic_retrieval.py` | Queries the RAG vector store for context |
| **Report Generator** | `report_generator.py` | Compiles structured reports from raw data |
| **API Caller** | `api_caller.py` | Makes arbitrary HTTP requests to external services |

## Sandboxing & Execution Safety
Tools like the `Python Executor` and `Shell Tool` pose massive security risks. ModelX mitigates this using a dedicated Docker sandbox (defined in `docker-compose.yml` as `sandbox`). This sandbox runs with dropped capabilities, read-only filesystems (with limited `tmpfs`), and memory caps, ensuring agent-generated code cannot compromise the host system.
