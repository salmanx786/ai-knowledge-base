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
    "What is an offer?",
    "How do you make an offer compelling?",
]


async def main() -> None:
    reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

    async with SessionFactory() as session:
        search = SearchService(session)

        for question in QUESTIONS:
            results = await search.search(
                owner_id=3,
                query=question,
                limit=20,
            )

            pairs = [
                (question, result.content)
                for result in results
            ]

            scores = reranker.predict(pairs)

            ranked = sorted(
                zip(scores, results, strict=True),
                key=lambda item: float(item[0]),
                reverse=True,
            )

            print(f"\nQUESTION: {question}")

            for score, result in ranked[:5]:
                print(
                    f"chunk={result.chunk_index} "
                    f"rerank={float(score):.4f} "
                    f"semantic={result.score:.4f}"
                )
                print(result.content[:180].replace("\n", " "))
                print()

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
