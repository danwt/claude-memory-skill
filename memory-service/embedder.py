from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info("loading embedding model: name=%s", MODEL_NAME)
        _model = SentenceTransformer(MODEL_NAME)
        logger.info("embedding model loaded")
    return _model


def embed_text(text: str) -> list[float]:
    model = get_model()
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_model()
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return embeddings.tolist()
