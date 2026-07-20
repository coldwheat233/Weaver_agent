"""子组件 4: ConflictDetector —— 冲突检测"""

from typing import List
from src.agents.base import BaseAgent
from src.core.llm_service import LLMService
from src.core.models import IdeaNode


CONFLICT_SYSTEM = """你是 Weaver 的冲突检测子组件。
识别逻辑矛盾/创造性张力的节点对。类型：contradiction/tension/incompatibility/misunderstanding。
输出 JSON：{"conflicts": [{"idx_a":2,"idx_b":3,"type":"contradiction","description":"...","suggested_strategy":"flag_for_user"}]}"""


class ConflictDetector:
    def __init__(self, llm: LLMService):
        self.agent = BaseAgent(llm=llm, model="",
                               temperature=0.5, max_tokens=2000)

    async def detect(self, nodes: List[IdeaNode],
                     relationships: List[dict]) -> dict:
        if len(nodes) < 2:
            return {"conflicts": []}

        text = "\n".join(
            f"[{i}] {n.standardized_content or n.raw_content}" for i, n in enumerate(nodes[:20])
        )
        messages = [
            {"role": "system", "content": CONFLICT_SYSTEM},
            {"role": "user", "content": f"节点：\n{text}"},
        ]
        return await self.agent.call_llm_json(messages)
