import asyncio

from app.models import (
    chunk,
    conversation,
    document,
    message,
    organization,
    organization_member,
    user,
)

from app.db.engine import engine
from app.db.session import SessionFactory
from app.services.search_service import SearchService
from sentence_transformers import CrossEncoder


QUESTIONS = [
    "Who is the author?",
    "Who wrote the book?",
    "What is an offer?",
    "What does an offer consist of?",
    "Why is the offer important to a business?",
    "What is a grand slam offer?",
    "How can an offer increase profits?",
    "What is the value equation?",
    "How does scarcity affect an offer?",
    "How does urgency affect an offer?",
    "What are bonuses?",
    "What is a guarantee?",
    "Why does naming an offer matter?",
    "What is the book about?",
    "How can an entrepreneur make an offer more compelling?",
]


async def main() -> None:
    reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

    async with SessionFactory() as session:
        search = SearchService(session)

        semantic_hits = 0
        reranked_hits = 0

        for question in QUESTIONS:
            results = await search.search(
                owner_id=3,
                query=question,
                limit=20,
            )

            semantic_top5 = results[:5]

            pairs = [(question, result.content) for result in results]
            scores = reranker.predict(pairs)

            ranked = sorted(
                zip(scores, results, strict=True),
                key=lambda x: float(x[0]),
                reverse=True,
            )

            reranked_top5 = [result for _, result in ranked[:5]]

            print(f"\nQUESTION: {question}")
            print(
                "Semantic:",
                [r.chunk_index for r in semantic_top5],
            )
            print(
                "Reranked:",
                [r.chunk_index for r in reranked_top5],
            )

        print("\nCompleted comparison.")
        print("Semantic and reranked results are ready for manual relevance review.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
