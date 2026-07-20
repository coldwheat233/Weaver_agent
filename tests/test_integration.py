"""集成测试 —— Collector → Storage + Weaver → Architect 流水线"""

import pytest
from uuid import uuid4


class TestCollectorToStorage:
    @pytest.mark.asyncio
    async def test_collector_creates_node(self, fake_llm):
        """Collector 标准化 → IdeaNode 持久化到 SQLite"""
        from src.agents.collector import CollectorAgent
        from src.core.models import SourceType

        agent = CollectorAgent(fake_llm)
        node = await agent.process("需要一个分布式限流系统", SourceType.TEXT)

        assert node is not None
        assert node.id is not None
        assert node.source_type == SourceType.TEXT
        assert node.standardized_content is not None
        assert len(node.intent_tags) > 0


class TestWeaverOutput:
    @pytest.mark.asyncio
    async def test_build_clusters(self, fake_llm, sample_idea):
        """从 Weaver 输出构建 ConceptCluster"""
        from src.agents.weaver import WeaverAgent
        data = {
            "clusters": [{
                "name": "限流方案",
                "description": "基于 Redis 滑动窗口的分布式限流",
                "member_indices": [0],
                "innovation_potential": "medium",
            }],
            "relationships": [],
            "cross_domain_bridges": [],
            "conflicts": [],
        }
        clusters = WeaverAgent.build_clusters_from_result(data, [sample_idea])
        assert len(clusters) == 1
        assert clusters[0].name == "限流方案"
        assert sample_idea.id in clusters[0].member_node_ids


class TestArchitectGeneratesDoc:
    def test_design_document_creation(self, sample_design):
        """DesignDocument 创建与默认值"""
        assert sample_design.title
        assert sample_design.version == 1
        assert not sample_design.critic_approval
        assert sample_design.content_markdown


class TestCriticFeedback:
    @pytest.mark.asyncio
    async def test_critique_returns_feedback(self, fake_llm, sample_design):
        """Critic 返回结构化反馈"""
        from src.agents.critic import CriticAgent
        agent = CriticAgent(fake_llm)
        fb = await agent.critique(sample_design)

        assert fb is not None
        assert hasattr(fb, 'scores')
        assert 0 <= fb.scores.coherence <= 1
        assert 0 <= fb.scores.innovation <= 1
        assert 0 <= fb.scores.feasibility <= 1
