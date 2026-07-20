"""Critic Agent —— 设计审计 + 评分 + 反馈"""

from typing import List
from src.agents.base import BaseAgent
from src.core.llm_service import LLMService
from src.core.models import DesignDocument, CriticFeedback, CriticScores
from src.utils.logging_config import logger


CRITIC_SYSTEM = """你是 Idea Weaving 系统中的 Critic Agent（设计审计员）。
对架构设计文档进行闭环验证。

评估维度：
1. 逻辑自洽性：数据流是否闭合？有无自相矛盾？因果链是否完整？
2. 需求覆盖率：原始问题是否都有方案？约束是否满足或明确拒绝？
3. 风险扫描：SPOF、安全缺口、可扩展性瓶颈、数据一致性隐患。

输出 JSON：
{
  "approved": true/false,
  "scores": {"coherence": 0.0-1.0, "innovation": 0.0-1.0, "feasibility": 0.0-1.0},
  "blocking_issues": [
    {"severity": "critical"|"major", "category": "...", "description": "...", "suggestion": "..."}
  ],
  "suggestions": [
    {"severity": "minor"|"enhancement", "aspect": "...", "suggestion": "..."}
  ],
  "strengths": ["..."],
  "feedback": "总体评估文本"
}

通过标准：coherence >= 0.6 且 feasibility >= 0.5"""


class CriticAgent:
    """设计审计——评判 + 引导改进"""

    def __init__(self, llm: LLMService):
        self.agent = BaseAgent(
            llm=llm,
            model="",
            temperature=0.2,
            max_tokens=4000,
        )

    async def critique(self, design: DesignDocument,
                       requirement_nodes: list | None = None) -> CriticFeedback:
        """评估设计文档"""

        # 截断过长的文档
        content = design.content_markdown
        if len(content) > 12000:
            content = content[:12000] + "\n\n...(内容过长，已截断)"

        req_text = ""
        if requirement_nodes:
            req_text = "\n\n原始需求：\n"
            for n in requirement_nodes:
                if hasattr(n, 'standardized_content'):
                    req_text += f"- {n.standardized_content}\n"

        messages = [
            {"role": "system", "content": CRITIC_SYSTEM},
            {"role": "user", "content": f"设计文档：\n\n{content}{req_text}\n\n请评估。"},
        ]

        data = await self.agent.call_llm_json(messages)

        if data.get("_parse_error"):
            logger.error("Critic JSON parse failed")
            return CriticFeedback(
                approved=True,
                scores=CriticScores(coherence=0.6, innovation=0.5, feasibility=0.5),
                blocking_issues=[],
                strengths=["JSON 解析失败，默认通过"],
            )

        scores_data = data.get("scores", {})
        feedback = CriticFeedback(
            approved=data.get("approved", False),
            scores=CriticScores(
                coherence=scores_data.get("coherence", 0.5),
                innovation=scores_data.get("innovation", 0.5),
                feasibility=scores_data.get("feasibility", 0.5),
            ),
            blocking_issues=data.get("blocking_issues", []),
            suggestions=data.get("suggestions", []),
            strengths=data.get("strengths", []),
        )

        logger.bind(component="critic").info(
            f"Critique: approved={feedback.approved} "
            f"coherence={feedback.scores.coherence:.2f} "
            f"feasibility={feedback.scores.feasibility:.2f}"
        )
        return feedback
