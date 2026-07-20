"""子组件 3: BridgeFinder —— 跨域桥梁"""

from typing import List
from src.agents.base import BaseAgent
from src.core.llm_service import LLMService
from src.core.models import IdeaNode


BRIDGE_SYSTEM = """你是 Weaver 的跨域桥梁子组件。
识别来自不同领域但共享结构模式的节点对——创新潜力最高的连接。
输出 JSON：{"cross_domain_bridges": [{"idx_a":0,"idx_b":5,"domain_a":"...","domain_b":"...","shared_structure":"..."}]}"""


class BridgeFinder:
    def __init__(self, llm: LLMService):
        self.agent = BaseAgent(llm=llm, model="",
                               temperature=0.7, max_tokens=2000)

    async def find(self, nodes: List[IdeaNode], clusters: List[dict],
                   relationships: List[dict]) -> dict:
        text = _format_nodes_brief(nodes[:20])
        messages = [
            {"role": "system", "content": BRIDGE_SYSTEM},
            {"role": "user", "content": f"节点：\n{text}"},
        ]
        return await self.agent.call_llm_json(messages)


def _format_nodes_brief(nodes: List[IdeaNode]) -> str:
    lines = []
    for i, n in enumerate(nodes):
        content = n.standardized_content or n.raw_content
        lines.append(f"[{i}] {content[:150]}\n    领域: {', '.join(n.context_tags[:5])}")
    return "\n".join(lines)
