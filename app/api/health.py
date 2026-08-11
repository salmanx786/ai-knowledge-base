from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Liveness probe: is the process up and serving requests?

    Deliberately does not touch the database. It is a *liveness* signal (used by
    the Docker/Compose healthcheck to know the app is running), not a
    *readiness* check of downstream dependencies -- a transient DB blip should
    not make the container report itself dead and get killed.
    """
    return {"status": "healthy"}
