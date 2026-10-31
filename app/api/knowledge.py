from fastapi import APIRouter, HTTPException, Query, Depends
from app.api.dependencies import verify_admin_api_key

from app.schemas.knowledge import (
    KnowledgeDocumentRequest,
    KnowledgeDocumentResponse,
    KnowledgeSearchResponse,
)
from app.services.knowledge_service import add_document
from app.services.knowledge_search_service import search_knowledge

router = APIRouter(
    prefix="/knowledge",
    tags=["Knowledge Base"],
)


@router.post(
    "",
    response_model=KnowledgeDocumentResponse,
    status_code=201,
    dependencies=[Depends(verify_admin_api_key)],
)
def upload_knowledge_document(
    request: KnowledgeDocumentRequest,
):
    try:
        result = add_document(
            title=request.title,
            text=request.text,
            source=request.source,
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail="The knowledge document could not be stored.",
            )

        return result

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to process the knowledge document.",
        )


@router.get(
    "/search",
    response_model=KnowledgeSearchResponse,
)
def search_knowledge_documents(
    q: str = Query(min_length=1, max_length=1000),
    limit: int = Query(default=5, ge=1, le=10),
):
    try:
        results = search_knowledge(
            query=q,
            limit=limit,
        )

        return {
            "query": q,
            "count": len(results),
            "results": results,
        }

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to search the knowledge base.",
        )

