"""ConceptCluster CRUD"""

import json
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from src.core.models import ConceptCluster


class ClusterRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, cluster: ConceptCluster) -> ConceptCluster:
        await self.session.execute(
            text("""
                INSERT INTO concept_clusters (id, name, description, member_node_ids,
                    summary, innovation_score, coherence_score, cross_domain_count, status)
                VALUES (:id, :name, :description, :member_node_ids,
                    :summary, :innovation_score, :coherence_score, :cross_domain_count, :status)
            """),
            {
                "id": str(cluster.id),
                "name": cluster.name,
                "description": cluster.description,
                "member_node_ids": json.dumps([str(i) for i in cluster.member_node_ids]),
                "summary": cluster.summary,
                "innovation_score": cluster.innovation_score,
                "coherence_score": cluster.coherence_score,
                "cross_domain_count": cluster.cross_domain_count,
                "status": cluster.status.value if hasattr(cluster.status, 'value') else cluster.status,
            },
        )

        # 写入 cluster_members 多对多表
        for node_id in cluster.member_node_ids:
            await self.session.execute(
                text("INSERT OR IGNORE INTO cluster_members (cluster_id, node_id) VALUES (:cid, :nid)"),
                {"cid": str(cluster.id), "nid": str(node_id)},
            )

        await self.session.commit()
        return cluster

    async def get(self, cluster_id: UUID) -> Optional[ConceptCluster]:
        result = await self.session.execute(
            text("SELECT * FROM concept_clusters WHERE id = :id"),
            {"id": str(cluster_id)},
        )
        row = result.fetchone()
        return self._row_to_cluster(row) if row else None

    async def list_active(self, limit: int = 50) -> List[ConceptCluster]:
        result = await self.session.execute(
            text("SELECT * FROM concept_clusters WHERE status = 'active' ORDER BY created_at DESC LIMIT :limit"),
            {"limit": limit},
        )
        return [self._row_to_cluster(row) for row in result.fetchall()]

    @staticmethod
    def _row_to_cluster(row) -> ConceptCluster:
        if row is None:
            return None
        r = dict(row._mapping)
        return ConceptCluster(
            id=UUID(r["id"]),
            name=r.get("name", ""),
            description=r.get("description", ""),
            member_node_ids=[UUID(i) for i in json.loads(r.get("member_node_ids", "[]"))],
            summary=r.get("summary", ""),
            innovation_score=r.get("innovation_score", 0.5),
            coherence_score=r.get("coherence_score", 0.5),
            cross_domain_count=r.get("cross_domain_count", 0),
            status=r.get("status", "active"),
        )
