"""ChromaDB 向量存储 —— chromadb 懒加载"""

from typing import List, Optional
from src.utils.config import get_settings

settings = get_settings()


class VectorStore:
    """ChromaDB 封装（chromadb 首次使用时才加载）"""

    def __init__(self):
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        chroma_dir = str(settings.chroma_dir)
        chroma_dir_path = settings.chroma_dir
        chroma_dir_path.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=chroma_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

        self.idea_collection = self.client.get_or_create_collection(
            name="idea_nodes",
            metadata={"hnsw:space": "cosine"},
        )

        self.cluster_collection = self.client.get_or_create_collection(
            name="cluster_centroids",
            metadata={"hnsw:space": "cosine"},
        )

    def add_idea(self, node_id: str, embedding: List[float],
                 document: str = "", metadata: dict | None = None):
        """添加想法向量"""
        self.idea_collection.add(
            ids=[node_id],
            embeddings=[embedding],
            documents=[document],
            metadatas=[metadata or {}],
        )

    def search_ideas(self, query_embedding: List[float], k: int = 10,
                     filter: dict | None = None) -> List[dict]:
        """语义搜索想法"""
        results = self.idea_collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where=filter,
            include=["documents", "metadatas", "distances"],
        )
        if not results["ids"] or not results["ids"][0]:
            return []

        items = []
        for i, node_id in enumerate(results["ids"][0]):
            items.append({
                "id": node_id,
                "document": results["documents"][0][i] if results["documents"] else "",
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "similarity": 1 - results["distances"][0][i],  # cosine distance → similarity
            })
        return items

    def add_cluster_centroid(self, cluster_id: str, embedding: List[float], metadata: dict | None = None):
        self.cluster_collection.add(
            ids=[cluster_id],
            embeddings=[embedding],
            metadatas=[metadata or {}],
        )

    def delete_idea(self, node_id: str):
        self.idea_collection.delete(ids=[node_id])

    def count(self) -> int:
        return self.idea_collection.count()
