"""核心数据模型测试"""

import pytest
from src.core.models import (
    IdeaNode, Relationship, ConceptCluster, DesignDocument,
    WeaverSession, UserProfile, CriticFeedback, CriticScores,
    SourceType, NodeStatus, RelationshipType, IntentTag,
    ConflictType, DesignType, SessionStatus, EmbeddingStatus,
)


class TestIdeaNode:
    def test_create_default(self):
        node = IdeaNode(source_type=SourceType.TEXT, raw_content="test")
        assert node.source_type == SourceType.TEXT
        assert node.status == NodeStatus.ACTIVE
        assert node.relevance_score == 0.5

    def test_scores_in_range(self):
        """Score 超出范围应被 Pydantic 拒绝"""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            IdeaNode(
                source_type=SourceType.TEXT,
                raw_content="test",
                relevance_score=1.5,
            )

    def test_uuid_auto_generated(self):
        node = IdeaNode(source_type=SourceType.TEXT, raw_content="test")
        assert node.id is not None


class TestRelationship:
    def test_create(self):
        from uuid import uuid4
        rid, sid, tid = uuid4(), uuid4(), uuid4()
        rel = Relationship(
            id=rid,
            source_node_id=sid,
            target_node_id=tid,
            relationship_type=RelationshipType.CAUSAL,
            strength=0.8,
        )
        assert rel.relationship_type == RelationshipType.CAUSAL
        assert rel.strength == 0.8


class TestConceptCluster:
    def test_create(self):
        from uuid import uuid4
        cid, nid = uuid4(), uuid4()
        cluster = ConceptCluster(
            id=cid,
            name="测试簇",
            description="描述",
            member_node_ids=[nid],
            summary="摘要",
        )
        assert len(cluster.member_node_ids) == 1


class TestDesignDocument:
    def test_create(self):
        from uuid import uuid4
        doc = DesignDocument(
            id=uuid4(),
            title="测试",
            type=DesignType.ARCHITECTURE,
            content_markdown="# 测试",
        )
        assert doc.version == 1
        assert not doc.critic_approval


class TestWeaverSession:
    def test_create(self):
        from uuid import uuid4
        session = WeaverSession(
            id=uuid4(),
            north_star="目标",
            divergence_degree=2,
        )
        assert session.status == SessionStatus.COLLECTING


class TestCriticFeedback:
    def test_default(self):
        fb = CriticFeedback()
        assert not fb.approved
        assert fb.iteration == 1
        assert fb.max_iterations == 3
        assert fb.scores.coherence == 0.5
