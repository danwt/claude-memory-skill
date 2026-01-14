---
name: memory
description: Search past Claude conversations using natural language queries via local memory service
---

# Memory Search

Search your past Claude conversations using natural language.

## Prerequisites

Docker service must be running from `~/Documents/repos/sketch-claude-memory-skill`:

```bash
cd ~/Documents/repos/sketch-claude-memory-skill && docker compose up -d
```

Service: http://localhost:8002

## Search Your Conversations

```bash
curl -s -X POST http://localhost:8002/search \
  -H "Content-Type: application/json" \
  -d '{"query": "YOUR NATURAL LANGUAGE QUERY"}'
```

The service will:
1. Parse your natural language query
2. Search both keyword (FTS5) and semantic (vector) indexes
3. Combine results using reciprocal rank fusion
4. Return a formatted response with relevant conversation excerpts

### Search Examples

```bash
# Find discussions about a topic
curl -s -X POST http://localhost:8002/search \
  -H "Content-Type: application/json" \
  -d '{"query": "what did we discuss about cosmos-sdk authentication"}'

# Recall recent work
curl -s -X POST http://localhost:8002/search \
  -H "Content-Type: application/json" \
  -d '{"query": "what was I working on in dymension-rdk last week"}'

# Find error solutions
curl -s -X POST http://localhost:8002/search \
  -H "Content-Type: application/json" \
  -d '{"query": "how did we fix the signature verification bug"}'

# General recall
curl -s -X POST http://localhost:8002/search \
  -H "Content-Type: application/json" \
  -d '{"query": "what projects have I been working on recently"}'
```

## Other Endpoints

```bash
# Health check
curl -s http://localhost:8002/health

# Database stats
curl -s http://localhost:8002/stats

# Re-index conversation archives
curl -s -X POST http://localhost:8002/ingest
```

## Troubleshooting

```bash
# Check container status
docker ps | grep memory

# Restart service
cd ~/Documents/repos/sketch-claude-memory-skill && docker compose restart

# View logs
docker compose -f ~/Documents/repos/sketch-claude-memory-skill/docker-compose.yml logs -f memory
```

## When to Use This

- Recalling something discussed in a previous session
- Finding how a problem was solved before
- Looking for context from past work on a project
- Referencing previous decisions or implementations
