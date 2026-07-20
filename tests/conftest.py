"""Pytest 固件与全局 Mock 配置"""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def fake_llm():
    """返回 FakeLLMService 实例（充足响应供全流水线）"""
    from src.core.llm_service import FakeLLMService
    return FakeLLMService(canned_responses=[
        # collector
        '{"standardized_content":"test idea","intent_tags":["observation"],"context_tags":["test"],"relevance_score":0.8,"completeness_score":0.7,"actionability_score":0.6}',
        # weaver
        '{"clusters":[{"name":"test cluster","description":"test","member_indices":[0]}],"relationships":[],"cross_domain_bridges":[],"conflicts":[]}',
        # architect
        "# Test Design\n\n```mermaid\ngraph TD\nA-->B\n```",
        # critic
        '{"approved":true,"scores":{"coherence":0.8,"innovation":0.7,"feasibility":0.75},"blocking_issues":[],"suggestions":[],"strengths":["test strength"]}',
        # inquisitor
        '{"questions":[{"priority":1,"question":"缓存策略是什么？","context":"未指定缓存类型","category":"detail"}],"completeness_estimate":0.5,"ready_to_architect":false}',
        # monitor
        '{"relevant":true,"standardized_content":"外部洞见","relevance_reason":"相关","intent_tags":["observation"],"context_tags":["test"]}',
        # fallback
        "{}",
        "{}",
        "{}",
        "{}",
        "{}",
    ])


@pytest.fixture
def sample_idea():
    """返回一个示例 IdeaNode"""
    from src.core.models import IdeaNode, SourceType
    return IdeaNode(
        source_type=SourceType.TEXT,
        raw_content="测试用想法",
        standardized_content="这是一个用于测试的标准化想法。",
        intent_tags=["observation"],
        context_tags=["testing"],
        relevance_score=0.8,
        completeness_score=0.7,
        actionability_score=0.6,
    )


@pytest.fixture
def sample_cluster(sample_idea):
    """返回一个示例 ConceptCluster"""
    from src.core.models import ConceptCluster
    from uuid import uuid4
    return ConceptCluster(
        id=uuid4(),
        name="测试簇",
        description="用于测试的概念簇",
        member_node_ids=[sample_idea.id],
        summary="测试摘要",
        cross_domain_count=1,
    )


@pytest.fixture
def sample_design():
    """返回一个示例 DesignDocument"""
    from src.core.models import DesignDocument, DesignType
    from uuid import uuid4
    return DesignDocument(
        id=uuid4(),
        title="测试设计文档",
        type=DesignType.ARCHITECTURE,
        content_markdown="# 测试设计\n\n## 架构概览\n\n```mermaid\ngraph TD\nA-->B\n```\n\n## 组件详规\n\n组件A: 测试组件",
        innovation_score=0.72,
        coherence_score=0.85,
        feasibility_score=0.68,
    )


@pytest.fixture
def sample_session():
    """返回一个示例 WeaverSession"""
    from src.core.models import WeaverSession
    from uuid import uuid4
    return WeaverSession(
        id=uuid4(),
        north_star="测试北极星目标",
        divergence_degree=2,
    )
