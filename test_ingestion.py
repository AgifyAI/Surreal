"""
Test script for email ingestion
Ingests sample emails to test the system
"""
import sys
from datetime import datetime, timedelta

from src.ingestion.pipeline import get_ingestion_pipeline


def create_sample_emails():
    """Create sample emails for testing"""
    base_date = datetime.now()

    return [
        {
            "subject": "Re: Dossier Martin - Accident du 15 janvier",
            "body": """Bonjour Maître,

Suite à notre dernier échange, je vous confirme que le rapport d'expertise médicale sera disponible la semaine prochaine.

Le Dr. Dupont a examiné M. Martin hier et les premiers résultats montrent des lésions importantes au niveau de la colonne vertébrale.

Cordialement,
Expert Medical Service""",
            "sender_email": "expert@medical-service.fr",
            "sender_name": "Dr. Dupont",
            "recipients": ["avocat@law-firm.fr"],
            "cc": [],
            "date": (base_date - timedelta(days=2)).isoformat(),
            "thread_id": "thread_martin_001",
            "message_id": "msg_001",
            "has_attachments": False
        },
        {
            "subject": "Dossier Martin - Demande d'informations",
            "body": """Cher Maître,

Je souhaiterais avoir des nouvelles concernant l'avancement de mon dossier.

L'assurance m'a contacté récemment pour une proposition d'indemnisation que je trouve insuffisante. Pouvons-nous en discuter rapidement?

Merci,
Jean Martin""",
            "sender_email": "jean.martin@email.fr",
            "sender_name": "Jean Martin",
            "recipients": ["avocat@law-firm.fr"],
            "cc": [],
            "date": (base_date - timedelta(days=5)).isoformat(),
            "thread_id": "thread_martin_001",
            "message_id": "msg_002",
            "has_attachments": False
        },
        {
            "subject": "Audience tribunal - Dossier RG 24/00123",
            "body": """Maître,

Je vous informe que l'audience concernant le dossier RG 24/00123 (Affaire Martin c/ Assurance XYZ) est fixée au 15 mars 2024 à 14h00.

Veuillez confirmer votre présence.

Cordialement,
Le Greffe du Tribunal""",
            "sender_email": "greffe@tribunal-paris.fr",
            "sender_name": "Greffe Tribunal de Paris",
            "recipients": ["avocat@law-firm.fr"],
            "cc": [],
            "date": (base_date - timedelta(days=1)).isoformat(),
            "thread_id": "thread_tribunal_001",
            "message_id": "msg_003",
            "has_attachments": False
        },
        {
            "subject": "Re: Proposition transactionnelle - Dossier Durand",
            "body": """Cher confrère,

Suite à nos échanges téléphoniques, je vous confirme que mon client est disposé à accepter la proposition d'indemnisation de 50 000€.

Nous pouvons organiser une rencontre la semaine prochaine pour finaliser les détails.

Cordialement,
Me. Leclerc""",
            "sender_email": "leclerc@avocat.fr",
            "sender_name": "Me. Pierre Leclerc",
            "recipients": ["avocat@law-firm.fr"],
            "cc": [],
            "date": (base_date - timedelta(days=3)).isoformat(),
            "thread_id": "thread_durand_001",
            "message_id": "msg_004",
            "has_attachments": False
        },
        {
            "subject": "URGENT - Délai de prescription - Dossier Durand",
            "body": """Maître,

Attention, le délai de prescription pour le dossier Durand expire dans 15 jours!

Il est impératif de déposer l'assignation avant cette date.

Tous les documents sont prêts et disponibles.

Urgent,
Secrétariat""",
            "sender_email": "secretariat@law-firm.fr",
            "sender_name": "Secrétariat",
            "recipients": ["avocat@law-firm.fr"],
            "cc": [],
            "date": base_date.isoformat(),
            "thread_id": "thread_durand_002",
            "message_id": "msg_005",
            "has_attachments": True
        }
    ]


def main():
    """Run ingestion test"""
    print("=== Test d'ingestion des emails ===\n")

    try:
        # Initialize pipeline
        print("Initialisation du pipeline d'ingestion...")
        pipeline = get_ingestion_pipeline()
        print("✓ Pipeline initialisé\n")

        # Create sample emails
        print("Création des emails de test...")
        emails = create_sample_emails()
        print(f"✓ {len(emails)} emails créés\n")

        # Ingest emails
        print("Ingestion des emails...")
        email_ids = pipeline.ingest_batch(emails)
        print(f"✓ {len(email_ids)} emails ingérés\n")

        # Build graph relations
        print("Construction des relations graphe...")
        pipeline.build_graph_relations(email_ids)
        print("✓ Relations graphe construites\n")

        print("=== Test terminé avec succès! ===")
        print(f"\nEmails ingérés:")
        for i, email_id in enumerate(email_ids, 1):
            print(f"  {i}. {email_id}")

    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
