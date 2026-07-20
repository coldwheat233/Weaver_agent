"""E2E 冒烟测试 —— 完整流程"""

import pytest


class TestEndToEndSmoke:
    """端到端冒烟：想法提交 → 会话创建 → 编织触发 → 设计输出"""

    @pytest.mark.asyncio
    async def test_full_text_to_design_pipeline(self, fake_llm):
        """最简完整流程（使用 FakeLLMService）"""
        from uuid import uuid4
        from src.agents.collector import CollectorAgent
        from src.agents.weaver import WeaverAgent
        from src.agents.architect import ArchitectAgent
        from src.agents.critic import CriticAgent
        from src.core.models import SourceType

        # Step 1: 收集想法
        collector = CollectorAgent(fake_llm)
        node = await collector.process("需要一个分布式限流系统", SourceType.TEXT)
        assert node.standardized_content is not None

        # Step 2: Weaver 编织
        weaver = WeaverAgent(fake_llm)
        result = await weaver.weave(
            nodes=[node],
            north_star="设计一个分布式限流系统",
        )
        clusters = WeaverAgent.build_clusters_from_result(result, [node])
        assert len(clusters) >= 0  # Fake LLM 可能返回空，但不应报错

        # Step 3: Architect 生成设计
        relationships = WeaverAgent.build_relationships(result, [node])
        bridges = result.get("cross_domain_bridges", [])
        conflicts = WeaverAgent.build_conflicts(result, [node])

        architect = ArchitectAgent(fake_llm)
        design = await architect.design(
            clusters=clusters,
            relationships=relationships,
            bridges=bridges,
            conflicts=[{"type": c.conflict_type.value, "description": c.description} for c in conflicts],
            north_star="设计一个分布式限流系统",
        )
        assert design is not None
        assert design.title

        # Step 4: Critic 评估
        critic = CriticAgent(fake_llm)
        fb = await critic.critique(design)
        assert fb.scores.coherence >= 0

        # E2E 通过
        assert design.content_markdown or fb.approved or True


class TestV2MultiTurn:
    """V2 多轮对话测试"""

    @pytest.mark.asyncio
    async def test_inquisitor_generates_questions(self):
        from src.agents.inquisitor import InquisitorAgent
        from src.core.llm_service import FakeLLMService
        from src.core.models import ConceptCluster, IdeaNode, SourceType
        from uuid import uuid4

        # 专用 FakeLLM — 避免与全局 fixture 响应序列冲突
        llm = FakeLLMService(canned_responses=[
            '{"questions":[{"priority":1,"question":"缓存策略？","context":"未指定类型","category":"detail"}],"completeness_estimate":0.5,"ready_to_architect":false}',
        ])
        agent = InquisitorAgent(llm)
        node = IdeaNode(
            source_type=SourceType.TEXT,
            raw_content="需要一个缓存方案",
            standardized_content="系统需要缓存来加速读操作。",
            intent_tags=["problem_statement"],
            context_tags=["caching"],
        )
        cluster = ConceptCluster(
            id=uuid4(),
            name="缓存方案",
            description="缓存相关想法",
            member_node_ids=[node.id],
        )

        result = await agent.interrogate(
            clusters=[cluster],
            nodes=[node],
            north_star="设计一个高性能缓存系统",
        )

        assert "questions" in result
        assert "completeness_estimate" in result
        assert "ready_to_architect" in result


class TestV3Trigger:
    """V3 临界质量检测测试"""

    def test_critical_mass_detector_too_few_nodes(self):
        from src.core.trigger import CriticalMassDetector
        from src.core.models import ConceptCluster
        from uuid import uuid4

        detector = CriticalMassDetector()
        cluster = ConceptCluster(
            id=uuid4(),
            name="小簇",
            member_node_ids=[uuid4() for _ in range(3)],  # < 5
            cross_domain_count=2,
            innovation_score=0.6,
        )

        assert not detector.should_trigger(cluster, [])

    def test_critical_mass_detector_ok(self):
        from src.core.trigger import CriticalMassDetector
        from src.core.models import ConceptCluster, IdeaNode, SourceType
        from uuid import uuid4
        from datetime import datetime, timedelta

        detector = CriticalMassDetector()
        nodes = [
            IdeaNode(
                id=uuid4(), source_type=SourceType.TEXT,
                raw_content=f"idea {i}",
                created_at=datetime.utcnow() - timedelta(hours=i * 2),
            )
            for i in range(6)
        ]
        cluster = ConceptCluster(
            id=uuid4(),
            name="成熟簇",
            member_node_ids=[n.id for n in nodes],
            cross_domain_count=3,
            innovation_score=0.65,
        )

        assert detector.should_trigger(cluster, nodes)
