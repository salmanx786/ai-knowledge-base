import asyncio

from app.models import chunk, conversation, document, message, organization, organization_member, user
from app.db.engine import engine
from app.db.session import SessionFactory
from app.services.search_service import SearchService


TESTS = [
    ("Who is the author?", 0),
    ("Who wrote it?", 0),
    ("What is the author's name?", 0),
    ("What is this book about?", 28),
    ("What is an offer?", 22),
    ("How do you make an offer compelling?", 22),
]


async def main() -> None:
    async with SessionFactory() as session:
        search = SearchService(session)

        total = len(TESTS)
        hits = 0

        for question, expected_chunk in TESTS:
            results = await search.search(
                owner_id=3,
                query=question,
                limit=5,
            )

            chunk_ids = [result.chunk_index for result in results]
            hit = expected_chunk in chunk_ids

            if hit:
                hits += 1

            print(f"\nQ: {question}")
            print(f"Expected chunk: {expected_chunk}")
            print(f"Retrieved: {chunk_ids}")
            print(f"Hit@5: {hit}")

            for result in results[:3]:
                print(
                    f"  chunk={result.chunk_index} "
                    f"score={result.score:.4f}"
                )

        print(f"\nRecall@5: {hits}/{total} = {hits / total:.1%}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
