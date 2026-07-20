"""子组件 2: RelationshipBuilder —— 关系发现"""

from typing import List
from src.agents.base import BaseAgent
from src.core.llm_service import LLMService
from src.core.models import IdeaNode
from src.agents.weaver.clusterer import _format_nodes


REL_BUILDER_SYSTEM = """你是 Weaver 的关系发现子组件。
对节点对判断关系：causal/contradicts/analogy/prerequisite/refines/generalizes/supports/transforms。
输出 JSON：{"relationships": [{"source_idx":0,"target_idx":1,"type":"causal","strength":0.8,"explanation":"..."}]}"""


class RelationshipBuilder:
    def __init__(self, llm: LLMService):
        self.agent = BaseAgent(llm=llm, model="",
                               temperature=0.7, max_tokens=4000)

    async def discover(self, nodes: List[IdeaNode], clusters: List[dict],
                       north_star: str) -> dict:
        text = _format_nodes(nodes[:30])
        cluster_text = "\n".join(
            f"簇 {c.get('name','?')}: 成员={c.get('member_indices',[])}" for c in clusters
        )
        messages = [
            {"role": "system", "content": REL_BUILDER_SYSTEM},
            {"role": "user", "content": f"北极星：{north_star}\n\n簇：\n{cluster_text}\n\n节点：\n{text}"},
        ]
        return await self.agent.call_llm_json(messages)
