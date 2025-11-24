"""
FastAPI application for RAG Email System
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

from src.rag.retriever import RAGRetriever, RAGFilters, RAGResult, get_rag_retriever
from src.ingestion.pipeline import get_ingestion_pipeline

app = FastAPI(
    title="RAG Email API",
    description="API for RAG-based email search and retrieval for law firm",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances (lazy-loaded)
rag_retriever: Optional[RAGRetriever] = None
ingestion_pipeline = None


def get_retriever() -> RAGRetriever:
    """Get or create RAG retriever instance"""
    global rag_retriever
    if rag_retriever is None:
        rag_retriever = get_rag_retriever()
    return rag_retriever


def get_pipeline():
    """Get or create ingestion pipeline instance"""
    global ingestion_pipeline
    if ingestion_pipeline is None:
        ingestion_pipeline = get_ingestion_pipeline()
    return ingestion_pipeline


# Request/Response Models

class SearchRequest(BaseModel):
    """RAG search request"""
    query: str = Field(..., description="Search query")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of initial results")
    filters: Optional[dict] = Field(default=None, description="Metadata filters")
    expand_graph: bool = Field(default=True, description="Enable graph expansion")
    expand_threads: bool = Field(default=True, description="Include thread members")
    expand_cases: bool = Field(default=True, description="Include same dossier emails")
    expand_people: bool = Field(default=False, description="Include emails with same people")
    max_results: int = Field(default=20, ge=1, le=100, description="Maximum total results")


class EmailResult(BaseModel):
    """Email search result"""
    email_id: str
    subject: str
    body: str
    sender_email: str
    sender_name: str
    date: str
    similarity_score: float
    context_type: str
    category: Optional[str] = None
    dossier_id: Optional[str] = None


class SearchResponse(BaseModel):
    """RAG search response"""
    results: List[EmailResult]
    total_results: int
    query: str


class IngestEmailRequest(BaseModel):
    """Email ingestion request"""
    subject: str
    body: str
    sender_email: str
    sender_name: str
    recipients: List[str] = Field(default_factory=list)
    cc: List[str] = Field(default_factory=list)
    date: Optional[str] = None
    thread_id: Optional[str] = None
    message_id: Optional[str] = None
    in_reply_to: Optional[str] = None
    has_attachments: bool = False


class IngestResponse(BaseModel):
    """Ingestion response"""
    email_id: str
    status: str


# API Endpoints

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "RAG Email API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/rag/search", response_model=SearchResponse)
async def search_emails(request: SearchRequest):
    """
    Search emails using RAG (vector search + graph expansion)

    Example request:
    ```json
    {
        "query": "Quel est le dernier email du client Martin?",
        "top_k": 5,
        "filters": {
            "category": "client",
            "client_id": "martin_123"
        },
        "expand_graph": true,
        "max_results": 20
    }
    ```
    """
    try:
        retriever = get_retriever()

        # Parse filters
        filters = None
        if request.filters:
            filters = RAGFilters(
                category=request.filters.get("category"),
                client_id=request.filters.get("client_id"),
                dossier_id=request.filters.get("dossier_id"),
                sender_email=request.filters.get("sender_email"),
                date_from=request.filters.get("date_from"),
                date_to=request.filters.get("date_to"),
                tags=request.filters.get("tags")
            )

        # Perform search
        results = retriever.hybrid_search(
            query=request.query,
            top_k=request.top_k,
            filters=filters,
            expand_graph=request.expand_graph,
            expand_threads=request.expand_threads,
            expand_cases=request.expand_cases,
            expand_people=request.expand_people,
            max_results=request.max_results
        )

        # Convert to response
        email_results = [
            EmailResult(
                email_id=r.email_id,
                subject=r.subject,
                body=r.body,
                sender_email=r.sender_email,
                sender_name=r.sender_name,
                date=r.date,
                similarity_score=r.similarity_score,
                context_type=r.context_type,
                category=r.category,
                dossier_id=r.dossier_id
            )
            for r in results
        ]

        return SearchResponse(
            results=email_results,
            total_results=len(email_results),
            query=request.query
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/rag/search/simple")
async def simple_search(
    q: str = Query(..., description="Search query"),
    top_k: int = Query(default=10, ge=1, le=50, description="Number of results"),
    category: Optional[str] = Query(default=None, description="Filter by category"),
    sender: Optional[str] = Query(default=None, description="Filter by sender email"),
    dossier_id: Optional[str] = Query(default=None, description="Filter by dossier"),
    expand: bool = Query(default=True, description="Enable graph expansion")
):
    """
    Simple search endpoint with query parameters

    Example: GET /api/rag/search/simple?q=expertise+medicale&category=expert_medical&top_k=10
    """
    try:
        retriever = get_retriever()

        # Build filters
        filters = None
        if category or sender or dossier_id:
            filters = RAGFilters(
                category=category,
                sender_email=sender,
                dossier_id=dossier_id
            )

        # Perform search
        results = retriever.hybrid_search(
            query=q,
            top_k=top_k,
            filters=filters,
            expand_graph=expand,
            max_results=top_k * 2
        )

        # Convert to response
        email_results = [
            EmailResult(
                email_id=r.email_id,
                subject=r.subject,
                body=r.body[:500],  # Truncate body for simple response
                sender_email=r.sender_email,
                sender_name=r.sender_name,
                date=r.date,
                similarity_score=r.similarity_score,
                context_type=r.context_type,
                category=r.category,
                dossier_id=r.dossier_id
            )
            for r in results
        ]

        return SearchResponse(
            results=email_results,
            total_results=len(email_results),
            query=q
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/emails/ingest", response_model=IngestResponse)
async def ingest_email(request: IngestEmailRequest):
    """
    Ingest a single email into the system

    Example request:
    ```json
    {
        "subject": "Re: Dossier Martin - Expertise medicale",
        "body": "Bonjour, voici le rapport d'expertise...",
        "sender_email": "expert@medical.fr",
        "sender_name": "Dr. Dupont",
        "recipients": ["avocat@law.fr"],
        "date": "2024-01-15T10:30:00"
    }
    ```
    """
    try:
        pipeline = get_pipeline()

        # Prepare email data
        email_data = {
            "subject": request.subject,
            "body": request.body,
            "sender_email": request.sender_email,
            "sender_name": request.sender_name,
            "recipients": request.recipients,
            "cc": request.cc,
            "date": request.date or datetime.now().isoformat(),
            "thread_id": request.thread_id or "",
            "message_id": request.message_id or "",
            "in_reply_to": request.in_reply_to,
            "has_attachments": request.has_attachments
        }

        # Ingest email
        email_id = pipeline.ingest_email(email_data)

        # Build graph relations for this email
        pipeline.build_graph_relations([email_id])

        return IngestResponse(
            email_id=email_id,
            status="success"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def get_stats():
    """Get system statistics"""
    try:
        retriever = get_retriever()

        # Get email count
        email_count_result = retriever.db.query("SELECT count() FROM email GROUP ALL;")
        email_count = 0
        if email_count_result and email_count_result[0].get("result"):
            email_count = email_count_result[0]["result"][0].get("count", 0)

        # Get category distribution
        category_result = retriever.db.query(
            "SELECT category, count() FROM email GROUP BY category;"
        )
        categories = {}
        if category_result and category_result[0].get("result"):
            for item in category_result[0]["result"]:
                categories[item.get("category", "unknown")] = item.get("count", 0)

        return {
            "total_emails": email_count,
            "categories": categories,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    import os

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))

    uvicorn.run(app, host=host, port=port)
