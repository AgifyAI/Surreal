"""
SurrealDB connection module using HTTP API
"""
import httpx
import json
from typing import Any, Dict, List, Optional
from base64 import b64encode


class SurrealDBClient:
    """HTTP client for SurrealDB"""

    def __init__(
        self,
        url: str = "http://localhost:8001",
        username: str = "root",
        password: str = "root",
        namespace: str = "Law IA",
        database: str = "mailify"
    ):
        self.url = url.rstrip('/') + '/sql'
        self.namespace = namespace
        self.database = database

        # Create Basic Auth header
        credentials = f"{username}:{password}"
        encoded = b64encode(credentials.encode()).decode()

        self.headers = {
            "Authorization": f"Basic {encoded}",
            "surreal-ns": namespace,
            "surreal-db": database,
            "Accept": "application/json",
            "Content-Type": "text/plain"
        }

        self.client = httpx.Client(timeout=30.0)

    def query(self, sql: str) -> List[Dict[str, Any]]:
        """
        Execute a SurrealQL query

        Args:
            sql: SurrealQL query string

        Returns:
            List of query results
        """
        response = self.client.post(
            self.url,
            headers=self.headers,
            content=sql
        )

        if response.status_code != 200:
            raise Exception(f"Query failed: {response.text}")

        results = response.json()

        # Check for errors in results
        for result in results:
            if result.get("status") == "ERR":
                raise Exception(f"Query error: {result.get('result', 'Unknown error')}")

        return results

    def query_single(self, sql: str) -> Optional[Dict[str, Any]]:
        """Execute a query and return the first result"""
        results = self.query(sql)
        if results and results[0].get("result"):
            return results[0]["result"]
        return None

    def create(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a record in a table

        Args:
            table: Table name
            data: Record data

        Returns:
            Created record
        """
        # Convert data to JSON string
        data_json = json.dumps(data)
        sql = f"CREATE {table} CONTENT {data_json};"

        result = self.query(sql)
        if result and result[0].get("result"):
            return result[0]["result"][0] if isinstance(result[0]["result"], list) else result[0]["result"]

        raise Exception("Failed to create record")

    def select(self, table: str, record_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Select records from a table

        Args:
            table: Table name
            record_id: Optional specific record ID

        Returns:
            List of records
        """
        if record_id:
            sql = f"SELECT * FROM {table}:{record_id};"
        else:
            sql = f"SELECT * FROM {table};"

        result = self.query(sql)
        if result and result[0].get("result") is not None:
            res = result[0]["result"]
            return res if isinstance(res, list) else [res]
        return []

    def relate(self, from_record: str, relation_table: str, to_record: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a relation between two records

        Args:
            from_record: Source record ID (e.g., "email:123")
            relation_table: Relation table name
            to_record: Target record ID
            data: Optional relation data

        Returns:
            Created relation
        """
        if data:
            data_json = json.dumps(data)
            sql = f"RELATE {from_record}->{relation_table}->{to_record} CONTENT {data_json};"
        else:
            sql = f"RELATE {from_record}->{relation_table}->{to_record};"

        result = self.query(sql)
        if result and result[0].get("result"):
            return result[0]["result"][0] if isinstance(result[0]["result"], list) else result[0]["result"]

        raise Exception("Failed to create relation")

    def vector_search(
        self,
        table: str,
        field: str,
        embedding: List[float],
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search

        Args:
            table: Table name
            field: Embedding field name
            embedding: Query embedding vector
            limit: Number of results
            filters: Optional WHERE clause filters

        Returns:
            List of similar records with similarity scores
        """
        # Convert embedding to JSON array
        embedding_json = json.dumps(embedding)

        # Build WHERE clause
        where_clause = ""
        if filters:
            conditions = []
            for key, value in filters.items():
                if isinstance(value, str):
                    conditions.append(f"{key} = '{value}'")
                else:
                    conditions.append(f"{key} = {json.dumps(value)}")
            if conditions:
                where_clause = "WHERE " + " AND ".join(conditions)

        # Build query
        sql = f"""
        SELECT *,
            vector::similarity::cosine({field}, {embedding_json}) AS similarity
        FROM {table}
        {where_clause}
        ORDER BY similarity DESC
        LIMIT {limit};
        """

        result = self.query(sql)
        if result and result[0].get("result") is not None:
            res = result[0]["result"]
            return res if isinstance(res, list) else [res]
        return []

    def close(self):
        """Close the HTTP client"""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def get_db_client() -> SurrealDBClient:
    """Factory function to create a database client with environment variables"""
    import os
    from dotenv import load_dotenv

    load_dotenv()

    return SurrealDBClient(
        url=os.getenv("SURREALDB_URL", "http://localhost:8001"),
        username=os.getenv("SURREALDB_USER", "root"),
        password=os.getenv("SURREALDB_PASSWORD", "root"),
        namespace=os.getenv("SURREALDB_NAMESPACE", "Law IA"),
        database=os.getenv("SURREALDB_DATABASE", "mailify")
    )
