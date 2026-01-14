# Memory Search Skill

Search your past Claude conversations using natural language.

## Prerequisites

The memory service must be running on localhost:8002. Start it with:
```bash
cd ~/path/to/claude-memory-skill && docker compose up -d
```

## Usage

When you need to recall something from a previous conversation, search your memory:

```bash
curl -s -X POST http://localhost:8002/search \
  -H "Content-Type: application/json" \
  -d '{"query": "YOUR NATURAL LANGUAGE QUERY HERE"}'
```

The service will:
1. Parse your natural language query
2. Search both keyword (FTS5) and semantic (vector) indexes
3. Combine results using reciprocal rank fusion
4. Return a formatted response with relevant conversation excerpts

## Examples

Find discussions about a topic:
```bash
curl -s -X POST http://localhost:8002/search \
  -H "Content-Type: application/json" \
  -d '{"query": "what did we discuss about cosmos-sdk authentication"}'
```

Recall recent work:
```bash
curl -s -X POST http://localhost:8002/search \
  -H "Content-Type: application/json" \
  -d '{"query": "what was I working on in dymension-rdk last week"}'
```

Find error solutions:
```bash
curl -s -X POST http://localhost:8002/search \
  -H "Content-Type: application/json" \
  -d '{"query": "how did we fix the signature verification bug"}'
```

## Other Endpoints

Check service health:
```bash
curl -s http://localhost:8002/health
```

Get database stats:
```bash
curl -s http://localhost:8002/stats
```

Trigger re-ingest of conversation archives:
```bash
curl -s -X POST http://localhost:8002/ingest
```

## When to Use

Use this skill when:
- You need to recall something discussed in a previous session
- You want to find how a problem was solved before
- You're looking for context from past work on a project
- You need to reference previous decisions or implementations
