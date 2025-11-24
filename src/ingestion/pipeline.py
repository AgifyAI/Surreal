"""
Main ingestion pipeline
Orchestrates email extraction, enrichment, embedding, and storage
"""
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.db.connection import SurrealDBClient
from src.embeddings.generator import EmbeddingGenerator
from src.ingestion.metadata_enricher import MetadataEnricher


class IngestionPipeline:
    """Complete email ingestion pipeline"""

    def __init__(
        self,
        db_client: SurrealDBClient,
        embedding_gen: EmbeddingGenerator,
        metadata_enricher: MetadataEnricher
    ):
        """
        Initialize pipeline

        Args:
            db_client: SurrealDB client
            embedding_gen: Embedding generator
            metadata_enricher: Metadata enricher
        """
        self.db = db_client
        self.embedding_gen = embedding_gen
        self.enricher = metadata_enricher

    def ingest_email(self, email_data: Dict[str, Any]) -> str:
        """
        Ingest a single email

        Args:
            email_data: Raw email data

        Returns:
            Inserted email ID
        """
        # Step 1: Enrich metadata
        enriched = self.enricher.enrich(email_data)

        # Step 2: Generate embedding
        subject = enriched.get("subject", "")
        body = enriched.get("body", "")
        embedding = self.embedding_gen.generate_for_email(subject, body)

        # Step 3: Prepare data for insertion
        email_record = {
            "subject": subject,
            "body": body,
            "body_embedding": embedding,
            "sender_email": enriched.get("sender_email", ""),
            "sender_name": enriched.get("sender_name", ""),
            "recipients": enriched.get("recipients", []),
            "cc": enriched.get("cc", []),
            "date": enriched.get("date", datetime.now().isoformat()),
            "thread_id": enriched.get("thread_id", ""),
            "message_id": enriched.get("message_id", ""),
            "in_reply_to": enriched.get("in_reply_to"),
            "category": enriched.get("category"),
            "client_id": enriched.get("client_id"),
            "dossier_id": enriched.get("dossier_id"),
            "priority": enriched.get("priority"),
            "tags": enriched.get("tags", []),
            "has_attachments": enriched.get("has_attachments", False),
            "language": enriched.get("language", "fr")
        }

        # Step 4: Insert into database
        result = self.db.create("email", email_record)

        email_id = result.get("id")
        print(f"Inserted email: {email_id}")

        return email_id

    def ingest_batch(self, emails: List[Dict[str, Any]], batch_size: int = 10) -> List[str]:
        """
        Ingest multiple emails in batches

        Args:
            emails: List of raw email data
            batch_size: Number of emails to process at once

        Returns:
            List of inserted email IDs
        """
        email_ids = []

        print(f"Ingesting {len(emails)} emails...")

        for i, email_data in enumerate(emails, 1):
            try:
                email_id = self.ingest_email(email_data)
                email_ids.append(email_id)

                if i % batch_size == 0:
                    print(f"Progress: {i}/{len(emails)} emails ingested")

            except Exception as e:
                print(f"Error ingesting email {i}: {e}")
                continue

        print(f"Completed: {len(email_ids)} emails ingested successfully")
        return email_ids

    def build_graph_relations(self, email_ids: Optional[List[str]] = None):
        """
        Build graph relations for emails

        Args:
            email_ids: Specific email IDs to process, or None for all
        """
        print("Building graph relations...")

        # Get emails to process
        if email_ids:
            emails = []
            for email_id in email_ids:
                email = self.db.select("email", email_id.split(':')[1])
                if email:
                    emails.extend(email)
        else:
            emails = self.db.select("email")

        # Build thread relations
        threads = {}
        for email in emails:
            thread_id = email.get("thread_id")
            if thread_id:
                if thread_id not in threads:
                    threads[thread_id] = []
                threads[thread_id].append(email.get("id"))

        # Create thread_member relations
        for thread_id, email_ids_in_thread in threads.items():
            for email_id in email_ids_in_thread:
                for other_email_id in email_ids_in_thread:
                    if email_id != other_email_id:
                        try:
                            self.db.relate(email_id, "thread_member", other_email_id)
                        except:
                            pass  # Relation may already exist

        print(f"Created thread relations for {len(threads)} threads")

        # Build reply relations
        reply_count = 0
        for email in emails:
            in_reply_to = email.get("in_reply_to")
            if in_reply_to:
                # Find original email by message_id
                original_emails = self.db.query(
                    f"SELECT id FROM email WHERE message_id = '{in_reply_to}' LIMIT 1;"
                )
                if original_emails and original_emails[0].get("result"):
                    original_id = original_emails[0]["result"][0].get("id")
                    try:
                        self.db.relate(email.get("id"), "replies_to", original_id)
                        reply_count += 1
                    except:
                        pass

        print(f"Created {reply_count} reply relations")

        # Build person relations
        person_cache = {}

        def get_or_create_person(email_addr: str, name: str = "") -> str:
            """Get or create person record"""
            if email_addr in person_cache:
                return person_cache[email_addr]

            # Check if person exists
            existing = self.db.query(
                f"SELECT id FROM person WHERE email = '{email_addr}' LIMIT 1;"
            )

            if existing and existing[0].get("result"):
                person_id = existing[0]["result"][0].get("id")
            else:
                # Create person
                person_data = {
                    "email": email_addr,
                    "name": name or email_addr,
                    "role": "autre"
                }
                person = self.db.create("person", person_data)
                person_id = person.get("id")

            person_cache[email_addr] = person_id
            return person_id

        # Create involves relations
        involves_count = 0
        for email in emails:
            email_id = email.get("id")

            # Add sender
            sender_email = email.get("sender_email")
            sender_name = email.get("sender_name", "")
            if sender_email:
                try:
                    person_id = get_or_create_person(sender_email, sender_name)
                    self.db.relate(email_id, "involves", person_id)
                    involves_count += 1
                except:
                    pass

            # Add recipients
            for recipient in email.get("recipients", []):
                try:
                    person_id = get_or_create_person(recipient)
                    self.db.relate(email_id, "involves", person_id)
                    involves_count += 1
                except:
                    pass

        print(f"Created {involves_count} person involvement relations")

        # Build dossier relations
        dossier_cache = {}

        def get_or_create_dossier(dossier_id: str) -> str:
            """Get or create dossier record"""
            if dossier_id in dossier_cache:
                return dossier_cache[dossier_id]

            # Check if dossier exists
            existing = self.db.query(
                f"SELECT id FROM dossier WHERE id = 'dossier:{dossier_id}' LIMIT 1;"
            )

            if existing and existing[0].get("result"):
                doss_id = existing[0]["result"][0].get("id")
            else:
                # Create dossier
                dossier_data = {
                    "client_name": "",
                    "description": f"Dossier {dossier_id}"
                }
                # Use specific ID
                dossier = self.db.query(
                    f"CREATE dossier:{dossier_id} CONTENT {{'client_name': '', 'description': 'Dossier {dossier_id}'}};"
                )
                doss_id = f"dossier:{dossier_id}"

            dossier_cache[dossier_id] = doss_id
            return doss_id

        # Create related_to_case relations
        case_count = 0
        for email in emails:
            dossier_id = email.get("dossier_id")
            if dossier_id:
                try:
                    doss_record_id = get_or_create_dossier(dossier_id)
                    self.db.relate(email.get("id"), "related_to_case", doss_record_id)
                    case_count += 1
                except Exception as e:
                    print(f"Error creating case relation: {e}")
                    pass

        print(f"Created {case_count} dossier relations")
        print("Graph relations built successfully!")


def get_ingestion_pipeline() -> IngestionPipeline:
    """Factory function to create ingestion pipeline"""
    from src.db.connection import get_db_client
    from src.embeddings.generator import get_embedding_generator
    from src.ingestion.metadata_enricher import get_metadata_enricher

    db_client = get_db_client()
    embedding_gen = get_embedding_generator()
    enricher = get_metadata_enricher()

    return IngestionPipeline(db_client, embedding_gen, enricher)
