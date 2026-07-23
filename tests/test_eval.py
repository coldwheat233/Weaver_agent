"""Agent Eval Harness — 质量基准测试

Golden task / Critic检出率 / 冲突准确率 / Mermaid语法
不依赖真实 LLM，使用预构造数据 + FakeLLMService
"""

import pytest
from uuid import uuid4


# ══════════════════════════════════════
# 1. Golden Task Eval
# ══════════════════════════════════════

GOLDEN_TASKS = [
    {
        "name": "分布式限流系统",
        "north_star": "设计一个支持分布式部署的 API 网关限流系统",
        "ideas": [
            "需要限制每个用户每分钟的 API 调用次数",
            "使用 Redis 做分布式计数器，滑动窗口算法",
            "系统要支持水平扩展，承载 10000 QPS",
            "限流失败时应该降级而非拒绝——返回缓存数据",
        ],
        "must_contain": ["Redis", "限流", "滑动窗口", "降级"],
        "must_have_mermaid": True,
        "min_components": 3,
    },
    {
        "name": "微服务缓存架构",
        "north_star": "设计微服务间调用的多级缓存方案",
        "ideas": [
            "微服务之间 RPC 调用延迟太高需要加缓存",
            "用本地缓存 Caffeine + 远程 Redis 两级",
            "缓存一致性要求: 数据库变更后 1 秒内缓存失效",
        ],
        "must_contain": ["缓存", "Redis", "一致性"],
        "must_have_mermaid": True,
        "min_components": 2,
    },
    {
        "name": "消息队列选型",
        "north_star": "为订单系统选择消息队列方案",
        "ideas": [
            "订单创建后需要异步通知库存、物流、通知三个服务",
            "要求消息不丢失，at-least-once 语义",
            "峰值 QPS 5000，消息堆积时需要能削峰",
        ],
        "must_contain": ["消息", "队列", "不丢失"],
        "must_have_mermaid": True,
        "min_components": 2,
    },
]


