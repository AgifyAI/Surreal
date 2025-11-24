"""
Email extraction from IMAP servers (Gmail, Outlook, etc.)
"""
import imaplib
import email
from email.header import decode_header
from typing import List, Dict, Any, Optional
from datetime import datetime
import re


class EmailExtractor:
    """Extract emails from IMAP server"""

    def __init__(self, server: str, email_address: str, password: str):
        """
        Initialize IMAP connection

        Args:
            server: IMAP server address (e.g., imap.gmail.com)
            email_address: Email address
            password: App password or regular password
        """
        self.server = server
        self.email_address = email_address
        self.password = password
        self.imap = None

    def connect(self):
        """Connect to IMAP server"""
        self.imap = imaplib.IMAP4_SSL(self.server)
        self.imap.login(self.email_address, self.password)
        print(f"Connected to {self.server}")

    def disconnect(self):
        """Disconnect from IMAP server"""
        if self.imap:
            self.imap.close()
            self.imap.logout()

    def _decode_header(self, header: str) -> str:
        """Decode email header"""
        if not header:
            return ""

        decoded = decode_header(header)
        result = []

        for text, encoding in decoded:
            if isinstance(text, bytes):
                try:
                    result.append(text.decode(encoding or 'utf-8'))
                except:
                    result.append(text.decode('utf-8', errors='ignore'))
            else:
                result.append(text)

        return ' '.join(result)

    def _extract_body(self, msg: email.message.Message) -> str:
        """Extract email body (text/plain or text/html)"""
        body = ""

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                disposition = str(part.get("Content-Disposition", ""))

                # Skip attachments
                if "attachment" in disposition:
                    continue

                if content_type == "text/plain":
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            body += payload.decode('utf-8', errors='ignore')
                    except:
                        pass
                elif content_type == "text/html" and not body:
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            html = payload.decode('utf-8', errors='ignore')
                            # Simple HTML to text conversion
                            body = re.sub(r'<[^>]+>', '', html)
                    except:
                        pass
        else:
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode('utf-8', errors='ignore')
            except:
                pass

        return body.strip()

    def _parse_email(self, msg: email.message.Message) -> Dict[str, Any]:
        """Parse email message into structured data"""
        # Extract headers
        subject = self._decode_header(msg.get("Subject", ""))
        from_header = self._decode_header(msg.get("From", ""))
        to_header = self._decode_header(msg.get("To", ""))
        cc_header = self._decode_header(msg.get("Cc", ""))
        date_header = msg.get("Date", "")
        message_id = msg.get("Message-ID", "")
        in_reply_to = msg.get("In-Reply-To", "")
        references = msg.get("References", "")

        # Parse sender
        sender_match = re.search(r'<(.+?)>', from_header)
        if sender_match:
            sender_email = sender_match.group(1)
            sender_name = from_header.split('<')[0].strip().strip('"')
        else:
            sender_email = from_header
            sender_name = from_header

        # Parse recipients
        recipients = []
        if to_header:
            recipients = [addr.strip() for addr in to_header.split(',')]

        # Parse CC
        cc = []
        if cc_header:
            cc = [addr.strip() for addr in cc_header.split(',')]

        # Parse date
        email_date = None
        try:
            from email.utils import parsedate_to_datetime
            email_date = parsedate_to_datetime(date_header)
        except:
            email_date = datetime.now()

        # Extract body
        body = self._extract_body(msg)

        # Generate thread_id from references or message-id
        thread_id = ""
        if references:
            # Use first message-id in references as thread_id
            ref_match = re.search(r'<(.+?)>', references)
            if ref_match:
                thread_id = ref_match.group(1)
        if not thread_id and message_id:
            thread_id = message_id

        # Check for attachments
        has_attachments = False
        if msg.is_multipart():
            for part in msg.walk():
                if part.get("Content-Disposition", "").startswith("attachment"):
                    has_attachments = True
                    break

        return {
            "subject": subject,
            "body": body,
            "sender_email": sender_email,
            "sender_name": sender_name,
            "recipients": recipients,
            "cc": cc,
            "date": email_date.isoformat(),
            "thread_id": thread_id,
            "message_id": message_id,
            "in_reply_to": in_reply_to or None,
            "has_attachments": has_attachments,
            "language": "fr"  # Default, will be detected later
        }

    def fetch_emails(
        self,
        folder: str = "INBOX",
        limit: Optional[int] = None,
        search_criteria: str = "ALL"
    ) -> List[Dict[str, Any]]:
        """
        Fetch emails from a folder

        Args:
            folder: Email folder (INBOX, Sent, etc.)
            limit: Maximum number of emails to fetch
            search_criteria: IMAP search criteria (ALL, UNSEEN, etc.)

        Returns:
            List of parsed email dictionaries
        """
        if not self.imap:
            self.connect()

        # Select folder
        self.imap.select(folder)

        # Search for emails
        status, messages = self.imap.search(None, search_criteria)

        if status != "OK":
            print(f"Failed to search emails: {status}")
            return []

        email_ids = messages[0].split()

        # Apply limit
        if limit:
            email_ids = email_ids[-limit:]  # Get most recent emails

        emails = []

        for email_id in email_ids:
            try:
                # Fetch email
                status, msg_data = self.imap.fetch(email_id, "(RFC822)")

                if status != "OK":
                    continue

                # Parse email
                msg = email.message_from_bytes(msg_data[0][1])
                parsed_email = self._parse_email(msg)
                emails.append(parsed_email)

            except Exception as e:
                print(f"Error parsing email {email_id}: {e}")
                continue

        print(f"Fetched {len(emails)} emails from {folder}")
        return emails

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


def get_email_extractor() -> EmailExtractor:
    """Factory function to create email extractor from environment"""
    import os
    from dotenv import load_dotenv

    load_dotenv()

    server = os.getenv("EMAIL_IMAP_SERVER", "imap.gmail.com")
    email_address = os.getenv("EMAIL_ADDRESS")
    password = os.getenv("EMAIL_PASSWORD")

    if not email_address or not password:
        raise ValueError("EMAIL_ADDRESS and EMAIL_PASSWORD must be set in environment")

    return EmailExtractor(server, email_address, password)
