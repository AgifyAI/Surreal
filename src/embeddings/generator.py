"""
Embedding generation module
Supports OpenAI and local models
"""
import os
from typing import List, Union
from openai import OpenAI


class EmbeddingGenerator:
    """Generate embeddings for text using OpenAI or local models"""

    def __init__(
        self,
        provider: str = "openai",
        model: str = "text-embedding-3-large",
        dimension: int = 1536
    ):
        """
        Initialize embedding generator

        Args:
            provider: "openai" or "local"
            model: Model name
            dimension: Embedding dimension
        """
        self.provider = provider
        self.model = model
        self.dimension = dimension

        if provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment")
            self.client = OpenAI(api_key=api_key)
        elif provider == "local":
            # Initialize local model (sentence-transformers)
            from sentence_transformers import SentenceTransformer
            self.model_instance = SentenceTransformer(model)
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def generate(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """
        Generate embeddings for text

        Args:
            text: Single text or list of texts

        Returns:
            Single embedding or list of embeddings
        """
        if isinstance(text, str):
            return self._generate_single(text)
        else:
            return self._generate_batch(text)

    def _generate_single(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        if self.provider == "openai":
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
                dimensions=self.dimension
            )
            return response.data[0].embedding

        elif self.provider == "local":
            embedding = self.model_instance.encode(text)
            return embedding.tolist()

    def _generate_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        if self.provider == "openai":
            response = self.client.embeddings.create(
                model=self.model,
                input=texts,
                dimensions=self.dimension
            )
            return [item.embedding for item in response.data]

        elif self.provider == "local":
            embeddings = self.model_instance.encode(texts)
            return [emb.tolist() for emb in embeddings]

    def generate_for_email(self, subject: str, body: str) -> List[float]:
        """
        Generate embedding for an email

        Args:
            subject: Email subject
            body: Email body

        Returns:
            Embedding vector
        """
        # Combine subject and body with emphasis on subject
        text = f"Sujet: {subject}\n\nCorps: {body}"
        return self.generate(text)


def get_embedding_generator() -> EmbeddingGenerator:
    """Factory function to create embedding generator from environment"""
    from dotenv import load_dotenv
    load_dotenv()

    provider = os.getenv("EMBEDDING_PROVIDER", "openai")
    model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
    dimension = int(os.getenv("EMBEDDING_DIMENSION", "1536"))

    return EmbeddingGenerator(
        provider=provider,
        model=model,
        dimension=dimension
    )