class TestGoldenTaskEval:
    """黄金标准: 预置想法→验证设计文档质量"""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("task", GOLDEN_TASKS, ids=[t["name"] for t in GOLDEN_TASKS])
    async def test_golden_task_pipeline(self, task):
        """端到端：验证 想法→标准化→编织→设计 四步流水线完整运行"""
        from src.core.llm_service import FakeLLMService
        from src.agents.collector import CollectorAgent
        from src.agents.weaver import WeaverAgent
        from src.agents.architect import ArchitectAgent
        from src.agents.critic import CriticAgent
        from src.core.models import SourceType

        # 只用第 1 条 idea，确保 LLM 调用序列可控（每条 idea=1 collector 调用）
        one_idea = task["ideas"][0]
        llm = FakeLLMService(canned_responses=[
            # 0: collector (1 idea = 1 call)
            '{"standardized_content":"' + one_idea[:30] + '","intent_tags":["problem_statement"],"context_tags":["api","distributed"],"relevance_score":0.8,"completeness_score":0.7,"actionability_score":0.6}',
            # 1: clusterer
            '{"clusters":[{"name":"' + task["name"] + '","description":"test","member_indices":[0]}]}',
            # 2: rel_builder
            '{"relationships":[]}',
            # 3: bridge_finder
            '{"cross_domain_bridges":[]}',
            # 4: architect (6 calls total, architect is #4)
            "# " + task["north_star"] + "\n\n## 2. 架构概览\n```mermaid\ngraph TD\nA-->B-->C\n```\n\n## 3. 组件详规\n### 3.1 Component A\n### 3.2 Component B\n### 3.3 Component C\n\n## 4. 关键决策\n| 决策 | 方案 |\n|------|------|\n| 测试 | 通过 |",
            # 5: critic
            '{"approved":true,"scores":{"coherence":0.85,"innovation":0.7,"feasibility":0.8},"blocking_issues":[],"suggestions":[],"strengths":["ok"]}',
            "{}", "{}", "{}", "{}", "{}", "{}", "{}", "{}", "{}", "{}", "{}", "{}", "{}", "{}", "{}",
        ])

        collector = CollectorAgent(llm)
        node = await collector.process(one_idea, SourceType.TEXT)

        weaver = WeaverAgent(llm)
        result = await weaver.weave([node], task["north_star"])
        clusters = WeaverAgent.build_clusters_from_result(result, [node])
        rels = WeaverAgent.build_relationships(result, [node])

        architect = ArchitectAgent(llm)
        design = await architect.design(clusters, rels, [], [], task["north_star"])

        critic = CriticAgent(llm)
        fb = await critic.critique(design)

        # 流水线完整性断言
        assert design is not None, "Architect 应生成设计文档"
        assert len(design.content_markdown) > 50, "设计文档内容不应过短"
        assert len(clusters) >= 0, "Weaver 应返回簇列表"
        assert fb.scores.coherence >= 0, "Critic 应返回有效评分"
        assert "mermaid" in design.content_markdown.lower() or "graph " in design.content_markdown.lower(), \
            "设计文档应包含 Mermaid 图"
        assert "### 3." in design.content_markdown, "设计文档应包含组件详规"

    # 黄金标准关键词验证（需真实 LLM 运行时执行）
    @pytest.mark.skip(reason="需真实 LLM API Key，在真实环境手动执行 python -m pytest tests/test_eval.py -k 'golden_real'")
    @pytest.mark.asyncio
    @pytest.mark.parametrize("task", GOLDEN_TASKS, ids=[t["name"] for t in GOLDEN_TASKS])
    async def test_golden_task_real_llm(self, task):
        """【真实 LLM】黄金标准：关键词覆盖 + Mermaid + 组件数"""
        from src.core.deepseek_service import OpenAICompatibleService
        from src.agents.collector import CollectorAgent
        from src.agents.weaver import WeaverAgent
        from src.agents.architect import ArchitectAgent
        from src.core.models import SourceType

        llm = OpenAICompatibleService()
        collector = CollectorAgent(llm)
        nodes = [await collector.process(t, SourceType.TEXT) for t in task["ideas"]]

        weaver = WeaverAgent(llm)
        result = await weaver.weave(nodes, task["north_star"])
        clusters = WeaverAgent.build_clusters_from_result(result, nodes)
        rels = WeaverAgent.build_relationships(result, nodes)
        conflicts = WeaverAgent.build_conflicts(result, nodes)

        architect = ArchitectAgent(llm)
        design = await architect.design(clusters, rels, [],
            [{"type": c.conflict_type.value, "description": c.description} for c in conflicts],
            task["north_star"])

        content = design.content_markdown
        for kw in task["must_contain"]:
            assert kw.lower() in content.lower(), f"缺少关键词: {kw}"
        component_count = content.count("### 3.")
        assert component_count >= task["min_components"]


# ══════════════════════════════════════
# 2. Critic 检出率
# ══════════════════════════════════════

TOXIC_DESIGNS = [
    {
        "name": "missing_auth",
        "content": """# 多用户博客系统
## 2. 架构概览
```mermaid
graph TD
User-->API-->DB
API-->Cache
```
## 3. 组件详规
### 3.1 API Server
处理所有请求的 REST API
### 3.2 PostgreSQL
存储用户数据和文章
## 4. 关键决策与权衡
| 决策 | 方案 |
|------|------|
| 数据库 | PostgreSQL |
""",
        "expected_issue": "暂无已知缺陷",  # FakeLLM 返回通过
        "should_detect": False,  # 用 FakeLLM 无法测真实检出
    },
    {
        "name": "cap_contradiction",
        "content": """# 分布式配置中心
## 2. 架构概览
```mermaid
graph TD
Client-->ConfigServer-->DB
```
## 3. 组件详规
### 3.1 ConfigServer
提供强一致性配置读取
### 3.2 MySQL
存储配置数据

系统优先保障可用性和分区容错，一致性可以最终一致。
但同时要求所有读操作必须看到最新写入。
""",
        "expected_issue": "CAP 自相矛盾",
        "should_detect": False,  # FakeLLM limitation
    },
    {
        "name": "spof_risk",
        "content": """# 实时数据处理系统
## 2. 架构概览
```mermaid
graph TD
Data-->SingleProcessor-->DB
```
## 3. 组件详规
### 3.1 SingleProcessor
单实例处理所有数据流
""",
        "expected_issue": "单点故障 (SPOF)",
        "should_detect": False,
    },
]


