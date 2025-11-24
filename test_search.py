"""
Test script for RAG search
Tests various search scenarios
"""
import sys
from src.rag.retriever import get_rag_retriever, RAGFilters


def print_results(results, query):
    """Pretty print search results"""
    print(f"\n{'='*80}")
    print(f"Query: {query}")
    print(f"Found {len(results)} results")
    print('='*80)

    for i, result in enumerate(results, 1):
        print(f"\n[{i}] {result.subject}")
        print(f"    From: {result.sender_name} <{result.sender_email}>")
        print(f"    Date: {result.date}")
        print(f"    Similarity: {result.similarity_score:.3f}")
        print(f"    Context: {result.context_type}")
        if result.category:
            print(f"    Category: {result.category}")
        if result.dossier_id:
            print(f"    Dossier: {result.dossier_id}")
        print(f"    Body: {result.body[:150]}...")


def test_basic_search(retriever):
    """Test basic vector search"""
    print("\n" + "="*80)
    print("TEST 1: Recherche sémantique basique")
    print("="*80)

    query = "Quelles sont les nouvelles de l'expertise médicale?"
    results = retriever.vector_search(query, top_k=5)
    print_results(results, query)


def test_filtered_search(retriever):
    """Test search with filters"""
    print("\n" + "="*80)
    print("TEST 2: Recherche filtrée par catégorie")
    print("="*80)

    query = "rapport"
    filters = RAGFilters(category="expert_medical")
    results = retriever.vector_search(query, top_k=5, filters=filters)
    print_results(results, query)


def test_dossier_search(retriever):
    """Test search by dossier"""
    print("\n" + "="*80)
    print("TEST 3: Recherche par dossier")
    print("="*80)

    filters = RAGFilters(dossier_id="24/00123")
    results = retriever.search_by_metadata_only(filters, limit=10)
    print_results(results, "Tous les emails du dossier 24/00123")


def test_hybrid_search(retriever):
    """Test hybrid search with graph expansion"""
    print("\n" + "="*80)
    print("TEST 4: Recherche hybride avec expansion graphe")
    print("="*80)

    query = "Quelle est la date de l'audience?"
    results = retriever.hybrid_search(
        query,
        top_k=3,
        expand_graph=True,
        expand_threads=True,
        expand_cases=True,
        max_results=10
    )
    print_results(results, query)


def test_urgent_search(retriever):
    """Test search for urgent emails"""
    print("\n" + "="*80)
    print("TEST 5: Recherche des emails urgents")
    print("="*80)

    filters = RAGFilters(tags=["urgence"])
    results = retriever.search_by_metadata_only(filters, limit=10)
    print_results(results, "Emails urgents")


def test_client_search(retriever):
    """Test search by sender"""
    print("\n" + "="*80)
    print("TEST 6: Recherche par expéditeur (client)")
    print("="*80)

    query = "informations dossier"
    filters = RAGFilters(sender_email="jean.martin@email.fr")
    results = retriever.vector_search(query, top_k=5, filters=filters)
    print_results(results, f"{query} (from jean.martin@email.fr)")


def main():
    """Run all search tests"""
    print("=== Tests de Recherche RAG ===\n")

    try:
        # Initialize retriever
        print("Initialisation du retriever RAG...")
        retriever = get_rag_retriever()
        print("✓ Retriever initialisé\n")

        # Run tests
        test_basic_search(retriever)
        test_filtered_search(retriever)
        test_dossier_search(retriever)
        test_hybrid_search(retriever)
        test_urgent_search(retriever)
        test_client_search(retriever)

        print("\n" + "="*80)
        print("=== Tous les tests terminés! ===")
        print("="*80)

    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
