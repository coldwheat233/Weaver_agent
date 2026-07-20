"""Collector Agent 单元测试"""

import pytest
from src.agents.collector import CollectorAgent


class TestCollectorAgent:
    def test_create(self, fake_llm):
        agent = CollectorAgent(fake_llm)
        assert agent is not None
        assert agent.DORMANT_THRESHOLD == 0.3

    @pytest.mark.asyncio
    async def test_process_text(self, fake_llm):
        agent = CollectorAgent(fake_llm)
        from src.core.models import SourceType

        node = await agent.process(
            content="这是一个测试想法",
            source_type=SourceType.TEXT,
        )

        assert node is not None
        assert node.source_type == SourceType.TEXT
        assert node.raw_content == "这是一个测试想法"
        # Fake LLM 返回了 JSON 数据
        assert node.standardized_content is not None

    def test_parse_tags(self):
        tags = CollectorAgent._parse_tags(["observation", "goal"])
        assert len(tags) == 2
        from src.core.models import IntentTag
        assert tags[0] == IntentTag.OBSERVATION


class TestCriticAgent:
    def test_create(self, fake_llm):
        from src.agents.critic import CriticAgent
        agent = CriticAgent(fake_llm)
        assert agent is not None

    @pytest.mark.asyncio
    async def test_critique(self, fake_llm, sample_design):
        from src.agents.critic import CriticAgent
        agent = CriticAgent(fake_llm)
        feedback = await agent.critique(sample_design)

        assert feedback is not None
        assert feedback.scores.coherence >= 0
        assert feedback.scores.coherence <= 1
