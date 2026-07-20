"""Architect Agent —— 生成结构化设计文档"""

from typing import List
from src.agents.base import BaseAgent
from src.core.llm_service import LLMService
from src.core.models import ConceptCluster, Relationship, DesignDocument, DesignType
from src.utils.logging_config import logger
from uuid import uuid4


ARCHITECT_SYSTEM = """你是 Idea Weaving 系统中的 Architect Agent（设计架构师）。
你将概念簇和关系图收敛为结构化工程设计文档。

输出完整的 Markdown 文档，包含：

## 1. 执行摘要
一段话概括设计目标与核心方案。

## 2. 架构概览
```mermaid
graph TD
    ...
```

列出所有组件及其职责，标明数据流方向。

## 3. 组件详规
每个组件：技术选型、接口定义、非功能性需求。

## 4. 关键决策与权衡
| 决策 | 备选方案 | 选择理由 | 代价 |

对识别的冲突给出明确回应。

## 5. 实施路径
分阶段建议，每阶段目标与里程碑。

约束：
- 技术选型要具体（"PostgreSQL with read replicas" 而非 "数据库"）
- Mermaid 图表语法必须正确
- 冲突不能回避"""


class ArchitectAgent:
    """生成结构化设计文档"""

    def __init__(self, llm: LLMService):
        self.agent = BaseAgent(
            llm=llm,
            model="",
            temperature=0.4,
            max_tokens=8000,
        )

    async def design(self, clusters: List[ConceptCluster],
                     relationships: List[Relationship],
                     bridges: List[dict],
                     conflicts: List[dict],
                     north_star: str) -> DesignDocument:
        """生成设计文档"""

        context = self._build_context(clusters, relationships, bridges, conflicts)
        messages = [
            {"role": "system", "content": ARCHITECT_SYSTEM},
            {"role": "user", "content": f"设计目标：{north_star}\n\n{context}\n\n请生成完整的设计文档。"},
        ]

        resp = await self.agent.call_llm(messages)

        doc = DesignDocument(
            id=uuid4(),
            title=north_star[:100],
            type=DesignType.ARCHITECTURE,
            source_cluster_ids=[c.id for c in clusters],
            content_markdown=resp.content,
        )

        logger.bind(component="architect").info(f"Design generated: {doc.id}")
        return doc

    def _build_context(self, clusters, relationships, bridges, conflicts) -> str:
        parts = []

        parts.append("## 概念簇")
        for i, c in enumerate(clusters):
            parts.append(f"### 簇 {i+1}: {c.name}")
            parts.append(f"描述: {c.description}")
            parts.append(f"跨域数: {c.cross_domain_count}")
            parts.append(f"成员节点 ID: {[str(nid)[:8] for nid in c.member_node_ids]}")

        parts.append("\n## 关系")
        for r in relationships:
            parts.append(f"- [{r.relationship_type.value}] {str(r.source_node_id)[:8]} → {str(r.target_node_id)[:8]} ({r.strength:.2f})")
            if r.explanation:
                parts.append(f"  说明: {r.explanation}")

        if bridges:
            parts.append("\n## 跨域桥梁")
            for b in bridges:
                parts.append(f"- {b.get('domain_a','?')} ↔ {b.get('domain_b','?')}: {b.get('shared_structure','')}")

        if conflicts:
            parts.append("\n## 冲突")
            for c in conflicts:
                parts.append(f"- [{c.get('type','?')}] {c.get('description','')}")

        return "\n".join(parts)
