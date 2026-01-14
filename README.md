# Claude Memory Skill

A self-hosted service that enables Claude Code to search your past conversations using natural language queries.

## Architecture

```
Claude (Opus)
    │
    │  POST /search {"query": "natural language question"}
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  Memory Service (Docker)                            │
│                                                     │
│  1. Cheap LLM parses query → search plan           │
│  2. Hybrid search (FTS5 + vector)                  │
│  3. RRF fusion combines results                    │
│  4. LLM formats response                           │
│                                                     │
│  SQLite (FTS5 + sqlite-vec)                        │
│  └── ~/.claude/projects/*.jsonl                    │
└─────────────────────────────────────────────────────┘
    │
    │  {"result": "On Jan 10, you discussed..."}
    │
    ▼
Claude (Opus)
```

## Quick Start

1. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenRouter API key
   ```

2. **Start the service**
   ```bash
   docker compose up -d
   ```

3. **Install the skill** (copy to your Claude skills directory)
   ```bash
   cp skill/SKILL.md ~/.claude/skills/memory.md
   ```

4. **Use it**
   ```bash
   curl -s -X POST http://localhost:8002/search \
     -H "Content-Type: application/json" \
     -d '{"query": "what did I discuss about authentication last week"}'
   ```

## Configuration

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `OPENROUTER_API_KEY` | Your OpenRouter API key | (required) |
| `OPENROUTER_MODEL` | LLM model for query processing | `google/gemini-2.0-flash-lite-001` |

The service automatically mounts `~/.claude/projects` to read conversation archives.

## API

### POST /search

Search your conversation history.

```bash
curl -X POST http://localhost:8002/search \
  -H "Content-Type: application/json" \
  -d '{"query": "your natural language question"}'
```

Response:
```json
{
  "result": "Formatted response with relevant conversation excerpts..."
}
```

### GET /stats

Get database statistics.

```bash
curl http://localhost:8002/stats
```

Response:
```json
{
  "total_messages": 1234,
  "sessions": 56,
  "projects": 7
}
```

### POST /ingest

Trigger re-indexing of conversation archives.

```bash
curl -X POST http://localhost:8002/ingest
```

### GET /health

Health check endpoint.

## How It Works

1. **Ingest**: On startup (and via `/ingest`), the service scans `~/.claude/projects` for JSONL conversation files and indexes them:
   - Full-text index (SQLite FTS5) for keyword search
   - Vector index (sqlite-vec) for semantic search

2. **Search**: When you query:
   - A cheap LLM (via OpenRouter) analyzes your query and generates search strategies
   - Hybrid search runs both FTS5 and vector queries
   - Results are combined using Reciprocal Rank Fusion (RRF)
   - The LLM formats a helpful response with relevant excerpts

3. **Cost**: Uses `gemini-2.0-flash-lite` (~$0.002 per search) for query processing and response formatting.

## Data Storage

- **Database**: `/app/data/memory.db` (persisted via Docker volume)
- **Embedding model**: Cached in `/app/models` (persisted via Docker volume)
- **Conversation archives**: Mounted read-only from `~/.claude/projects`

## Troubleshooting

**Service won't start**
```bash
docker compose logs memory
```

**No results found**
- Check if archives exist: `ls ~/.claude/projects`
- Trigger re-ingest: `curl -X POST http://localhost:8002/ingest`
- Check stats: `curl http://localhost:8002/stats`

**Slow first query**
- The embedding model (~90MB) downloads on first use
- Subsequent queries are fast (~500ms)

## License

MIT
