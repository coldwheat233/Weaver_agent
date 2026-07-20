"""Collector Agent —— 多模态标准化 + 三轴评分过滤"""

from typing import Optional
from src.agents.base import BaseAgent
from src.core.models import IdeaNode, SourceType, IntentTag
from src.core.llm_service import LLMService
from src.utils.logging_config import logger


COLLECTOR_SYSTEM = """你是 Idea Weaving 系统中的 Collector Agent（想法捕获者）。
你的职责：接收原始的非结构化输入（文本、图片描述、语音转写），产出一个标准化的"想法节点"。

对每条输入，你必须输出一个 JSON 对象：
{
  "standardized_content": "经过澄清和扩展的想法描述（2-4 句）",
  "intent_tags": ["problem_statement"|"solution_hypothesis"|"constraint"|"question"|"observation"|"analogy"|"goal"|"feature_idea"|"risk"|"assumption"],
  "context_tags": ["领域关键词数组"],
  "relevance_score": 0.0-1.0,
  "completeness_score": 0.0-1.0,
  "actionability_score": 0.0-1.0
}

质量过滤：
- 三项评分均 < 0.3 → 标记为 dormant
- 三项评分均 > 0.7 → 标记为高优先级
- 明显垃圾/空内容 → 三项评分均给 0.0

只输出有效 JSON。不要前言、不要解释。"""


COLLECTOR_FEWSHOT_USER = "微服务之间调用太慢了，需要加缓存"
COLLECTOR_FEWSHOT_ASSISTANT = """{
  "standardized_content": "微服务架构中存在服务间调用的延迟问题，需要通过引入缓存层来降低响应时间。这可能涉及本地缓存（如 Caffeine）、分布式缓存（如 Redis）或多级缓存策略的选型。需要考虑缓存失效策略、数据一致性保证和缓存穿透防护。",
  "intent_tags": ["problem_statement", "solution_hypothesis"],
  "context_tags": ["microservices", "caching", "latency", "distributed_systems"],
  "relevance_score": 0.85,
  "completeness_score": 0.6,
  "actionability_score": 0.5
}"""


class CollectorAgent:
    """标准化原始输入，生成 IdeaNode"""

    DORMANT_THRESHOLD = 0.3
    HIGH_PRIORITY_THRESHOLD = 0.7

    def __init__(self, llm: LLMService, model: str | None = None):
        from src.utils.config import get_settings
        m = model or get_settings().LIGHT_MODEL or "deepseek-chat"
        self.agent = BaseAgent(
            llm=llm,
            model=m,
            temperature=0.3,
            max_tokens=1000,
        )

    async def process(self, content: str, source_type: SourceType = SourceType.TEXT,
                      asset_path: Optional[str] = None,
                      session_id: Optional[str] = None) -> IdeaNode:
        """将原始输入转换为标准化的 IdeaNode"""
        messages = [
            {"role": "system", "content": COLLECTOR_SYSTEM},
            {"role": "user", "content": COLLECTOR_FEWSHOT_USER},
            {"role": "assistant", "content": COLLECTOR_FEWSHOT_ASSISTANT},
            {"role": "user", "content": content},
        ]

        data = await self.agent.call_llm_json(messages)

        if data.get("_parse_error"):
            logger.warning(f"Collector JSON parse failed, using raw content")

        node = IdeaNode(
            source_type=source_type,
            raw_content=content,
            raw_asset_path=asset_path,
            standardized_content=data.get("standardized_content", content),
            intent_tags=self._parse_tags(data.get("intent_tags", [])),
            context_tags=data.get("context_tags", []),
            relevance_score=data.get("relevance_score", 0.5),
            completeness_score=data.get("completeness_score", 0.5),
            actionability_score=data.get("actionability_score", 0.5),
            session_id=session_id,
        )

        # L2 过滤：综合评分
        composite = (node.relevance_score + node.completeness_score + node.actionability_score) / 3
        if composite < self.DORMANT_THRESHOLD:
            from src.core.models import NodeStatus
            node.status = NodeStatus.DORMANT
        elif composite >= self.HIGH_PRIORITY_THRESHOLD:
            node.north_star_relevance = 0.9

        logger.bind(component="collector").info(
            f"Normalized idea: {node.id} status={node.status.value} composite={composite:.2f}"
        )
        return node

    @staticmethod
    def _parse_tags(tags: list) -> list:
        result = []
        for t in tags:
            if isinstance(t, IntentTag):
                result.append(t)
            elif isinstance(t, str):
                try:
                    result.append(IntentTag(t))
                except ValueError:
                    pass
        return result
