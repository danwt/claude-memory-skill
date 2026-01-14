from db import get_connection, fts_search, vec_search, get_stats
from embedder import embed_text
from llm import generate_search_plan, format_response
import logging

logger = logging.getLogger(__name__)

RRF_K = 60


def reciprocal_rank_fusion(
    ranked_lists: list[list[dict]], k: int = RRF_K
) -> list[dict]:
    scores: dict[str, float] = {}
    docs: dict[str, dict] = {}

    for ranked_list in ranked_lists:
        for rank, doc in enumerate(ranked_list, 1):
            doc_id = doc["id"]
            scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (k + rank)
            if doc_id not in docs:
                docs[doc_id] = doc

    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    return [docs[doc_id] for doc_id in sorted_ids]


def hybrid_search(query: str) -> tuple[list[dict], dict]:
    conn = get_connection()
    stats = get_stats(conn)

    if stats["total_messages"] == 0:
        conn.close()
        return [], stats

    plan = generate_search_plan(query)
    logger.info("search plan generated: plan=%s", plan)

    all_results: list[list[dict]] = []

    for fts_query in plan.get("fts_queries", []):
        try:
            results = fts_search(conn, fts_query, limit=20)
            if results:
                all_results.append(results)
                logger.debug(
                    "fts search complete: query=%s results=%d", fts_query, len(results)
                )
        except Exception as e:
            logger.debug("fts search error: query=%s error=%s", fts_query, e)

    vec_query = plan.get("vec_query", query)
    try:
        embedding = embed_text(vec_query)
        vec_results = vec_search(conn, embedding, limit=20)
        if vec_results:
            all_results.append(vec_results)
            logger.debug("vec search complete: results=%d", len(vec_results))
    except Exception as e:
        logger.debug("vec search error: error=%s", e)

    conn.close()

    if not all_results:
        return [], stats

    fused = reciprocal_rank_fusion(all_results)
    logger.info("hybrid search complete: total_results=%d", len(fused))

    return fused, stats


def search(query: str) -> str:
    logger.info("search request: query=%s", query)
    results, stats = hybrid_search(query)
    response = format_response(query, results, stats)
    logger.info("search response generated: length=%d", len(response))
    return response
