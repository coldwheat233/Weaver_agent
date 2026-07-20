"""DesignDocument CRUD"""

import json
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from src.core.models import DesignDocument


class DesignRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, doc: DesignDocument) -> DesignDocument:
        await self.session.execute(
            text("""
                INSERT INTO design_documents (id, title, type, source_cluster_ids,
                    content_markdown, innovation_score, coherence_score, feasibility_score,
                    critic_approval, critic_feedback, version, parent_design_id)
                VALUES (:id, :title, :type, :source_cluster_ids,
                    :content_markdown, :innovation_score, :coherence_score, :feasibility_score,
                    :critic_approval, :critic_feedback, :version, :parent_design_id)
            """),
            {
                "id": str(doc.id),
                "title": doc.title,
                "type": doc.type.value if hasattr(doc.type, 'value') else doc.type,
                "source_cluster_ids": json.dumps([str(i) for i in doc.source_cluster_ids]),
                "content_markdown": doc.content_markdown,
                "innovation_score": doc.innovation_score,
                "coherence_score": doc.coherence_score,
                "feasibility_score": doc.feasibility_score,
                "critic_approval": int(doc.critic_approval),
                "critic_feedback": doc.critic_feedback,
                "version": doc.version,
                "parent_design_id": str(doc.parent_design_id) if doc.parent_design_id else None,
            },
        )
        await self.session.commit()
        return doc

    async def get(self, design_id: UUID) -> Optional[DesignDocument]:
        result = await self.session.execute(
            text("SELECT * FROM design_documents WHERE id = :id"),
            {"id": str(design_id)},
        )
        row = result.fetchone()
        return self._row_to_doc(row) if row else None

    async def update(self, doc: DesignDocument):
        await self.session.execute(
            text("""
                UPDATE design_documents SET title=:title, content_markdown=:content_markdown,
                    innovation_score=:innovation_score, coherence_score=:coherence_score,
                    feasibility_score=:feasibility_score, critic_approval=:critic_approval,
                    critic_feedback=:critic_feedback, version=:version,
                    updated_at=datetime('now')
                WHERE id=:id
            """),
            {
                "id": str(doc.id),
                "title": doc.title,
                "content_markdown": doc.content_markdown,
                "innovation_score": doc.innovation_score,
                "coherence_score": doc.coherence_score,
                "feasibility_score": doc.feasibility_score,
                "critic_approval": int(doc.critic_approval),
                "critic_feedback": doc.critic_feedback,
                "version": doc.version,
            },
        )
        await self.session.commit()

    @staticmethod
    def _row_to_doc(row) -> DesignDocument:
        if row is None:
            return None
        r = dict(row._mapping)
        return DesignDocument(
            id=UUID(r["id"]),
            title=r.get("title", ""),
            type=r.get("type", "architecture"),
            source_cluster_ids=[UUID(i) for i in json.loads(r.get("source_cluster_ids", "[]"))],
            content_markdown=r.get("content_markdown", ""),
            innovation_score=r.get("innovation_score", 0.5),
            coherence_score=r.get("coherence_score", 0.5),
            feasibility_score=r.get("feasibility_score", 0.5),
            critic_approval=bool(r.get("critic_approval", 0)),
            critic_feedback=r.get("critic_feedback"),
            version=r.get("version", 1),
            parent_design_id=UUID(r["parent_design_id"]) if r.get("parent_design_id") else None,
        )
