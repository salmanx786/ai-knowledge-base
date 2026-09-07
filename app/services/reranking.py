"""Cross-encoder reranking for retrieval candidates."""

from functools import lru_cache

from sentence_transformers import CrossEncoder


MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"


@lru_cache(maxsize=1)
def _load_reranker() -> CrossEncoder:
    return CrossEncoder(MODEL_NAME)


class RerankingService:
    """Score query/chunk pairs with a cross-encoder."""

    def rerank(
        self,
        *,
        query: str,
        results: list,
        limit: int,
    ) -> list:
        if not results:
            return []

        pairs = [(query, result.content) for result in results]
        scores = _load_reranker().predict(pairs)

        ranked = sorted(
            zip(scores, results, strict=True),
            key=lambda item: float(item[0]),
            reverse=True,
        )

        reranked = []

        for score, result in ranked[:limit]:
            reranked.append(
                result.model_copy(
                    update={"rerank_score": float(score)}
                )
            )

        return reranked
