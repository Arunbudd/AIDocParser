import io
import json
import logging

import pdfplumber

from fastapi import APIRouter, Depends, UploadFile, File, Body, HTTPException, Path
from sqlalchemy.orm import Session

from app.embedding_store import EmbeddingStore
from app.sessions import get_db
import app.document as doc_model
import app.document_chunk as doc_chunk_model

from app.chunk import chunk_text
from app.async_llm import summarize_entire_document, answer_question_async

import tiktoken
ENC = tiktoken.get_encoding("cl100k_base")
MAX_CTX_TOKENS = 12000
router = APIRouter()
store = EmbeddingStore()


@router.get("/documents")
def list_documents(db: Session = Depends(get_db)):
    documents = db.query(doc_model.Document).all()
    return {
        "total_documents": len(documents),
        "documents": [
            {"filename": doc.filename, "summary": doc.summary}
            for doc in documents
        ]
    }


@router.delete("/documents/{filename}")
def delete_document(filename: str = Path(...), db: Session = Depends(get_db)):
    document = db.query(doc_model.Document).filter_by(filename=filename).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Delete chunks first
    db.query(doc_chunk_model.DocumentChunk).filter_by(document_id=document.id).delete()
    # Then delete the document
    db.delete(document)
    db.commit()

    return {"message": f"Document '{filename}' and all its chunks have been deleted."}


def extract_pdf_text(file_bytes: bytes) -> str:
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
    if not text.strip():
        raise HTTPException(status_code=400, detail="No readable text found in PDF.")
    return text


def insert_document_with_chunks(db: Session, filename: str, text: str, summary: str) -> doc_model.Document:
    doc = doc_model.Document(filename=filename, content=text, summary=summary)
    db.add(doc)
    db.flush()
    chunks = chunk_text(text, max_tokens=1200)
    db.bulk_save_objects([
        doc_chunk_model.DocumentChunk(
            document_id=doc.id,
            chunk_index=i,
            chunk_text=chunk,
            embedding=json.dumps(store.embed_text(chunk))
        )
        for i, chunk in enumerate(chunks)
    ])
    return doc


@router.post("/upload")
async def upload_doc(file: UploadFile = File(...), replace: bool = False, db: Session = Depends(get_db)):
    filename = file.filename
    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    text = extract_pdf_text(contents)
    ensure_token_limit(text)
    summary = await summarize_entire_document(text)

    existing_doc = db.query(doc_model.Document).filter_by(filename=filename).first()
    if existing_doc and not replace:
        raise HTTPException(status_code=409, detail=f"Document '{filename}' already exists!")

    try:
        if existing_doc and replace:
            db.delete(existing_doc)

        doc = insert_document_with_chunks(db, filename, text, summary)
        db.commit()
        db.refresh(doc)

        return {
            "filename": filename,
            "summary": summary,
            "message": "Document replaced and chunks stored." if existing_doc else "New document saved."
        }
    except Exception as e:
        db.rollback()
        logging.exception(f"Error while saving {filename}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error while saving document.")


def get_document_context_from_db(db: Session, filename: str) -> str:
    doc = db.query(doc_model.Document).filter(doc_model.Document.filename == filename).first()
    return doc.summary or doc.content or "" if doc else ""


def build_faiss_index_from_db(filename: str, db: Session, store: EmbeddingStore, chunk) -> bool:
    doc = db.query(doc_model.Document).filter(doc_model.Document.filename == filename).first()
    if not doc:
        return False

    chunks = db.query(doc_chunk_model.DocumentChunk).filter(
        doc_chunk_model.DocumentChunk.document_id == doc.id
    ).order_by(doc_chunk_model.DocumentChunk.chunk_index).all()

    for chunk in chunks:
        embedding = json.loads(chunk.embedding)
        store.add_chunk(chunk.chunk_text, doc.id, chunk.chunk_index, embedding=embedding, add_embedding_direct=True)

    return True


@router.post("/ask")
async def ask_question_route(
        question: str = Body(..., embed=True),
        filename: str = Body(..., embed=True),
        db: Session = Depends(get_db)
):
    # Step 1: Build FAISS index from DB
    build_success = build_faiss_index_from_db(filename, db, store)
    if not build_success:
        raise HTTPException(status_code=404, detail="Document not found or has no chunks.")

    # Step 2: Search for relevant chunks
    relevant_chunks = store.search(question, top_k=3)

    # Step 3: Prepare context
    if relevant_chunks:
        context = "\n\n".join(relevant_chunks)
    else:
        # Fallback to full document if chunks are empty
        context = get_document_context_from_db(db, filename)
        if not context:
            raise HTTPException(status_code=404, detail="Document content not found for fallback.")

    # Step 4: Answer question via LLM
    answer = await answer_question_async(question, context)

    return {
        "filename": filename,
        "question": question,
        "answer": answer
    }


def ensure_token_limit(text: str):
    if len(ENC.encode(text)) > MAX_CTX_TOKENS:
        raise HTTPException(status_code=413, detail="Document too large to process")
