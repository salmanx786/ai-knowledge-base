"""Document HTTP endpoints.

Same thin-controller style as the auth router: validate input via schemas,
delegate to DocumentService, translate the one domain error into an
HTTPException. Every route is protected by ``get_current_user`` and passes the
authenticated user's id to the service as the owner -- the client never
supplies ownership, and the service never trusts anything but ``current_user``.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.auth import get_current_user
from app.dependencies.documents import get_document_service
from app.models.user import User
from app.repositories.errors import DocumentNotFoundError
from app.schemas.document import DocumentCreate, DocumentResponse
from app.services.document_service import DocumentService

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a document owned by the current user",
)
async def create_document(
    payload: DocumentCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentResponse:
    """Create a document owned by the authenticated user."""
    document = await service.create_document(
        owner_id=current_user.id, data=payload
    )
    return DocumentResponse.model_validate(document)


@router.get(
    "",
    response_model=list[DocumentResponse],
    status_code=status.HTTP_200_OK,
    summary="List the current user's documents",
)
async def list_documents(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> list[DocumentResponse]:
    """Return every document owned by the authenticated user."""
    documents = await service.list_documents(owner_id=current_user.id)
    return [DocumentResponse.model_validate(doc) for doc in documents]


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get one of the current user's documents",
)
async def get_document(
    document_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentResponse:
    """Return a single document owned by the authenticated user.

    Returns 404 if the document does not exist *or* belongs to another user --
    the two are deliberately indistinguishable.
    """
    try:
        document = await service.get_document(
            document_id=document_id, owner_id=current_user.id
        )
    except DocumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )
    return DocumentResponse.model_validate(document)


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete one of the current user's documents",
)
async def delete_document(
    document_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> None:
    """Delete a document owned by the authenticated user.

    Returns 404 (not 403) when the document is missing or owned by someone
    else, so the endpoint never reveals that another user's document exists.
    """
    try:
        await service.delete_document(
            document_id=document_id, owner_id=current_user.id
        )
    except DocumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )
