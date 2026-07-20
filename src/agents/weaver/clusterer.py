"""子组件 1: Clusterer —— 语义聚类"""

from typing import List
from src.agents.base import BaseAgent
from src.core.llm_service import LLMService
from src.core.models import IdeaNode


CLUSTERER_SYSTEM = """你是 Weaver 的聚类子组件。基于共同主题、互补视角或结构相似性，将想法分组。
输出 JSON：{"clusters": [{"name": "...", "description": "...", "member_indices": [0,1,3]}]}"""


class Clusterer:
    def __init__(self, llm: LLMService):
        self.agent = BaseAgent(llm=llm, model="",
                               temperature=0.7, max_tokens=4000)

    async def cluster(self, nodes: List[IdeaNode], north_star: str) -> dict:
        text = _format_nodes(nodes)
        messages = [
            {"role": "system", "content": CLUSTERER_SYSTEM},
            {"role": "user", "content": f"北极星：{north_star}\n\n节点：\n{text}"},
        ]
        return await self.agent.call_llm_json(messages)


def _format_nodes(nodes: List[IdeaNode]) -> str:
    lines = []
    for i, n in enumerate(nodes):
        content = n.standardized_content or n.raw_content
        tags = [t.value if hasattr(t, 'value') else str(t) for t in n.intent_tags]
        lines.append(f"[{i}] {content}\n    意图: {', '.join(tags)}\n    领域: {', '.join(n.context_tags)}")
    return "\n".join(lines)