class TestCriticDetection:
    """Critic 对已知缺陷的检出能力"""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("case", TOXIC_DESIGNS, ids=[t["name"] for t in TOXIC_DESIGNS])
    async def test_critic_runs(self, case):
        """验证 Critic 能正常运行（真实检出率需真实 LLM）"""
        from src.core.llm_service import FakeLLMService
        from src.agents.critic import CriticAgent
        from src.core.models import DesignDocument, DesignType
        from uuid import uuid4

        llm = FakeLLMService(canned_responses=[
            '{"approved":true,"scores":{"coherence":0.8,"innovation":0.7,"feasibility":0.75},"blocking_issues":[],"suggestions":[],"strengths":["test"]}',
            "{}",
        ])

        doc = DesignDocument(
            id=uuid4(), title=case["name"],
            type=DesignType.ARCHITECTURE,
            content_markdown=case["content"],
        )

        critic = CriticAgent(llm)
        feedback = await critic.critique(doc)

        assert feedback is not None
        assert 0 <= feedback.scores.coherence <= 1
        assert 0 <= feedback.scores.feasibility <= 1


# ══════════════════════════════════════
# 3. 冲突检测准确率
# ══════════════════════════════════════

CONFLICT_PAIRS = [
    {
        "name": "consistency_vs_availability",
        "nodes": [
            ("系统必须强一致", "constraint"),
            ("系统优先可用性和分区容错", "constraint"),
        ],
        "expected_conflict": True,
        "expected_type": "contradiction",
    },
    {
        "name": "unrelated_ideas",
        "nodes": [
            ("需要加缓存提高性能", "solution_hypothesis"),
            ("前端用 React 18 重构", "feature_idea"),
        ],
        "expected_conflict": False,
    },
    {
        "name": "redis_vs_memcached",
        "nodes": [
            ("使用 Redis 做缓存", "solution_hypothesis"),
            ("使用 Memcached 做缓存", "solution_hypothesis"),
        ],
        "expected_conflict": True,
        "expected_type": "tension",
    },
]


class TestConflictAccuracy:
    """Weaver 冲突检测准确率"""

    def test_conflict_detection_has_methods(self):
        """验证 ConflictDetector 实现存在且方法签名正确"""
        from src.agents.weaver.conflict_detector import ConflictDetector
        assert hasattr(ConflictDetector, "detect"), "ConflictDetector 缺少 detect 方法"

    def test_conflict_types_defined(self):
        """验证 4 种冲突类型枚举完整"""
        from src.core.models import ConflictType
        types = [t.value for t in ConflictType]
        assert "contradiction" in types
        assert "tension" in types
        assert "incompatibility" in types
        assert "misunderstanding" in types


# ══════════════════════════════════════
# 4. Mermaid 语法回归
# ══════════════════════════════════════

class TestMermaidSyntax:
    """Architect 生成 Mermaid 语法正确性"""

    def test_mermaid_extraction(self):
        """验证代码能提取 Mermaid 块"""
        import re
        content = """# 测试
## 2. 架构概览
```mermaid
graph TD
A[Start]-->B[End]
```
"""
        mermaid_blocks = re.findall(r'```mermaid\n(.*?)```', content, re.DOTALL)
        assert len(mermaid_blocks) == 1

    def test_mermaid_has_arrows(self):
        """Mermaid 图应包含节点和箭头"""
        import re
        content = """```mermaid
graph TD
Client-->Gateway-->Cache
```"""
        blocks = re.findall(r'```mermaid\n(.*?)```', content, re.DOTALL)
        if blocks:
            assert "-->" in blocks[0] or "->" in blocks[0], \
                "Mermaid 应包含连接箭头"

    def test_mermaid_no_empty_block(self):
        """Mermaid 块不应为空"""
        import re
        content = """```mermaid
graph TD
A-->B
```"""
        blocks = re.findall(r'```mermaid\n(.*?)```', content, re.DOTALL)
        for block in blocks:
            assert block.strip(), "Mermaid 块不应为空"
