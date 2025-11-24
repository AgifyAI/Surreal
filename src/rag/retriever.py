"""
RAG Retrieval System
Combines vector search, metadata filtering, and graph expansion
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from src.db.connection import SurrealDBClient
from src.embeddings.generator import EmbeddingGenerator


@dataclass
class RAGFilters:
    """Filters for RAG search"""
    category: Optional[str] = None
    client_id: Optional[str] = None
    dossier_id: Optional[str] = None
    sender_email: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    tags: Optional[List[str]] = None


@dataclass
class RAGResult:
    """Single RAG search result"""
    email_id: str
    subject: str
    body: str
    sender_email: str
    sender_name: str
    date: str
    similarity_score: float
    context_type: str  # "direct_match", "thread_member", "same_case", "same_person"
    category: Optional[str] = None
    dossier_id: Optional[str] = None


class RAGRetriever:
    """Hybrid RAG retrieval system"""

    def __init__(self, db_client: SurrealDBClient, embedding_gen: EmbeddingGenerator):
        """
        Initialize RAG retriever

        Args:
            db_client: SurrealDB client
            embedding_gen: Embedding generator
        """
        self.db = db_client
        self.embedding_gen = embedding_gen

    def _build_where_clause(self, filters: Optional[RAGFilters]) -> str:
        """Build WHERE clause from filters"""
        if not filters:
            return ""

        conditions = []

        if filters.category:
            conditions.append(f"category = '{filters.category}'")

        if filters.client_id:
            conditions.append(f"client_id = '{filters.client_id}'")

        if filters.dossier_id:
            conditions.append(f"dossier_id = '{filters.dossier_id}'")

        if filters.sender_email:
            conditions.append(f"sender_email = '{filters.sender_email}'")

        if filters.date_from:
            conditions.append(f"date >= '{filters.date_from}'")

        if filters.date_to:
            conditions.append(f"date <= '{filters.date_to}'")

        if filters.tags:
            # Check if any tag is present
            tag_conditions = [f"'{tag}' IN tags" for tag in filters.tags]
            conditions.append(f"({' OR '.join(tag_conditions)})")

        if conditions:
            return "WHERE " + " AND ".join(conditions)

        return ""

    def vector_search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[RAGFilters] = None
    ) -> List[RAGResult]:
        """
        Perform pure vector similarity search

        Args:
            query: Search query
            top_k: Number of results
            filters: Optional metadata filters

        Returns:
            List of RAG results
        """
        # Generate query embedding
        query_embedding = self.embedding_gen.generate(query)

        # Search with vector similarity
        results = self.db.vector_search(
            table="email",
            field="body_embedding",
            embedding=query_embedding,
            limit=top_k,
            filters=self._filters_to_dict(filters) if filters else None
        )

        # Convert to RAG results
        rag_results = []
        for result in results:
            rag_results.append(RAGResult(
                email_id=result.get("id", ""),
                subject=result.get("subject", ""),
                body=result.get("body", ""),
                sender_email=result.get("sender_email", ""),
                sender_name=result.get("sender_name", ""),
                date=result.get("date", ""),
                similarity_score=result.get("similarity", 0.0),
                context_type="direct_match",
                category=result.get("category"),
                dossier_id=result.get("dossier_id")
            ))

        return rag_results

    def _filters_to_dict(self, filters: RAGFilters) -> Dict[str, Any]:
        """Convert filters to dictionary for vector search"""
        filter_dict = {}

        if filters.category:
            filter_dict["category"] = filters.category
        if filters.client_id:
            filter_dict["client_id"] = filters.client_id
        if filters.dossier_id:
            filter_dict["dossier_id"] = filters.dossier_id
        if filters.sender_email:
            filter_dict["sender_email"] = filters.sender_email

        return filter_dict

    def graph_expand_threads(self, email_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Expand search results with emails from same threads

        Args:
            email_ids: List of email IDs to expand

        Returns:
            List of related emails
        """
        if not email_ids:
            return []

        # Build query to get thread members
        email_ids_str = ", ".join([f"'{eid}'" for eid in email_ids])

        query = f"""
        SELECT ->thread_member->email.* AS related FROM email WHERE id IN [{email_ids_str}];
        """

        results = self.db.query(query)

        related_emails = []
        if results and results[0].get("result"):
            for item in results[0]["result"]:
                if item.get("related"):
                    for email in item["related"]:
                        if email:
                            related_emails.append(email)

        return related_emails

    def graph_expand_cases(self, email_ids: List[str], limit: int = 3) -> List[Dict[str, Any]]:
        """
        Expand search results with emails from same dossiers

        Args:
            email_ids: List of email IDs to expand
            limit: Max emails per dossier

        Returns:
            List of related emails
        """
        if not email_ids:
            return []

        email_ids_str = ", ".join([f"'{eid}'" for eid in email_ids])

        query = f"""
        SELECT ->related_to_case->dossier<-related_to_case<-email.* AS related FROM email WHERE id IN [{email_ids_str}];
        """

        results = self.db.query(query)

        related_emails = []
        if results and results[0].get("result"):
            for item in results[0]["result"]:
                if item.get("related"):
                    for email in item["related"]:
                        if email:
                            related_emails.append(email)

        return related_emails[:limit * len(email_ids)]

    def graph_expand_people(self, email_ids: List[str], limit: int = 5) -> List[Dict[str, Any]]:
        """
        Expand search results with emails involving same people

        Args:
            email_ids: List of email IDs to expand
            limit: Max emails per person

        Returns:
            List of related emails
        """
        if not email_ids:
            return []

        email_ids_str = ", ".join([f"'{eid}'" for eid in email_ids])

        query = f"""
        SELECT ->involves->person<-involves<-email.* AS related FROM email WHERE id IN [{email_ids_str}];
        """

        results = self.db.query(query)

        related_emails = []
        if results and results[0].get("result"):
            for item in results[0]["result"]:
                if item.get("related"):
                    for email in item["related"]:
                        if email:
                            related_emails.append(email)

        return related_emails[:limit * len(email_ids)]

    def hybrid_search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[RAGFilters] = None,
        expand_graph: bool = True,
        expand_threads: bool = True,
        expand_cases: bool = True,
        expand_people: bool = False,
        max_results: int = 20
    ) -> List[RAGResult]:
        """
        Hybrid RAG search: Vector search + Graph expansion

        Args:
            query: Search query
            top_k: Number of initial vector search results
            filters: Optional metadata filters
            expand_graph: Enable graph expansion
            expand_threads: Include thread members
            expand_cases: Include same dossier emails
            expand_people: Include emails with same people
            max_results: Maximum total results

        Returns:
            List of RAG results, ranked by relevance
        """
        # Step 1: Vector search
        vector_results = self.vector_search(query, top_k, filters)

        if not expand_graph:
            return vector_results[:max_results]

        # Step 2: Graph expansion
        email_ids = [r.email_id for r in vector_results]
        expanded_emails = []
        seen_ids = set(email_ids)

        # Expand threads
        if expand_threads:
            thread_emails = self.graph_expand_threads(email_ids)
            for email in thread_emails:
                eid = email.get("id")
                if eid and eid not in seen_ids:
                    expanded_emails.append((email, "thread_member"))
                    seen_ids.add(eid)

        # Expand cases
        if expand_cases:
            case_emails = self.graph_expand_cases(email_ids, limit=3)
            for email in case_emails:
                eid = email.get("id")
                if eid and eid not in seen_ids:
                    expanded_emails.append((email, "same_case"))
                    seen_ids.add(eid)

        # Expand people
        if expand_people:
            people_emails = self.graph_expand_people(email_ids, limit=2)
            for email in people_emails:
                eid = email.get("id")
                if eid and eid not in seen_ids:
                    expanded_emails.append((email, "same_person"))
                    seen_ids.add(eid)

        # Step 3: Convert expanded emails to RAG results
        for email, context_type in expanded_emails:
            vector_results.append(RAGResult(
                email_id=email.get("id", ""),
                subject=email.get("subject", ""),
                body=email.get("body", ""),
                sender_email=email.get("sender_email", ""),
                sender_name=email.get("sender_name", ""),
                date=email.get("date", ""),
                similarity_score=0.0,  # No direct similarity
                context_type=context_type,
                category=email.get("category"),
                dossier_id=email.get("dossier_id")
            ))

        # Step 4: Limit results
        return vector_results[:max_results]

    def search_by_metadata_only(
        self,
        filters: RAGFilters,
        limit: int = 20,
        order_by: str = "date DESC"
    ) -> List[RAGResult]:
        """
        Search by metadata only (no semantic search)

        Args:
            filters: Metadata filters
            limit: Max results
            order_by: Ordering clause

        Returns:
            List of RAG results
        """
        where_clause = self._build_where_clause(filters)

        query = f"""
        SELECT * FROM email
        {where_clause}
        ORDER BY {order_by}
        LIMIT {limit};
        """

        results = self.db.query(query)

        if not results or not results[0].get("result"):
            return []

        rag_results = []
        for result in results[0]["result"]:
            rag_results.append(RAGResult(
                email_id=result.get("id", ""),
                subject=result.get("subject", ""),
                body=result.get("body", ""),
                sender_email=result.get("sender_email", ""),
                sender_name=result.get("sender_name", ""),
                date=result.get("date", ""),
                similarity_score=0.0,
                context_type="metadata_filter",
                category=result.get("category"),
                dossier_id=result.get("dossier_id")
            ))

        return rag_results


def get_rag_retriever() -> RAGRetriever:
    """Factory function to create RAG retriever"""
    from src.db.connection import get_db_client
    from src.embeddings.generator import get_embedding_generator

    db_client = get_db_client()
    embedding_gen = get_embedding_generator()

    return RAGRetriever(db_client, embedding_gen)
