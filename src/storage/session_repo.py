"""WeaverSession CRUD"""

import json
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from src.core.models import WeaverSession, SessionStatus


class SessionRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, s: WeaverSession) -> WeaverSession:
        await self.session.execute(
            text("""
                INSERT INTO weaver_sessions (id, north_star, divergence_degree,
                    status, input_idea_ids, output_design_id, errors)
                VALUES (:id, :north_star, :divergence_degree,
                    :status, :input_idea_ids, :output_design_id, :errors)
            """),
            {
                "id": str(s.id),
                "north_star": s.north_star,
                "divergence_degree": s.divergence_degree,
                "status": s.status.value if hasattr(s.status, 'value') else s.status,
                "input_idea_ids": json.dumps([str(i) for i in s.input_idea_ids]),
                "output_design_id": str(s.output_design_id) if s.output_design_id else None,
                "errors": json.dumps(s.errors),
            },
        )
        await self.session.commit()
        return s

    async def get(self, session_id: UUID) -> Optional[WeaverSession]:
        result = await self.session.execute(
            text("SELECT * FROM weaver_sessions WHERE id = :id"),
            {"id": str(session_id)},
        )
        row = result.fetchone()
        return self._row_to_session(row) if row else None

    async def update_status(self, session_id: str, status: str):
        await self.session.execute(
            text("UPDATE weaver_sessions SET status = :status WHERE id = :id"),
            {"id": session_id, "status": status},
        )
        await self.session.commit()

    async def mark_complete(self, session_id: str, design_id: str):
        await self.session.execute(
            text("""
                UPDATE weaver_sessions
                SET status = 'complete', output_design_id = :did, completed_at = datetime('now')
                WHERE id = :id
            """),
            {"id": session_id, "did": design_id},
        )
        await self.session.commit()

    async def mark_failed(self, session_id: str, error: str):
        await self.session.execute(
            text("""
                UPDATE weaver_sessions
                SET status = 'failed', errors = json_insert(errors, '$[#]', :error)
                WHERE id = :id
            """),
            {"id": session_id, "error": error},
        )
        await self.session.commit()

    async def add_idea(self, session_id: str, idea_id: UUID):
        s = await self.get(UUID(session_id))
        if s:
            ids = [str(i) for i in s.input_idea_ids] + [str(idea_id)]
            await self.session.execute(
                text("UPDATE weaver_sessions SET input_idea_ids = :ids WHERE id = :id"),
                {"id": session_id, "ids": json.dumps(ids)},
            )
            await self.session.commit()

    @staticmethod
    def _row_to_session(row) -> Optional[WeaverSession]:
        if row is None:
            return None
        r = dict(row._mapping)
        return WeaverSession(
            id=UUID(r["id"]),
            north_star=r.get("north_star", ""),
            divergence_degree=r.get("divergence_degree", 2),
            status=r.get("status", "collecting"),
            input_idea_ids=[UUID(i) for i in json.loads(r.get("input_idea_ids", "[]"))],
            output_design_id=UUID(r["output_design_id"]) if r.get("output_design_id") else None,
            errors=json.loads(r.get("errors", "[]")),
            completed_at=r.get("completed_at"),
        )
