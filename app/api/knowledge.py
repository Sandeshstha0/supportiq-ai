from hashlib import sha256
from pathlib import PurePosixPath

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from app.api.dependencies import get_current_user, require_admin, verify_admin_api_key

from app.schemas.knowledge import (
    KnowledgeDocumentRequest,
    KnowledgeDocumentResponse,
    KnowledgeSearchResponse,
)
from app.services.knowledge_service import add_document
from app.services.knowledge_search_service import search_knowledge
from app.schemas.knowledge_management import (
    KnowledgeDocumentDetails,
    KnowledgeDocumentPage,
    KnowledgeMutationResponse,
)
from app.services.knowledge_management_service import (
    delete_document,
    get_document,
    has_duplicate_content,
    list_documents,
)
from app.services.knowledge_service import replace_document

router = APIRouter(
    prefix="/knowledge",
    tags=["Knowledge Base"],
)

MAX_UPLOAD_BYTES = 1024 * 1024
MAX_UPLOAD_CHARS = 50000


async def _read_text_file(upload: UploadFile) -> tuple[str, str]:
    raw_name = upload.filename or ""
    filename = PurePosixPath(raw_name.replace("\\", "/")).name
    if not filename or PurePosixPath(filename).suffix.casefold() != ".txt":
        raise HTTPException(status_code=415, detail="Only plain text .txt files are supported.")
    contents = await upload.read(MAX_UPLOAD_BYTES + 1)
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds the 1 MiB upload limit.")
    try:
        text = contents.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail="Text files must use UTF-8 encoding.") from exc
    text = text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="The uploaded text file is empty.")
    if len(text) < 10 or len(text) > MAX_UPLOAD_CHARS:
        raise HTTPException(status_code=422, detail="Text content must be between 10 and 50,000 characters.")
    return filename[:255], text


@router.get("/staff/documents", response_model=KnowledgeDocumentPage)
def list_knowledge_documents(
    search: str = Query(default="", max_length=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user=Depends(get_current_user),
):
    return list_documents(search=search, page=page, page_size=page_size)


@router.get("/staff/documents/{document_id}", response_model=KnowledgeDocumentDetails)
def retrieve_knowledge_document(
    document_id: str,
    current_user=Depends(get_current_user),
):
    document = get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Knowledge document not found.")
    return document


@router.post("/staff/documents/upload", response_model=KnowledgeMutationResponse, status_code=201)
async def upload_knowledge_file(
    file: UploadFile = File(...),
    current_user=Depends(require_admin),
):
    filename, text = await _read_text_file(file)
    content_hash = sha256(text.encode("utf-8")).hexdigest()
    if has_duplicate_content(content_hash):
        raise HTTPException(status_code=409, detail="An identical document is already indexed.")
    try:
        result = add_document(
            title=PurePosixPath(filename).stem[:200],
            text=text,
            source=filename,
            filename=filename,
        )
        return {
            "success": result["success"],
            "document_id": result["document_id"],
            "title": result["title"],
            "source": result["source"],
            "filename": result["filename"],
            "created_at": result["created_at"],
            "chunks_stored": result["chunks_stored"],
            "indexing_status": result["indexing_status"],
            "message": result["message"],
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail="The document could not be embedded and indexed; indexing was not confirmed.") from exc


@router.put("/staff/documents/{document_id}", response_model=KnowledgeMutationResponse)
async def replace_knowledge_file(
    document_id: str,
    file: UploadFile = File(...),
    current_user=Depends(require_admin),
):
    current = get_document(document_id)
    if current is None:
        raise HTTPException(status_code=404, detail="Knowledge document not found.")
    if current["legacy"]:
        raise HTTPException(status_code=409, detail="Legacy documents have no safe document ID and cannot be replaced.")
    filename, text = await _read_text_file(file)
    content_hash = sha256(text.encode("utf-8")).hexdigest()
    if has_duplicate_content(content_hash):
        raise HTTPException(status_code=409, detail="An identical document is already indexed.")
    try:
        return replace_document(
            document_id,
            title=PurePosixPath(filename).stem[:200],
            text=text,
            source=filename,
            filename=filename,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="The document could not be safely replaced; verify its indexing state before retrying.") from exc


@router.delete("/staff/documents/{document_id}")
def remove_knowledge_document(
    document_id: str,
    current_user=Depends(require_admin),
):
    document = get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Knowledge document not found.")
    if document["legacy"]:
        raise HTTPException(status_code=409, detail="Legacy documents have no safe document ID and cannot be deleted.")
    try:
        delete_document(document_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="The document vectors could not be deleted.") from exc
    return {"success": True, "document_id": document_id, "message": "Knowledge document deleted."}


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

