"""Inquisitor Agent (V2) —— 主动提问，填补想法拼图

Weaver 编织后，Inquisitor 分析概念簇中的信息缺口，
主动向用户提问以细化设计。
"""

from typing import List
from src.agents.base import BaseAgent
from src.core.llm_service import LLMService
from src.core.models import ConceptCluster, IdeaNode
from src.utils.logging_config import logger


INQUISITOR_SYSTEM = """你是 Idea Weaver V2 的 Inquisitor Agent。
你的任务是：分析当前的想法集合和概念簇，找出信息缺口，向用户提出精准的追问。

规则：
1. 每个问题必须是具体的、可回答的
2. 问题应覆盖：缺失的约束条件、未定义的边界、模糊的技术选型、未考虑的权衡
3. 一次最多提 3 个问题，按优先级排序
4. 如果当前想法已经足够完整（形成了 2+ 个完整的概念簇且无冲突），返回空列表

输出 JSON：
{
  "questions": [
    {"priority": 1, "question": "...", "context": "为什么问这个", "category": "constraint|boundary|tradeoff|detail"},
    ...
  ],
  "completeness_estimate": 0.0-1.0,
  "ready_to_architect": true/false
}"""


class InquisitorAgent:
    """主动提问者——V2 交互式编织的核心"""

    def __init__(self, llm: LLMService):
        self.agent = BaseAgent(
            llm=llm,
            model="",
            temperature=0.5,
            max_tokens=1500,
        )

    async def converse(self, current_idea: str, history: List[str] | None = None,
                        round_num: int = 1) -> dict:
        """对话模式：引导完善想法。最多3轮，识别用户知识边界"""
        ctx = ""
        if history:
            ctx = "对话历史:\n" + "\n".join(history[-6:])
        round_hint = ""
        if round_num >= 3:
            round_hint = "\n重要：这是最后一轮追问。如果还缺细节，标记 completeness>0.6 让用户去编织。"
        elif round_num >= 2:
            round_hint = "\n重要：尽量在1-2轮内结束引导。用户说不知道代表触及知识边界，不要继续追问。"

        messages = [
            {"role": "system", "content": f"""你是技术导师，帮用户完善技术想法。

规则:
1. 每轮只提1个问题，要具体可回答
2. 用户回答"不知道/没概念/不确定"时→不要再追问这个方向，换角度或用 completenss>0.6 放行
3. 想法足够具体(有技术栈或量化指标)→completeness>0.7 建议编织
4. {round_hint}

输出 JSON: {{"question":"...","context":"为什么问","completeness":0.0-1.0}}"""},
            {"role": "user", "content": f"当前想法: {current_idea}\n{ctx}\n请提一个追问(第{round_num}轮)。"},
        ]
        data = await self.agent.call_llm_json(messages)
        if data.get("_parse_error"):
            return {"question": "", "context": "", "completeness": 0.5}
        return data

    async def interrogate(self, clusters: List[ConceptCluster],
                          nodes: List[IdeaNode],
                          north_star: str) -> dict:
        """分析信息缺口，生成追问"""
        if not clusters or not nodes:
            return {"questions": [], "completeness_estimate": 0.0, "ready_to_architect": False}

        # 构建上下文
        context_parts = [f"北极星目标：{north_star}\n"]
        context_parts.append("## 已有想法")
        for i, n in enumerate(nodes):
            content = n.standardized_content or n.raw_content
            context_parts.append(f"[{i}] {content}")

        context_parts.append("\n## 概念簇")
        for c in clusters:
            context_parts.append(f"- {c.name}: {c.description[:200]}")
            if c.conflicts:
                context_parts.append(f"  冲突: {len(c.conflicts)} 个")

        context = "\n".join(context_parts)

        messages = [
            {"role": "system", "content": INQUISITOR_SYSTEM},
            {"role": "user", "content": context},
        ]

        data = await self.agent.call_llm_json(messages)

        if data.get("_parse_error"):
            logger.warning("Inquisitor JSON parse failed")
            return {"questions": [], "completeness_estimate": 0.5, "ready_to_architect": False}

        q_count = len(data.get("questions", []))
        logger.bind(component="inquisitor").info(
            f"Generated {q_count} questions, completeness={data.get('completeness_estimate', 0):.2f}"
        )
        return data


class DialogueManager:
    """管理多轮对话状态"""

    def __init__(self):
        self.turns: List[dict] = []  # [{"role":"agent","content":"..."}, {"role":"user","content":"..."}]

    def add_agent_question(self, question: str):
        self.turns.append({"role": "agent", "content": question})

    def add_user_answer(self, answer: str):
        self.turns.append({"role": "user", "content": answer})

    def get_context(self) -> str:
        """将对话历史转为 Weaver 可用的上下文"""
        if not self.turns:
            return ""
        lines = ["## 交互历史"]
        for t in self.turns:
            role = "Agent" if t["role"] == "agent" else "用户"
            lines.append(f"**{role}**: {t['content']}")
        return "\n".join(lines)

    @property
    def turn_count(self) -> int:
        return len(self.turns)
