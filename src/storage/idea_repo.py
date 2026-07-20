"""IdeaNode CRUD"""

import json
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from src.core.models import IdeaNode, NodeStatus


class IdeaRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, node: IdeaNode) -> IdeaNode:
        await self.session.execute(
            text("""
                INSERT INTO idea_nodes (id, source_type, raw_content, raw_asset_path,
                    standardized_content, embedding_status, intent_tags, context_tags,
                    relevance_score, completeness_score, actionability_score, status,
                    merged_into, north_star_relevance, session_id)
                VALUES (:id, :source_type, :raw_content, :raw_asset_path,
                    :standardized_content, :embedding_status, :intent_tags, :context_tags,
                    :relevance_score, :completeness_score, :actionability_score, :status,
                    :merged_into, :north_star_relevance, :session_id)
            """),
            {
                "id": str(node.id),
                "source_type": node.source_type.value,
                "raw_content": node.raw_content,
                "raw_asset_path": node.raw_asset_path,
                "standardized_content": node.standardized_content,
                "embedding_status": node.embedding_status.value if hasattr(node.embedding_status, 'value') else "pending",
                "intent_tags": json.dumps([t.value if hasattr(t, 'value') else t for t in node.intent_tags]),
                "context_tags": json.dumps(node.context_tags),
                "relevance_score": node.relevance_score,
                "completeness_score": node.completeness_score,
                "actionability_score": node.actionability_score,
                "status": node.status.value,
                "merged_into": str(node.merged_into) if node.merged_into else None,
                "north_star_relevance": node.north_star_relevance,
                "session_id": node.session_id,
            },
        )
        await self.session.commit()
        return node

    async def get(self, node_id: UUID) -> Optional[IdeaNode]:
        result = await self.session.execute(
            text("SELECT * FROM idea_nodes WHERE id = :id"),
            {"id": str(node_id)},
        )
        row = result.fetchone()
        return self._row_to_node(row) if row else None

    async def get_by_ids(self, ids: List[UUID]) -> List[IdeaNode]:
        if not ids:
            return []
        # SQLAlchemy 2.0 不允许列表参数, 用命名绑定
        params = {f"id{i}": str(uid) for i, uid in enumerate(ids)}
        placeholders = ", ".join(f":id{i}" for i in range(len(ids)))
        result = await self.session.execute(
            text(f"SELECT * FROM idea_nodes WHERE id IN ({placeholders})"),
            params,
        )
        return [self._row_to_node(row) for row in result.fetchall()]

    async def list_active(self, limit: int = 100, offset: int = 0) -> List[IdeaNode]:
        result = await self.session.execute(
            text("SELECT * FROM idea_nodes WHERE status = 'active' ORDER BY created_at DESC LIMIT :limit OFFSET :offset"),
            {"limit": limit, "offset": offset},
        )
        return [self._row_to_node(row) for row in result.fetchall()]

    async def list_by_session(self, session_id: str) -> List[IdeaNode]:
        result = await self.session.execute(
            text("SELECT * FROM idea_nodes WHERE session_id = :sid ORDER BY created_at"),
            {"sid": session_id},
        )
        return [self._row_to_node(row) for row in result.fetchall()]

    async def search_by_context_tags(self, tags: List[str], limit: int = 20) -> List[IdeaNode]:
        if not tags:
            return []
        conditions = " OR ".join(["context_tags LIKE :t" + str(i) for i in range(len(tags))])
        params = {f"t{i}": f"%{tag}%" for i, tag in enumerate(tags)}
        params["limit"] = limit
        result = await self.session.execute(
            text(f"SELECT * FROM idea_nodes WHERE ({conditions}) AND status = 'active' ORDER BY created_at DESC LIMIT :limit"),
            params,
        )
        return [self._row_to_node(row) for row in result.fetchall()]

    async def update_embedding_status(self, node_id: UUID, status: str):
        await self.session.execute(
            text("UPDATE idea_nodes SET embedding_status = :status, updated_at = datetime('now') WHERE id = :id"),
            {"id": str(node_id), "status": status},
        )
        await self.session.commit()

    async def update_status(self, node_id: UUID, status: NodeStatus):
        await self.session.execute(
            text("UPDATE idea_nodes SET status = :status, updated_at = datetime('now') WHERE id = :id"),
            {"id": str(node_id), "status": status.value},
        )
        await self.session.commit()

    async def get_pending_embeddings(self, limit: int = 50) -> List[IdeaNode]:
        result = await self.session.execute(
            text("SELECT * FROM idea_nodes WHERE embedding_status IN ('pending','failed') AND standardized_content IS NOT NULL LIMIT :limit"),
            {"limit": limit},
        )
        return [self._row_to_node(row) for row in result.fetchall()]

    async def get_relationships(self, node_id) -> list:
        """获取某个节点的所有关系（作为 source 或 target）"""
        from uuid import UUID as _UUID
        nid = str(node_id) if not isinstance(node_id, str) else node_id
        result = await self.session.execute(
            text("SELECT * FROM relationships WHERE source_node_id = :nid OR target_node_id = :nid2"),
            {"nid": nid, "nid2": nid},
        )
        rows = result.fetchall()
        from src.core.models import Relationship
        rels = []
        for row in rows:
            r = dict(row._mapping)
            rels.append(Relationship(
                id=_UUID(r["id"]),
                source_node_id=_UUID(r["source_node_id"]),
                target_node_id=_UUID(r["target_node_id"]),
                relationship_type=r["relationship_type"],
                strength=r.get("strength", 0.5),
                explanation=r.get("explanation"),
                discovery_method=r.get("discovery_method", "llm_inferred"),
            ))
        return rels

    @staticmethod
    def _row_to_node(row) -> IdeaNode:
        if row is None:
            return None
        r = dict(row._mapping)
        return IdeaNode(
            id=UUID(r["id"]),
            source_type=r["source_type"],
            raw_content=r.get("raw_content", ""),
            raw_asset_path=r.get("raw_asset_path"),
            standardized_content=r.get("standardized_content"),
            embedding_status=r.get("embedding_status", "pending"),
            intent_tags=json.loads(r.get("intent_tags", "[]")),
            context_tags=json.loads(r.get("context_tags", "[]")),
            relevance_score=r.get("relevance_score", 0.5),
            completeness_score=r.get("completeness_score", 0.5),
            actionability_score=r.get("actionability_score", 0.5),
            status=r.get("status", "active"),
            merged_into=UUID(r["merged_into"]) if r.get("merged_into") else None,
            north_star_relevance=r.get("north_star_relevance", 0.5),
            session_id=r.get("session_id"),
        )
