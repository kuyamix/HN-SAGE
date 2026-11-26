# HN-Sage
### Multi-Source, Provider-Agnostic Retrieval-Augmented Generation

<p align="center">

**A Local-First AI Knowledge Engine for Technology Discussions**

</p>

HN-Sage is a full-stack, local-first Retrieval-Augmented Generation (RAG) application that transforms discussions from **Hacker News** and **Lobsters** into a searchable, AI-powered knowledge base.

Built with a modular architecture, it integrates heterogeneous data sources, hybrid information retrieval, vector search, and provider-independent LLM inference to deliver context-aware answers supported by verifiable source citations.

The application supports both local AI inference through **Ollama** and cloud-based inference through **DeepSeek**, allowing users to choose between local execution and external AI services without changing the underlying retrieval pipeline.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Key Features](#2-key-features)
3. [Technology Stack](#3-technology-stack)
4. [System Architecture](#4-system-architecture)
5. [How HN-Sage Works](#5-how-hn-sage-works)
6. [Core Engineering Concepts](#6-core-engineering-concepts)
7. [Database Architecture](#7-database-architecture)
8. [Project Structure](#8-project-structure)
9. [Installation and Setup](#9-installation-and-setup)
10. [Configuration](#10-configuration)
11. [API Reference](#11-api-reference)
12. [Privacy and Data Handling](#12-privacy-and-data-handling)
13. [Future Development](#13-future-development)

---

## 1. Overview

### What is HN-Sage?

HN-Sage addresses the difficulty of searching, understanding, and extracting useful information from large volumes of online technology discussions.

Traditional keyword-based searches often struggle to understand the intent behind a question. Meanwhile, general-purpose LLMs may generate answers using outdated information or unsupported assumptions.

HN-Sage combines information retrieval with language generation to address these limitations.

Instead of asking an LLM to answer a question entirely from its pre-trained knowledge, the system:

1. Collects discussions from Hacker News and Lobsters.
2. Processes and indexes stories and comments locally.
3. Retrieves relevant passages using hybrid search.
4. Removes redundant results through MMR diversification.
5. Supplies the selected passages to an LLM.
6. Generates an answer with references to the original discussions.

### Design Principles

| Principle | Implementation |
|---|---|
| Local-First | Local database, vector index, and Ollama inference |
| Modularity | Independent ingestion, retrieval, API, and inference modules |
| Interoperability | Unified data representation for multiple external sources |
| Provider Independence | Switch between Ollama and DeepSeek through configuration |
| Grounded Generation | Answers are generated using retrieved source material |

### The Problems HN-Sage Addresses

**The Hallucination Problem**

LLMs can produce convincing but inaccurate responses. RAG reduces reliance on internal model knowledge by providing relevant external information as context.

**The Retrieval Redundancy Problem**

Traditional retrieval systems can return multiple passages containing nearly identical information. MMR improves contextual diversity by penalizing redundant results.

**The Data Integration Problem**

Different platforms expose information through different APIs and data structures. HN-Sage uses an adapter-based ingestion architecture to normalize these sources into a common format.

---

## 2. Key Features

### Data Integration

- **Multi-Source Ingestion:** Collects stories and comments from Hacker News and Lobsters.
- **Adapter Pattern:** Integrates external sources through a common `SourceAdapter` protocol.
- **Data Normalization:** Converts platform-specific records into a unified `RawDoc` structure.
- **Modular Ingestion Pipeline:** Separates source collection from chunking, embedding, and storage.

### Artificial Intelligence

- **Retrieval-Augmented Generation:** Grounds generated responses in retrieved discussions.
- **Provider-Agnostic Inference:** Supports local Ollama and cloud-based DeepSeek/OpenAI-compatible inference.
- **Streaming Generation:** Delivers generated answers progressively through Server-Sent Events (SSE).
- **Source Citations:** Provides references to the original stories and comments.

### Information Retrieval

- **Hybrid Search:** Combines dense vector retrieval with sparse keyword retrieval.
- **FAISS Vector Search:** Performs semantic similarity searches using numerical embeddings.
- **SQLite FTS5:** Provides full-text keyword retrieval and BM25-based ranking.
- **Reciprocal Rank Fusion:** Combines multiple retrieval rankings.
- **MMR Diversification:** Balances relevance and contextual diversity.

### Database and Backend

- **Relational Storage:** Uses SQLite to store structured stories, comments, and associated information.
- **Database Migrations:** Maintains database schema changes through versioned SQL migration scripts.
- **Foreign Key Constraints:** Maintains relationships and referential integrity.
- **Full-Text Search:** Uses FTS5 virtual tables and synchronization triggers.
- **WAL Mode:** Supports concurrent database reading and writing.

### User Interface

- Responsive web interface built with HTML, CSS, and JavaScript.
- Dark mode support.
- Source filtering.
- Streaming AI responses.
- Interactive search and question-answering experience.

---

## 3. Technology Stack

HN-Sage integrates technologies from web development, database management, information retrieval, and artificial intelligence.

| Category | Technology | Purpose |
|---|---|---|
| Frontend | HTML5 | Application structure |
| Frontend | CSS3 | Styling and responsive layout |
| Frontend | JavaScript | UI interactions and API communication |
| Backend | Python | Application logic |
| Backend | FastAPI | API and application server |
| Database | SQLite | Structured data storage |
| Database | SQLite FTS5 | Full-text keyword retrieval |
| Vector Search | FAISS | Embedding similarity search |
| Embeddings | Sentence Transformers | Text-to-vector conversion |
| Retrieval | BM25 | Lexical relevance ranking |
| Retrieval | RRF | Ranking fusion |
| Retrieval | MMR | Context diversification |
| Local Inference | Ollama | Local model execution |
| Language Model | Llama 3.2 | Local answer generation |
| Cloud Inference | DeepSeek | External LLM inference |
| Data Sources | Hacker News API | Technology discussions |
| Data Sources | Lobsters | Technology discussions |

### Default AI Configuration

| Component | Default |
|---|---|
| Embedding Model | `all-MiniLM-L6-v2` |
| Embedding Dimensions | 384 |
| Local LLM Runtime | Ollama |
| Local Language Model | `llama3.2` |
| Vector Index | FAISS |
| Keyword Search | SQLite FTS5 |
| LLM Alternative | DeepSeek |

---

## 4. System Architecture

HN-Sage follows a modular, layered architecture. Each component has a specific responsibility, allowing data ingestion, retrieval, and inference to operate independently.

### 4.1 Application Architecture

```text
┌──────────────────────────────────────────────────────────┐
│                       FRONTEND                            │
│                                                          │
│                 HTML5 / CSS3 / JavaScript                 │
│                                                          │
│       Search Interface | Source Filters | Dark Mode      │
└────────────────────────────┬─────────────────────────────┘
                             │
                             │ HTTP / SSE
                             ▼
┌──────────────────────────────────────────────────────────┐
│                     FASTAPI SERVER                        │
│                                                          │
│                       src/main.py                        │
│                                                          │
│                  API Routing & Static UI                 │
└────────────────────────────┬─────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────┐
│                    RETRIEVAL ENGINE                       │
│                                                          │
│                  src/core/retrieval.py                    │
│                                                          │
│       ┌─────────────────┐    ┌────────────────────┐       │
│       │   FAISS Search  │    │  SQLite FTS5       │       │
│       │  Dense Vectors  │    │  BM25 Retrieval    │       │
│       └────────┬────────┘    └─────────┬──────────┘       │
│                └──────────┬────────────┘                  │
│                           ▼                              │
│                  Reciprocal Rank Fusion                  │
│                           │                              │
│                           ▼                              │
│                   MMR Diversification                    │
└────────────────────────────┬─────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────┐
│                     LLM ABSTRACTION                       │
│                                                          │
│                      src/core/llm.py                     │
│                                                          │
│       ┌────────────────────┐  ┌────────────────────┐      │
│       │   Ollama           │  │    DeepSeek        │      │
│       │   Local Inference  │  │    Cloud API       │      │
│       └────────────────────┘  └────────────────────┘      │
└────────────────────────────┬─────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────┐
│                    RESPONSE GENERATION                    │
│                                                          │
│               Streamed Answer + Citations                │
└──────────────────────────────────────────────────────────┘
```

### 4.2 Data Integration Architecture

The ingestion system uses the Adapter Pattern to support different external data sources.

```text
                 EXTERNAL DATA SOURCES
                           │
              ┌────────────┴────────────┐
              │                         │
              ▼                         ▼
      ┌───────────────┐         ┌───────────────┐
      │  Hacker News  │         │   Lobsters    │
      │    Adapter    │         │    Adapter    │
      └───────┬───────┘         └───────┬───────┘
              │                         │
              └────────────┬────────────┘
                           │
                           ▼
                ┌────────────────────┐
                │   SourceAdapter    │
                │  Unified RawDoc    │
                └─────────┬──────────┘
                          │
                          ▼
                ┌────────────────────┐
                │ Ingestion          │
                │ Orchestrator       │
                └─────────┬──────────┘
                          │
                          ▼
                ┌────────────────────┐
                │  Passage Chunking  │
                └─────────┬──────────┘
                          │
                          ▼
                ┌────────────────────┐
                │ Embedding Creation │
                └─────────┬──────────┘
                          │
                          ▼
                ┌────────────────────┐
                │   Local Storage    │
                │                    │
                │   SQLite + FAISS   │
                └────────────────────┘
```

**Architectural advantage:** Adding another supported source does not require rewriting the retrieval engine or database processing logic. A new adapter can implement the shared interface and pass normalized documents to the ingestion orchestrator.

---

## 5. How HN-Sage Works

The application operates through two independent but interconnected pipelines.

### 5.1 Data Ingestion Pipeline

The ingestion pipeline collects and prepares external discussions for retrieval.

| Stage | Process | Description |
|---|---|---|
| 1 | Collection | Retrieve stories and comments from external APIs. |
| 2 | Adaptation | Convert platform-specific data into a unified structure. |
| 3 | Chunking | Divide discussions into smaller passages. |
| 4 | Embedding | Generate numerical representations of passages. |
| 5 | Database Storage | Save structured records in SQLite. |
| 6 | Vector Indexing | Store embeddings in FAISS. |

The resulting knowledge base is stored locally and reused during subsequent searches.

### 5.2 Retrieval and Generation Pipeline

When a user submits a question:

1. **Query Submission:** The frontend sends the user's question to FastAPI.
2. **Query Processing:** The retrieval engine prepares the query for keyword and semantic retrieval.
3. **Hybrid Search:** FAISS and SQLite FTS5 independently identify relevant passages.
4. **Ranking Fusion:** RRF combines the search results into a unified ranking.
5. **Diversification:** MMR selects relevant passages while reducing redundancy.
6. **Context Construction:** Retrieved passages are assembled into an LLM prompt.
7. **Model Inference:** The configured provider generates an answer.
8. **Response Streaming:** FastAPI streams the generated answer and associated source references to the frontend.

---

## 6. Core Engineering Concepts

### 6.1 Adapter Pattern for Multi-Source Integration

**Implementation:** `src/ingest/sources/`

HN-Sage uses the Adapter Pattern to integrate different external platforms through a common interface.

Hacker News and Lobsters expose different API structures and content formats. Instead of writing separate database and embedding pipelines for each source, the application normalizes their data before processing.

The architecture follows three principles:

**Source Adapter**

Each source implements the `SourceAdapter` protocol, including the operations:

- `fetch_ids()`
- `fetch_doc()`

**Unified Data Representation**

Platform-specific records are converted into a shared `RawDoc` structure.

**Centralized Processing**

The ingestion orchestrator handles chunking, embedding generation, and database writes without needing to know which platform supplied the content.

**Benefits:**
- Reduces duplicated code.
- Simplifies integration of additional sources.
- Separates external API dependencies from core application logic.
- Makes the ingestion pipeline easier to maintain and extend.

### 6.2 Hybrid Information Retrieval

**Implementation:** `src/core/retrieval.py`

HN-Sage combines dense vector retrieval and sparse keyword retrieval.

**Dense Retrieval — FAISS**

Text is converted into numerical embeddings using Sentence Transformers.

The default model, `all-MiniLM-L6-v2`, generates 384-dimensional vectors.

FAISS uses these vectors to identify semantically related passages.

**Sparse Retrieval — SQLite FTS5**

SQLite Full-Text Search provides lexical retrieval through indexed text fields and BM25 ranking.

This approach is particularly useful for queries involving exact technical terms, product names, programming languages, and specific technologies.

**Reciprocal Rank Fusion (RRF)**

The two retrieval methods produce separate rankings. RRF combines them into one result list.

\[
RRF(d)=\sum_{r\in R}\frac{1}{k+rank_r(d)}
\]

Where:

- \(d\) = Retrieved document.
- \(R\) = Collection of retrieval rankings.
- \(rank_r(d)\) = Position of the document in ranking \(r\).
- \(k\) = Ranking constant.

**Benefits:**
- Combines keyword and semantic search.
- Reduces dependence on a single retrieval strategy.
- Improves coverage for different types of queries.

### 6.3 Maximal Marginal Relevance

**Implementation:** `src/core/retrieval.py`

MMR addresses retrieval redundancy by selecting passages based on both relevance and diversity.

The algorithm evaluates:

- How relevant a passage is to the user's question.
- How similar that passage is to previously selected passages.

The selection formula is:

\[
MMR(D)=
\lambda Sim(D,Q)
-
(1-\lambda)
\max_{D_j\in S}Sim(D,D_j)
\]

Where:

| Variable | Meaning |
|---|---|
| \(D\) | Candidate passage |
| \(Q\) | User query |
| \(S\) | Previously selected passages |
| \(Sim(D,Q)\) | Query relevance |
| \(Sim(D,D_j)\) | Redundancy similarity |
| \(\lambda\) | Relevance-diversity balance |

The default configuration is:

```python
MMR_LAMBDA = 0.5
```

A value of `0.5` balances relevance and diversity. A value of `1.0` removes the diversity penalty and prioritizes query relevance.

**Benefits:**
- Reduces repetitive retrieved context.
- Improves contextual diversity.
- Helps the LLM receive a broader range of discussion perspectives.

### 6.4 Provider-Agnostic LLM Abstraction

**Implementation:** `src/core/llm.py`

The LLM inference layer separates response generation from the retrieval pipeline.

Instead of coupling the application to one specific language model, HN-Sage uses a common provider interface and configuration-driven inference.

Supported configurations include:

| Provider | Execution | Description |
|---|---|---|
| Ollama | Local | Runs Llama 3.2 on the user's machine |
| DeepSeek | Cloud | Uses DeepSeek's API |
| OpenAI-compatible | Cloud | Supports compatible inference endpoints where configured |

Provider selection is controlled through environment variables.

For example:

```powershell
$env:LLM_PROVIDER="ollama"
```

Or:

```powershell
$env:LLM_PROVIDER="openai"
```

**Benefits:**
- Separates inference from retrieval logic.
- Makes model replacement easier.
- Supports different deployment environments.
- Reduces dependency on a single AI provider.

### 6.5 Database Migrations and Full-Text Search

**Implementation:** `src/db.py` and `migrations/`

HN-Sage uses SQLite as its primary structured storage system.

Instead of relying on a manually maintained database schema, the application uses versioned SQL migrations.

The migration system tracks the database version through SQLite's `user_version` mechanism and applies the appropriate SQL scripts sequentially.

Additional database capabilities include:

- Foreign key constraints for relational integrity.
- Write-Ahead Logging (WAL) for improved concurrent database access.
- FTS5 virtual tables for full-text search.
- Synchronization triggers for keeping search indexes consistent with source records.

**Benefits:**
- Reproducible database initialization.
- Easier schema evolution.
- Better data consistency.
- Integrated keyword retrieval without requiring a separate search server.

---

## 7. Database Architecture

HN-Sage uses SQLite to manage structured records and full-text search indexes, while FAISS handles vector similarity search.

### Storage Components

| Component | Responsibility |
|---|---|
| SQLite | Stores structured source data |
| FTS5 | Maintains searchable text indexes |
| FAISS | Stores vector embeddings |
| `ids.json` | Maps vector identifiers to database records |
| SQL Migrations | Manages database schema versions |

### Database Design Principles

**Referential Integrity**

Foreign key constraints help maintain relationships between related database records.

**Full-Text Index Synchronization**

SQLite triggers synchronize the FTS5 index with its associated source records when supported database operations modify the underlying data.

**Schema Versioning**

The migration runner tracks applied schema versions and executes pending migrations.

**Concurrent Access**

WAL mode improves concurrency by allowing readers to access the database while write transactions are being processed, subject to SQLite's transaction and locking behavior.

---

## 8. Project Structure

The project follows a modular organization separating the backend, data integration, database management, frontend, and generated data.

```text
HN-Sage/
│
├── data/                       # Local generated data (gitignored)
│   ├── hn.db                   # SQLite database and FTS5
│   ├── hn.faiss                # FAISS vector index
│   └── ids.json                # Vector-to-record mapping
│
├── docs/                       # Project documentation
│
├── migrations/                 # Versioned SQL migrations
│   ├── 000_init_v1.sql
│   └── 001_v2_schema.sql
│
├── src/                        # Backend application
│   │
│   ├── main.py                 # FastAPI entry point
│   ├── config.py               # Application configuration
│   ├── db.py                   # Database and migrations
│   │
│   ├── api/
│   │   └── routes.py           # API endpoints
│   │
│   ├── core/
│   │   ├── retrieval.py        # Hybrid search, RRF, and MMR
│   │   └── llm.py              # LLM provider abstraction
│   │
│   └── ingest/
│       ├── orchestrator.py    # Chunking, embeddings, and storage
│       │
│       └── sources/
│           ├── base.py         # SourceAdapter protocol
│           ├── hackernews.py   # Hacker News adapter
│           └── lobsters.py     # Lobsters adapter
│
├── static/                     # Frontend application
│   ├── index.html
│   ├── style.css
│   └── app.js
│
├── requirements.txt            # Python dependencies
├── .gitignore                  # Git exclusions
└── README.md                   # Project documentation
```

---

## 9. Installation and Setup

### Prerequisites

Install the following before running HN-Sage:

- Python 3.9 or later.
- Git.
- [Ollama](https://ollama.com/) for local LLM inference.
- A DeepSeek API key if cloud inference is preferred.

### Step 1. Clone the Repository

```bash
git clone <repository-url>
cd HN-Sage
```

Alternatively, download and extract the repository.

### Step 2. Create a Virtual Environment

```bash
python -m venv venv
```

Activate it using the appropriate command.

**Windows PowerShell:**

```powershell
.\venv\Scripts\Activate.ps1
```

**Linux/macOS:**

```bash
source venv/bin/activate
```

### Step 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4. Configure Local Inference

Install Ollama and download the default language model:

```bash
ollama pull llama3.2
```

Ensure the Ollama service is running before starting the application.

### Step 5. Ingest Hacker News Data

Run the Hacker News ingestion module:

```bash
python -m src.ingest.sources.hackernews
```

### Step 6. Ingest Lobsters Data

Run the Lobsters ingestion module:

```bash
python -m src.ingest.sources.lobsters
```

Both ingestion processes populate the local knowledge base.

The application stores its generated data in the `data/` directory.

```text
data/
├── hn.db
├── hn.faiss
└── ids.json
```

**Note:** Internet access is required to retrieve external discussions. Depending on the implementation, the ingestion process may need to be rerun when updating the knowledge base.

### Step 7. Start HN-Sage

Start the FastAPI application:

```bash
uvicorn src.main:app --reload
```

The backend serves the frontend and API from the same application.

Open your browser:

**http://localhost:8000**

---

## 10. Configuration

HN-Sage uses environment variables to configure its LLM provider and retrieval behavior.

### 10.1 Local Inference — Ollama

Local inference is the default configuration.

```powershell
$env:LLM_PROVIDER="ollama"
```

The application uses the configured Ollama model, with `llama3.2` as the default.

### 10.2 Cloud Inference — DeepSeek

To use DeepSeek instead of local Ollama, configure the provider through PowerShell:

```powershell
$env:LLM_PROVIDER="openai"
$env:LLM_API_KEY="your-deepseek-api-key"
$env:LLM_BASE_URL="https://api.deepseek.com/v1"
$env:LLM_MODEL="deepseek-chat"
```

Start the application:

```powershell
uvicorn src.main:app --reload
```

The `openai` provider setting uses an OpenAI-compatible client configuration with DeepSeek's API endpoint.

**Security:** Never commit API keys to GitHub. Use environment variables or a properly configured local `.env` file if supported by the application.

### 10.3 Retrieval Configuration

HN-Sage supports retrieval ablation through environment variables.

| Variable | Value | Behavior |
|---|---|---|
| `RETRIEVAL_MODE` | `hybrid` | FAISS + BM25 |
| `RETRIEVAL_MODE` | `vector` | FAISS only |
| `RETRIEVAL_MODE` | `bm25` | Keyword retrieval only |
| `MMR_LAMBDA` | `0.5` | Balanced relevance and diversity |
| `MMR_LAMBDA` | `1.0` | Relevance without diversity penalty |

**Example: BM25 Only**

```powershell
$env:RETRIEVAL_MODE="bm25"
uvicorn src.main:app --reload
```

**Example: Vector Only**

```powershell
$env:RETRIEVAL_MODE="vector"
uvicorn src.main:app --reload
```

**Example: Disable MMR Diversification**

```powershell
$env:MMR_LAMBDA="1.0"
uvicorn src.main:app --reload
```

### 10.4 Reset Configuration

To restore default environment behavior in PowerShell:

```powershell
Remove-Item Env:LLM_PROVIDER -ErrorAction SilentlyContinue
Remove-Item Env:LLM_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:LLM_BASE_URL -ErrorAction SilentlyContinue
Remove-Item Env:LLM_MODEL -ErrorAction SilentlyContinue
Remove-Item Env:RETRIEVAL_MODE -ErrorAction SilentlyContinue
Remove-Item Env:MMR_LAMBDA -ErrorAction SilentlyContinue
```

---

## 11. API Reference

The FastAPI backend exposes endpoints for application health checks, information retrieval, and AI-powered question answering.

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Checks application availability |
| `/search` | GET | Searches the indexed knowledge base |
| `/ask/stream` | GET | Generates and streams an AI response |

### Interactive API Documentation

FastAPI automatically provides an interactive API documentation interface.

After starting the application, navigate to:

**http://localhost:8000/docs**

The Swagger interface allows developers to inspect available routes, parameters, and response schemas.

---

## 12. Privacy and Data Handling

HN-Sage is designed around a local-first architecture.

### Local Components

- Hacker News and Lobsters data is retrieved and indexed locally.
- SQLite stores structured records and searchable content.
- FAISS stores vector embeddings.
- Ollama performs local LLM inference.

### External Communication

The application requires internet connectivity for external data ingestion and downloading models.

When using DeepSeek or another cloud inference provider, prompts and retrieved context are transmitted to that provider for processing.

| Operation | Local | External |
|---|---|---|
| Database Storage | Yes | No |
| Vector Indexing | Yes | No |
| Ollama Inference | Yes | No |
| Hacker News Ingestion | No | Yes |
| Lobsters Ingestion | No | Yes |
| DeepSeek Inference | No | Yes |

**Privacy principle:** Local inference keeps LLM processing on the user's machine. Cloud inference is optional and should be enabled only when the user accepts the associated external data processing.

---

## 13. Future Development

Although HN-Sage already supports multiple sources and inference providers, several improvements could expand its capabilities.

### 13.1 Agentic Retrieval

Introduce query decomposition, allowing complex questions to be divided into smaller sub-queries before retrieval.

### 13.2 Cross-Source Deduplication

Identify discussions that share the same URL across Hacker News and Lobsters to reduce duplicate content and improve search results.

### 13.3 Expanded Data Sources

Extend the existing adapter architecture to support additional sources:

- arXiv research papers.
- GitHub Trending.
- RSS feeds.
- Additional technology discussion communities.

### 13.4 Retrieval Evaluation Framework

Develop an automated evaluation system using a curated benchmark dataset.

Potential evaluation metrics:

- Precision@K.
- Recall@K.
- Mean Reciprocal Rank (MRR).
- Normalized Discounted Cumulative Gain (nDCG).
- Answer faithfulness.
- Citation accuracy.

### 13.5 Persistent Conversation History

Introduce conversation persistence to support follow-up questions and multi-turn interactions.

---

## Project Summary

HN-Sage demonstrates how modern AI technologies can be integrated into a practical, full-stack information retrieval application.

Through its combination of multi-source data integration, relational database management, semantic search, hybrid retrieval, MMR diversification, and provider-agnostic LLM inference, the project explores a more modular and controllable approach to AI-powered knowledge discovery.

Its local-first architecture also demonstrates how AI applications can provide useful language model capabilities while maintaining greater control over data storage and inference.

**HN-Sage — Turning technology discussions into searchable, contextual, and AI-powered knowledge.**

---

*Developed as a Final Project for Application Development & Emerging Technologies.*