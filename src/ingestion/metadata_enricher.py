"""
Metadata enrichment for emails
Automatic classification, tagging, and language detection
"""
import re
from typing import Dict, Any, List, Optional
from langdetect import detect


class MetadataEnricher:
    """Enrich email metadata with classification and tags"""

    def __init__(
        self,
        client_domains: Optional[List[str]] = None,
        confrere_domains: Optional[List[str]] = None,
        expert_domains: Optional[List[str]] = None
    ):
        """
        Initialize metadata enricher

        Args:
            client_domains: List of client email domains
            confrere_domains: List of lawyer colleague domains
            expert_domains: List of medical expert domains
        """
        self.client_domains = client_domains or []
        self.confrere_domains = confrere_domains or ['avocat.fr', 'barreau']
        self.expert_domains = expert_domains or ['medecin', 'medical', 'expert']

        # Database of known contacts (can be loaded from file/DB)
        self.known_clients = {}  # {email: client_id}
        self.known_dossiers = {}  # {reference: dossier_id}

    def load_client_database(self, clients: Dict[str, str]):
        """
        Load known clients database

        Args:
            clients: Dict mapping email addresses to client IDs
        """
        self.known_clients = clients

    def load_dossier_database(self, dossiers: Dict[str, str]):
        """
        Load known dossiers database

        Args:
            dossiers: Dict mapping references to dossier IDs
        """
        self.known_dossiers = dossiers

    def _classify_sender(self, sender_email: str, sender_name: str) -> str:
        """
        Classify email sender

        Returns:
            Category: "client", "confrere", "expert_medical", "tribunal", "autre"
        """
        email_lower = sender_email.lower()
        name_lower = sender_name.lower()

        # Check if known client
        if sender_email in self.known_clients:
            return "client"

        # Check domain patterns
        for domain in self.confrere_domains:
            if domain in email_lower:
                return "confrere"

        for domain in self.expert_domains:
            if domain in email_lower or domain in name_lower:
                return "expert_medical"

        # Check for tribunal keywords
        tribunal_keywords = ['tribunal', 'cour', 'justice', 'greffe']
        if any(kw in email_lower or kw in name_lower for kw in tribunal_keywords):
            return "tribunal"

        return "autre"

    def _extract_dossier_id(self, subject: str, body: str) -> Optional[str]:
        """
        Extract dossier/case reference from email

        Common patterns:
        - Dossier n° 2024-001
        - Ref: ABC123
        - RG 24/00123
        """
        text = f"{subject} {body}"

        # Try known references first
        for ref, dossier_id in self.known_dossiers.items():
            if ref in text:
                return dossier_id

        # Pattern matching
        patterns = [
            r'dossier\s*n?°?\s*(\d{4}-\d+)',
            r'ref\s*:?\s*([A-Z0-9]+)',
            r'RG\s*:?\s*(\d{2}/\d+)',
            r'affaire\s*n?°?\s*(\d+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def _extract_client_id(self, sender_email: str) -> Optional[str]:
        """Extract client ID from sender"""
        if sender_email in self.known_clients:
            return self.known_clients[sender_email]
        return None

    def _extract_tags(self, subject: str, body: str) -> List[str]:
        """
        Extract relevant tags from email content

        Uses simple keyword matching (can be enhanced with NLP)
        """
        text = f"{subject} {body}".lower()

        tag_keywords = {
            "urgence": ["urgent", "immédiat", "rapide"],
            "rendez-vous": ["rendez-vous", "rdv", "rencontre", "entrevue"],
            "expertise": ["expertise", "expert", "rapport"],
            "tribunal": ["audience", "tribunal", "cour", "jugement"],
            "délai": ["délai", "échéance", "date limite"],
            "paiement": ["paiement", "facture", "honoraires", "règlement"],
            "contrat": ["contrat", "convention", "accord"],
            "accident": ["accident", "sinistre", "collision"],
            "préjudice": ["préjudice", "dommage", "indemnisation"],
        }

        tags = []
        for tag, keywords in tag_keywords.items():
            if any(kw in text for kw in keywords):
                tags.append(tag)

        return tags

    def _detect_language(self, text: str) -> str:
        """
        Detect language of text

        Args:
            text: Text to analyze

        Returns:
            Language code (fr, en, etc.)
        """
        try:
            return detect(text)
        except:
            return "fr"  # Default to French

    def _detect_priority(self, subject: str, body: str) -> str:
        """
        Detect email priority

        Returns:
            Priority: "high", "normal", "low"
        """
        text = f"{subject} {body}".lower()

        urgent_keywords = ["urgent", "immédiat", "asap", "rapidement"]
        if any(kw in text for kw in urgent_keywords):
            return "high"

        return "normal"

    def enrich(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich email with metadata

        Args:
            email_data: Raw email data

        Returns:
            Enriched email data with metadata
        """
        sender_email = email_data.get("sender_email", "")
        sender_name = email_data.get("sender_name", "")
        subject = email_data.get("subject", "")
        body = email_data.get("body", "")

        # Classify sender
        category = self._classify_sender(sender_email, sender_name)

        # Extract IDs
        client_id = self._extract_client_id(sender_email)
        dossier_id = self._extract_dossier_id(subject, body)

        # Extract tags
        tags = self._extract_tags(subject, body)

        # Detect language
        language = self._detect_language(f"{subject} {body}")

        # Detect priority
        priority = self._detect_priority(subject, body)

        # Add enriched metadata
        email_data.update({
            "category": category,
            "client_id": client_id,
            "dossier_id": dossier_id,
            "tags": tags,
            "language": language,
            "priority": priority
        })

        return email_data

    def enrich_batch(self, emails: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enrich multiple emails

        Args:
            emails: List of raw email data

        Returns:
            List of enriched email data
        """
        return [self.enrich(email) for email in emails]


def get_metadata_enricher() -> MetadataEnricher:
    """Factory function to create metadata enricher"""
    # Could load client/dossier databases from files or database
    enricher = MetadataEnricher()

    # Example: Load from files if they exist
    # enricher.load_client_database(load_clients_from_file())
    # enricher.load_dossier_database(load_dossiers_from_file())

    return enricher
