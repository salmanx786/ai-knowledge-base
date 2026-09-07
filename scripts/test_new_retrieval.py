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


QUESTIONS = [
    "Who is the author?",
    "What is an offer?",
    "What does an offer consist of?",
    "Why is the offer important to a business?",
    "What is a grand slam offer?",
    "What is the value equation?",
    "How does scarcity affect an offer?",
    "How does urgency affect an offer?",
    "What are bonuses?",
    "What is a guarantee?",
    "Why does naming an offer matter?",
]


async def main() -> None:
    async with SessionFactory() as session:
        search = SearchService(session)

        for question in QUESTIONS:
            results = await search.search(
                owner_id=3,
                query=question,
                limit=5,
            )

            print(f"\nQUESTION: {question}")

            for result in results:
                print(
                    f"chunk={result.chunk_index} "
                    f"semantic={result.semantic_score:.4f} "
                    f"rerank={result.rerank_score:.4f}"
                )


if __name__ == "__main__":
    asyncio.run(main())
