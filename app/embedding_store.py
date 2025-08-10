import faiss
import numpy as np
import tiktoken

from config import openai_client


class EmbeddingStore:
    def __init__(self, dim: int = 1536):
        self.index = faiss.IndexFlatL2(dim)  # L2 = Euclidean distance
        self.id_map = {}  # Maps FAISS index ID -> (chunk_text, document_id, chunk_index)

    def _truncate_text(self, text: str, max_tokens: int = 8000) -> str:
        encoding = tiktoken.encoding_for_model("text-embedding-3-small")
        tokens = encoding.encode(text)
        truncated = tokens[:max_tokens]
        return encoding.decode(truncated)

    def embed_text(self, text: str) -> list[float]:
        safe_text = self._truncate_text(text)
        response = openai_client.embeddings.create(input=safe_text, model="text-embedding-3-small")
        return response.data[0].embedding

    def add_chunk(self, chunk_text: str, document_id: int, chunk_index: int, embedding: list[float] = None,
                  add_embedding_direct: bool = False):
        if not add_embedding_direct or embedding is None:
            embedding = self.embed_text(chunk_text)

        vec = np.array([embedding], dtype=np.float32)
        internal_id = len(self.id_map)
        self.index.add(vec)
        self.id_map[internal_id] = (chunk_text, document_id, chunk_index)

    def search(self, query: str, top_k: int = 3) -> list[str]:
        query_vec = np.array([self.embed_text(query)], dtype=np.float32)
        distances, indices = self.index.search(query_vec, top_k)

        results = []
        for idx in indices[0]:
            if idx in self.id_map:
                chunk_text, _, _ = self.id_map[idx]
                results.append(chunk_text)
        return results
