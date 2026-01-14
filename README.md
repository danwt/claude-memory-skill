# Claude Memory Skill

[![GitHub stars](https://img.shields.io/github/stars/danwt/claude-memory-skill?style=flat-square)](https://github.com/danwt/claude-memory-skill/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/danwt/claude-memory-skill?style=flat-square)](https://github.com/danwt/claude-memory-skill/network/members)
[![GitHub issues](https://img.shields.io/github/issues/danwt/claude-memory-skill?style=flat-square)](https://github.com/danwt/claude-memory-skill/issues)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-ready-blue?style=flat-square&logo=docker)](https://www.docker.com/)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-skill-blueviolet?style=flat-square)](https://claude.ai/claude-code)
[![Python](https://img.shields.io/badge/Python-3.12-green?style=flat-square&logo=python)](https://www.python.org/)

> Give Claude Code persistent memory across sessions with natural language search

A self-hosted Docker service that indexes your Claude Code conversation history and makes it searchable using natural language. Uses hybrid search (FTS5 + vector embeddings) with an agentic LLM layer that understands your queries and returns relevant excerpts from past conversations.

## Features

- **Natural language search** - Ask questions like "what did we discuss about auth last week?"
- **Hybrid retrieval** - Combines keyword (BM25) and semantic (vector) search with RRF fusion
- **Agentic query planning** - Cheap LLM interprets your query and runs optimal searches
- **Auto-ingestion** - Automatically indexes `~/.claude/projects` on startup
- **Cost-efficient** - Uses Gemini Flash Lite (~$0.002 per search) via OpenRouter
- **Fully local** - Your conversations never leave your machine (except LLM calls)

## Quick Start

```bash
# Clone
git clone https://github.com/danwt/claude-memory-skill.git
cd claude-memory-skill

# Configure
cp .env.example .env
# Edit .env and add your OpenRouter API key

# Start
docker compose up -d

# Verify
curl http://localhost:8002/health
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Claude Code                         │
│                          │                              │
│                     /memory skill                       │
│                          │                              │
│                       curl/bash                         │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│              Memory Service (port 8002)                  │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │              Agentic Search Layer                  │  │
│  │                                                    │  │
│  │  1. Parse natural language query                  │  │
│  │  2. Generate FTS5 + vector search strategies      │  │
│  │  3. Execute searches, evaluate results            │  │
│  │  4. Format helpful response                       │  │
│  │                     (Gemini Flash Lite)           │  │
│  └────────────────────────────────────────────────────┘  │
│                          │                               │
│                          ▼                               │
│  ┌────────────────────────────────────────────────────┐  │
│  │           SQLite + FTS5 + sqlite-vec              │  │
│  │                                                    │  │
│  │  • Full-text index (BM25 ranking)                 │  │
│  │  • Vector index (384-dim embeddings)              │  │
│  │  • RRF fusion for hybrid results                  │  │
│  └────────────────────────────────────────────────────┘  │
│                          │                               │
│                          ▼                               │
│  ┌────────────────────────────────────────────────────┐  │
│  │              ~/.claude/projects                    │  │
│  │                                                    │  │
│  │  Your conversation archives (JSONL)               │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

## Usage

Just ask Claude to search your memory:

```bash
curl -X POST http://localhost:8002/search \
  -H "Content-Type: application/json" \
  -d '{"query": "how did we fix the authentication bug in cosmos-sdk?"}'
```

Example queries:
- "what did I work on yesterday?"
- "find discussions about database migrations"
- "how did we implement the rate limiter?"
- "what was the solution for the Docker networking issue?"

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENROUTER_API_KEY` | Your OpenRouter API key | (required) |
| `OPENROUTER_MODEL` | LLM for query processing | `google/gemini-2.0-flash-lite-001` |

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/search` | POST | Search conversations with `{"query": "..."}` |
| `/stats` | GET | Database statistics (messages, sessions, projects) |
| `/ingest` | POST | Trigger re-indexing of archives |
| `/health` | GET | Health check |

## How It Works

1. **Ingest** - On startup, scans `~/.claude/projects/*.jsonl` and builds:
   - SQLite FTS5 index for keyword/phrase search
   - sqlite-vec index with sentence-transformer embeddings

2. **Search** - When you query:
   - Cheap LLM analyzes your question and generates search strategies
   - Runs parallel FTS5 (keyword) and vector (semantic) searches
   - Combines results using Reciprocal Rank Fusion (RRF)
   - LLM formats a helpful response with relevant excerpts

3. **Cost** - ~$0.002 per search (2 LLM calls via Gemini Flash Lite)

## Data Storage

| Path | Description |
|------|-------------|
| `memory-data` volume | SQLite database |
| `embedding-models` volume | Cached sentence-transformers model (~90MB) |
| `~/.claude/projects` | Your conversation archives (read-only mount) |

## Troubleshooting

<details>
<summary><b>Service won't start</b></summary>

```bash
docker compose logs memory
```
</details>

<details>
<summary><b>No results found</b></summary>

- Check archives exist: `ls ~/.claude/projects`
- Trigger re-ingest: `curl -X POST http://localhost:8002/ingest`
- Check stats: `curl http://localhost:8002/stats`
</details>

<details>
<summary><b>Slow first query</b></summary>

The embedding model (~90MB) downloads on first use. Subsequent queries are fast (~500ms).
</details>

## Related Projects

- [claude-search-skill](https://github.com/danwt/claude-search-skill) - Web search and scraping for Claude Code

## License

MIT
