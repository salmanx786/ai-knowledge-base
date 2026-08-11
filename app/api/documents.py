"""Document HTTP endpoints.

Same thin-controller style as the auth router: delegate to DocumentService and
translate the one domain error into an HTTPException. Every route is protected
by ``get_current_user`` and passes the authenticated user's id to the service
as the owner -- the client never supplies ownership, and the service never
trusts anything but ``current_user``.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from app.config.settings import settings
from app.dependencies.auth import get_current_user
from app.dependencies.documents import get_document_service, get_search_service
from app.models.user import User
from app.repositories.errors import DocumentNotFoundError, TextExtractionError
from app.schemas.document import DocumentResponse, DocumentSummaryResponse
from app.schemas.search import SearchRequest, SearchResultResponse
from app.services.document_service import DocumentService
from app.services.search_service import SearchService

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a PDF and create a document for the current user",
)
async def upload_document(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[DocumentService, Depends(get_document_service)],
    file: Annotated[UploadFile, File(description="PDF file")],
) -> DocumentResponse:
    """Save an uploaded PDF and create the document that describes it.

    Only PDFs are accepted; anything else is rejected with 415. The document is
    owned by the authenticated user -- ownership is never taken from the request.
    A PDF that cannot be read for text extraction returns 400.
    """
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF files are accepted.",
        )

    # Validate file size
    max_size_bytes = settings.max_upload_size_mb * 1024 * 1024
    file_size = 0
    if file.size is not None:
        file_size = file.size
    else:
        # Fallback to seeking to check size dynamically
        try:
            file.file.seek(0, 2)
            file_size = file.file.tell()
            file.file.seek(0)
        except Exception as exc:
            logger.error(f"Failed to determine file size: {exc}")

    if file_size > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File size exceeds the maximum limit of {settings.max_upload_size_mb}MB.",
        )

    try:
        document = await service.upload_document(
            owner_id=current_user.id, upload=file
        )
    except TextExtractionError as exc:
        logger.error(f"Text extraction failed for file {file.filename}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to extract text from the uploaded PDF. The file may be malformed or unreadable.",
        )
    except Exception as exc:
        logger.error(f"Unexpected error during document upload: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during document upload.",
        )
    return DocumentResponse.model_validate(document)



@router.get(
    "",
    response_model=list[DocumentSummaryResponse],
    status_code=status.HTTP_200_OK,
    summary="List the current user's documents",
)
async def list_documents(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[DocumentService, Depends(get_document_service)],
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum number of documents to return")] = 10,
    offset: Annotated[int, Query(ge=0, description="Number of documents to skip")] = 0,
) -> list[DocumentSummaryResponse]:
    """Return every document owned by the authenticated user (paginated)."""
    documents = await service.list_documents(
        owner_id=current_user.id, limit=limit, offset=offset
    )
    return [DocumentSummaryResponse.model_validate(doc) for doc in documents]



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


@router.post(
    "/search",
    response_model=list[SearchResultResponse],
    status_code=status.HTTP_200_OK,
    summary="Search the current user's document chunks by semantic similarity",
)
async def search_documents(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SearchService, Depends(get_search_service)],
    body: SearchRequest,
) -> list[SearchResultResponse]:
    """Return the top-K chunks most similar to ``query``.

    Only chunks belonging to the authenticated user's documents are searched.
    Returns an empty list when the user has no indexed chunks.
    """
    return await service.search(
        owner_id=current_user.id,
        query=body.query,
        limit=body.limit,
    )
