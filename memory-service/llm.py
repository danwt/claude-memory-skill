import os
from openai import OpenAI
import logging

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "google/gemini-2.0-flash-lite-001")

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY,
        )
    return _client


def chat(system_prompt: str, user_message: str) -> str:
    client = get_client()
    logger.debug("llm request: model=%s", OPENROUTER_MODEL)
    response = client.chat.completions.create(
        model=OPENROUTER_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.3,
        max_tokens=2000,
    )
    result = response.choices[0].message.content or ""
    logger.debug("llm response received: length=%d", len(result))
    return result


SEARCH_AGENT_SYSTEM = """You are a search agent for a conversation memory database.
Your job is to help find relevant past conversations based on user queries.

You have access to two search methods:
1. FTS (full-text search) - keyword matching with BM25 ranking
2. VEC (vector search) - semantic similarity search

Given a user query, you should:
1. Analyze what the user is looking for
2. Generate appropriate search queries
3. Evaluate results and decide if more searches are needed
4. Format a helpful response

Respond in JSON format:
{
    "fts_queries": ["query1", "query2"],  // FTS5 queries (use AND/OR/NOT, quotes for phrases)
    "vec_query": "semantic search text",   // Text to embed for vector search
    "reasoning": "brief explanation"
}

FTS5 query syntax tips:
- Use AND/OR/NOT: cosmos AND auth
- Use quotes for phrases: "error handling"
- Use * for prefix matching: cosmos*
- Use NEAR for proximity: NEAR(cosmos auth, 5)
"""

RESPONSE_FORMAT_SYSTEM = """You are formatting search results from a conversation memory database.

Given the user's original query and the search results, create a clear, helpful response that:
1. Directly answers or addresses what the user was looking for
2. Includes relevant quotes/excerpts from conversations
3. Mentions when and in what project context the conversations occurred
4. Notes if the search didn't find relevant results

Keep the response concise but informative. Use markdown formatting."""


def generate_search_plan(query: str) -> dict:
    response = chat(SEARCH_AGENT_SYSTEM, query)
    try:
        import json
        clean = response.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        if clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        return json.loads(clean.strip())
    except Exception as e:
        logger.error("failed to parse search plan: error=%s", e)
        return {
            "fts_queries": [query],
            "vec_query": query,
            "reasoning": "Fallback to direct query",
        }


def format_response(query: str, results: list[dict], stats: dict) -> str:
    if not results:
        return f"No relevant conversations found for: {query}"

    results_text = ""
    for i, r in enumerate(results[:10], 1):
        timestamp = r.get("timestamp", "unknown")[:10]
        project = r.get("project_path", "unknown").split("/")[-1]
        role = r.get("role", "unknown")
        content = r.get("content", "")[:500]
        results_text += f"\n---\n**Result {i}** ({timestamp}, {project}, {role}):\n{content}\n"

    prompt = f"""User query: {query}

Search results:
{results_text}

Database stats: {stats['total_messages']} messages across {stats['sessions']} sessions in {stats['projects']} projects.

Format a helpful response for the user."""

    return chat(RESPONSE_FORMAT_SYSTEM, prompt)
