import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel

from db import init_db, get_connection, get_stats
from ingest import ingest_all
from search import search as do_search

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("initializing database")
    init_db()
    logger.info("running initial ingest")
    ingest_all()
    yield
    logger.info("shutting down")


app = FastAPI(
    title="Claude Memory Service",
    description="Search your past Claude conversations",
    version="0.1.0",
    lifespan=lifespan,
)


class SearchRequest(BaseModel):
    query: str


class SearchResponse(BaseModel):
    result: str


class IngestResponse(BaseModel):
    files: int
    messages: int


class StatsResponse(BaseModel):
    total_messages: int
    sessions: int
    projects: int


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/stats", response_model=StatsResponse)
async def stats():
    conn = get_connection()
    result = get_stats(conn)
    conn.close()
    return result


@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    result = do_search(request.query)
    return SearchResponse(result=result)


@app.post("/ingest", response_model=IngestResponse)
async def ingest(background_tasks: BackgroundTasks):
    result = ingest_all()
    return IngestResponse(**result)
